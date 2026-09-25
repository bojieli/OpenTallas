# Area-constrained roofline: n6_vs_a100-flash-32k

> CONTEXT-LADDER RUNG of n6_vs_a100: DeepSeek-V4-Flash-0731 at 32,768 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 20x (ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream, 114 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 57 devices. On the GPU side the correction reaches 7x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 16 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Flash-0731 takes 43 x 815 mm2 (35,045 mm2, array, KV in SRAM) at 3,550 tok/s per user and 101 tok/s per 1,000 mm2, holding 1 session, against 42 copies of one unified HBM die at the same silicon: 10.6x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Flash-0731 on 60,310 mm2 of ROM silicon at 4,175 tok/s per user against 60,298 mm2 of a100_sxm_80gb-x73-hybrid at 338 tok/s: **12.4x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 23,056 resident sessions against the GPU cluster's 22,023. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on DeepSeek-V4-Flash-0731 at batch 1, the iso-area GPU cluster is 672 devices. Cut as one serial pipeline that is 84 stages and 1,473 us of link latency per token; but the model has 43 layers, so at most 43 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 1,376 us. The iso-area per-user ratio at that point falls from 12.2x to 11.8x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 2.62x to it.** At 46,455 mm2 on DeepSeek-V4-Flash-0731 the pipeline-only GPU delivers 132.39 tok/s and the same silicon running hybrid delivers 347 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.00x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 9.96x (DeepSeek-V4-Flash-0731, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 271 to 10,591 tok/s, and its rate with every slot occupied from 10,310 to 10,591. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 38 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,218 us over NVLink, capping per-user decode at 821 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 184.6 us and cap it at 5,416 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 5.2x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 3 of 10 operating points and an array 7; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 137 of 4468 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 63.7x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 14.59x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.03x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4-Flash-0731 at 32,768 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-hybrid-x43`** -- 43 x 815 mm2 reticle dies, 35,045 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **3,549.8 tok/s per user** (0.28 ms/token), binding on `layer_fixed_latency`
- **101.3 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 3,550 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 2,217 W at 0.063 W/mm2, 624.7 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 42 copies of one unified HBM die -- `a100_sxm_80gb-x42-hybrid`, 34,692 mm2, area ratio 1.0102 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 35,045 | 34,692 | 1.0102 |
| user tok/s | 3,549.8 | 335.2 | 10.59x |
| aggregate tok/s | 3,550 | 2,011 | 0.64x |
| resident sessions | 1 | 12,364 | -- |
| J/token | 0.6247 | 19.2782 | 30.9x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 12,364 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x16-hybrid` at 13,216 mm2 and 349.0 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57` | 46,455 | 4,053.7 | 87.3 | 1 | 11.68x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 60,310 | 4,175.0 | 69.2 | 23,056 | 12.37x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x36` | 29,340 | 2,655.9 | 90.5 | 1 | 7.85x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | 35,045 | 3,549.8 | 101.3 | 1 | 10.59x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | 35,045 | 3,549.8 | 101.3 | -- | 101.3 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x44` | 35,860 | 3,619.4 | 100.9 | 85.3 | 101.3 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x53` | 43,195 | 3,949.0 | 91.4 | 49.0 | 101.3 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x57` | 46,455 | 4,053.7 | 87.3 | 44.2 | 101.3 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x59` | 48,085 | 4,121.9 | 85.7 | 43.9 | 101.3 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x61` | 49,715 | 4,129.5 | 83.1 | 39.5 | 101.3 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x62` | 50,530 | 4,157.9 | 82.3 | 39.3 | 101.3 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x70` | 57,050 | 4,165.2 | 73.0 | 28.0 | 101.3 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 60,310 | 4,175.0 | 69.2 | 24.7 | 101.3 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` **<-- recommended** | 35,045 | 43 | 3,549.8 | 3,550 | 101.3 | 1 | `layer_fixed_latency` | 2,217 | 624.7 | `a100_sxm_80gb-x42-hybrid` | 10.59x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x44` | 35,860 | 44 | 3,619.4 | 3,619 | 100.9 | 1 | `layer_fixed_latency` | 2,336 | 645.4 | `a100_sxm_80gb-x43-hybrid` | 10.73x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x53` | 43,195 | 53 | 3,949.0 | 3,949 | 91.4 | 1 | `layer_fixed_latency` | 3,401 | 861.3 | `a100_sxm_80gb-x52-hybrid` | 11.60x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x57` | 46,455 | 57 | 4,053.7 | 4,054 | 87.3 | 1 | `layer_fixed_latency` | 3,874 | 955.8 | `a100_sxm_80gb-x56-hybrid` | 11.68x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x59` | 48,085 | 59 | 4,121.9 | 4,122 | 85.7 | 1 | `layer_fixed_latency` | 4,111 | 997.4 | `a100_sxm_80gb-x58-hybrid` | 12.20x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x61` | 49,715 | 61 | 4,129.5 | 4,130 | 83.1 | 1 | `layer_fixed_latency` | 4,348 | 1,052.8 | `a100_sxm_80gb-x60-hybrid` | 12.12x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x62` | 50,530 | 62 | 4,157.9 | 4,158 | 82.3 | 1 | `layer_fixed_latency` | 4,466 | 1,074.1 | `a100_sxm_80gb-x61-hybrid` | 12.15x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x70` | 57,050 | 70 | 4,165.2 | 74,974 | 73.0 | 21,810 | `layer_fixed_latency` | 7,260 | 1,543.5 | `a100_sxm_80gb-x69-hybrid` | 12.16x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 60,310 | 74 | 4,175.0 | 79,325 | 69.2 | 23,056 | `layer_fixed_latency` | 7,840 | 1,666.6 | `a100_sxm_80gb-x73-hybrid` | 12.37x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 378 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | 35,045 | 3,549.8 | 101.3 | 1 |
| array | 378 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 60,310 | 4,175.0 | 69.2 | 23,056 |
| array | 378 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x36` | 29,340 | 2,655.9 | 90.5 | 1 |
| wafer | 76 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,264.3 | 70.6 | 1 |
| wafer | 76 | fastest | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 3,951.3 | 42.7 | 5,359 |
| wafer | 76 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,264.3 | 70.6 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 60,310 | 4,175.0 | 79,325 | 23,056 | 7,840 | 1,666.6 | `layer_fixed_latency` | `a100_sxm_80gb-x73-hybrid` | 337.6 | 22,023 | 32,409.1 | 1.000 | 12.37x | 19.4x |
| 1 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 3,951.3 | 59,269 | 5,359 | 11,470 | 2,738.5 | `layer_fixed_latency` | `a100_sxm_80gb-x112-hybrid` | 344.2 | 34,174 | 48,170.5 | 0.999 | 11.48x | 17.6x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill` | 90,465 | 4,136.4 | 115,818 | 34,585 | 11,407 | 2,440.8 | `layer_fixed_latency` | `a100_sxm_80gb-x110-hybrid` | 342.6 | 33,551 | 47,542.8 | 0.996 | 12.07x | 19.5x |
| 1 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 3,951.3 | -- | 5,359 | -- | 2,738.5 | -- | -- | -- | -- | -- | 0.979 | 0.96x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 60,310 | 4,175.0 | 79,325 | 23,056 | 7,840 | 839.2 | `layer_fixed_latency` | `a100_sxm_80gb-x73-hybrid` | 337.6 | 22,023 | 16,798.6 | 1.000 | 12.37x | 20.0x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 3,951.3 | 59,269 | 5,359 | 11,470 | 1,375.1 | `layer_fixed_latency` | `a100_sxm_80gb-x112-hybrid` | 344.2 | 34,174 | 24,679.3 | 0.999 | 11.48x | 17.9x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill` | 90,465 | 4,136.4 | 115,818 | 34,585 | 11,407 | 1,226.3 | `layer_fixed_latency` | `a100_sxm_80gb-x110-hybrid` | 342.6 | 33,551 | 24,365.5 | 0.996 | 12.07x | 19.9x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 3,951.3 | -- | 5,359 | -- | 1,375.1 | -- | -- | -- | -- | -- | 0.979 | 0.96x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 60,310 | 4,175.0 | 79,325 | 23,056 | 7,840 | 425.4 | `layer_fixed_latency` | `a100_sxm_80gb-x73-hybrid` | 337.6 | 22,023 | 8,993.4 | 1.000 | 12.37x | 21.1x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 3,951.3 | 59,269 | 5,359 | 11,470 | 693.4 | `layer_fixed_latency` | `a100_sxm_80gb-x112-hybrid` | 344.2 | 34,174 | 12,933.7 | 0.999 | 11.48x | 18.7x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill` | 90,465 | 4,136.4 | 115,818 | 34,585 | 11,407 | 619.0 | `layer_fixed_latency` | `a100_sxm_80gb-x110-hybrid` | 342.6 | 33,551 | 12,776.8 | 0.996 | 12.07x | 20.6x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 3,951.3 | -- | 5,359 | -- | 693.4 | -- | -- | -- | -- | -- | 0.979 | 0.96x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 60,310 | 4,175.0 | 79,325 | 23,056 | 7,840 | 218.6 | `layer_fixed_latency` | `a100_sxm_80gb-x73-hybrid` | 337.6 | 22,023 | 5,090.7 | 1.000 | 12.37x | 23.3x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 3,951.3 | 59,269 | 5,359 | 11,470 | 352.6 | `layer_fixed_latency` | `a100_sxm_80gb-x112-hybrid` | 344.2 | 34,174 | 7,060.9 | 0.999 | 11.48x | 20.0x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill` | 90,465 | 4,136.4 | 115,818 | 34,585 | 11,407 | 315.4 | `layer_fixed_latency` | `a100_sxm_80gb-x110-hybrid` | 342.6 | 33,551 | 6,982.5 | 0.996 | 12.07x | 22.1x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 3,951.3 | -- | 5,359 | -- | 352.6 | -- | -- | -- | -- | -- | 0.979 | 0.96x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 60,310 | 4,175.0 | 79,325 | 23,056 | 7,840 | 115.2 | `layer_fixed_latency` | `a100_sxm_80gb-x73-hybrid` | 316.4 | 22,023 | 2,961.7 | 1.000 | 13.20x | 25.7x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 3,948.7 | 86,871 | 8,038 | 13,914 | 215.8 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 341.4 | 51,623 | 5,628.2 | 0.999 | 11.56x | 26.1x |
| 16 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 4,090.6 | 175,896 | 52,968 | 17,453 | 246.8 | `layer_fixed_latency` | `a100_sxm_80gb-x168-hybrid` | 341.4 | 51,623 | 5,628.2 | 0.998 | 11.98x | 22.8x |
| 16 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 3,948.7 | -- | 8,038 | -- | 215.8 | -- | -- | -- | -- | -- | 0.999 | 0.97x wafer/array | -- |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 120,620 | 4,116.2 | 152,298 | 46,113 | 15,184 | 113.4 | `layer_fixed_latency` | `a100_sxm_80gb-x146-hybrid` | 314.6 | 44,768 | 2,947.3 | 1.000 | 13.08x | 26.0x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 3,936.2 | 224,364 | 21,436 | 37,019 | 284.7 | `layer_fixed_latency` | `a100_sxm_80gb-x448-hybrid` | 333.1 | 138,865 | 7,256.8 | 0.999 | 11.82x | 25.5x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 4,098.7 | 348,387 | 105,937 | 34,865 | 129.1 | `layer_fixed_latency` | `a100_sxm_80gb-x335-hybrid` | 313.9 | 103,657 | 3,313.0 | 1.001 | 13.06x | 25.7x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,934.1 | 338,331 | 32,155 | 55,549 | 216.6 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 333.1 | 208,659 | 5,739.6 | 0.999 | 11.81x | 26.5x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 2,917.5 | 746,875 | 105,937 | 38,934 | 52.1 | `layer_fixed_latency` | `a100_sxm_80gb-x335-hybrid` | 211.0 | 103,657 | 1,380.2 | 1.001 | 13.83x | 26.5x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,261.4 | 834,919 | 32,155 | 60,705 | 72.7 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 269.0 | 208,659 | 2,040.0 | 0.999 | 12.13x | 28.1x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 1,290.7 | 1,321,687 | 105,937 | 44,131 | 33.4 | `compute` | `a100_sxm_80gb-x335-hybrid` | 106.5 | 103,657 | 838.0 | 1.001 | 12.12x | 25.1x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,776.8 | 1,819,472 | 32,155 | 71,456 | 39.3 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 155.0 | 208,659 | 1,095.8 | 0.999 | 11.46x | 27.9x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 378.6 | 1,550,862 | 105,937 | 45,356 | 29.2 | `compute` | `a100_sxm_80gb-x335-hybrid` | 45.8 | 103,657 | 500.8 | 1.001 | 8.26x | 17.1x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 567.0 | 2,322,541 | 32,155 | 74,035 | 31.9 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 69.3 | 208,659 | 663.0 | 0.999 | 8.18x | 20.8x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | 35,045 | array | SRAM | 1 |
| 2-4 | `ROM-N6-native-HBMKV-array-hw-hybrid-x45` | 36,675 | array | HBM | 14,021 |
| 8 | `ROM-N6-native-HBMKV-array-hw-hybrid-x47` | 38,305 | array | HBM | 14,644 |
| 16 | `ROM-N6-native-HBMKV-array-hw-hybrid-x56` | 45,640 | array | HBM | 17,448 |
| 32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x64-romfill` | 52,160 | array | HBM | 19,941 |
| 64 | `ROM-N6-native-HBMKV-array-hw-pipeline-x64-romfill` | 52,160 | array | HBM | 19,941 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x111` | 90,465 | array | HBM | 34,585 |
| 1024 | `ROM-N6-native-HBMKV-array-hw-hybrid-x148` | 120,620 | array | HBM | 46,113 |
| 4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x170` | 138,550 | array | HBM | 52,968 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 38, 43, 45, 47, 56, 57, 64, 67, 74, 111, 113, 148, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 38, 43, 45, 47, 56, 57, 67, 69, 70, 74, 111, 113, 148, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 36, 40, 43, 44, 53, 57, 59, 61, 62, 70, 105, 113, 140, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 36, 40, 43, 44, 53, 57, 59, 61, 62, 70, 105, 113, 140, 170, 227, 340 |

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
| DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | 1 | 8 | 5.51 | hierarchical | 191.35 | 38.08 | 58.43 | 34.54 | 3,549.8 |
| DeepSeek-V4-Flash-0731 | `a100_sxm_80gb-x42-hybrid` | 1 | 8 | 5.51 | measured_floor | 894.40 | 1,252.69 | 975.99 | 460.35 | 335.2 |
| DeepSeek-V4-Flash-0731 | `a100_sxm_80gb-x42-hybrid` | 64 | 8 | 5.51 | measured_floor | 894.40 | 2,030.90 | 3,578.07 | 535.77 | 166.8 |

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

- **0 of 4,468 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 81% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 520 | 0 | 49.0% | 80.8% | 0.391 | 79% |
| gpu | wafer (>=40,000 mm2) | 920 | 0 | 48.5% | 80.0% | 0.387 | 89% |
| rom | large array (5,000-40,000 mm2) | 948 | 0 | 18.2% | 48.2% | 0.241 | 95% |
| rom | wafer (>=40,000 mm2) | 2,080 | 0 | 25.3% | 45.8% | 0.229 | 95% |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,455 | `DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x57` | 0.955775 | 3,874.4 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x56-hybrid` | 24.490207 | 10,971.3 | link_latency | 25.62x |
| DeepSeek-V4-Flash-0731 | 2 | 52,160 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x64-romfill` | 0.691870 | 6,358.6 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x63-hybrid` | 14.363553 | 12,377.3 | link_latency | 20.76x |
| DeepSeek-V4-Flash-0731 | 4 | 52,160 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x64-romfill` | 0.351804 | 6,358.6 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x63-hybrid` | 7.775838 | 12,377.3 | link_latency | 22.10x |
| DeepSeek-V4-Flash-0731 | 8 | 52,160 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x64-romfill` | 0.181771 | 6,358.6 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x63-hybrid` | 4.481981 | 12,377.3 | link_latency | 24.66x |
| DeepSeek-V4-Flash-0731 | 16 | 52,160 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x64-romfill` | 0.096754 | 6,358.6 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x63-hybrid` | 2.598684 | 12,966.1 | link_latency | 26.86x |
| DeepSeek-V4-Flash-0731 | 32 | 90,465 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill` | 0.091396 | 11,484.2 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x110-hybrid` | 2.374545 | 22,840.3 | link_latency | 25.98x |
| DeepSeek-V4-Flash-0731 | 64 | 185,005 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 0.093674 | 23,415.2 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x224-hybrid` | 2.430785 | 46,044.4 | link_latency | 25.95x |
| DeepSeek-V4-Flash-0731 | 256 | 554,700 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.072708 | 60,705.5 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x672-hybrid` | 2.040009 | 140,466.9 | link_latency | 28.06x |
| DeepSeek-V4-Flash-0731 | 1024 | 554,700 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 0.039273 | 71,455.7 | kv_read | `DSV4-Flash/a100_sxm_80gb-x672-hybrid` | 1.095778 | 173,955.5 | weight_read | 27.90x |
| DeepSeek-V4-Flash-0731 | 4096 | 554,700 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 0.031877 | 74,035.3 | kv_read | `DSV4-Flash/a100_sxm_80gb-x672-hybrid` | 0.663046 | 188,158.0 | weight_read | 20.80x |

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
| DeepSeek-V4-Flash-0731 | 32,768 | 284 B | 166.9 GB | 4.70 | 0.066 GB | 0.231 GB | 170.1 |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 5,058.2 | wafer-pipeline | 3,264.3 | wafer-tensor | 1.55x | 872.0 | pipeline | 347.0 | hybrid | 2.51x | 5.80x | 9.41x | 1.62x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 5,060.5 | wafer-pipeline | 3,951.3 | wafer-hybrid | 1.28x | 917.0 | pipeline | 344.2 | hybrid | 2.66x | 5.52x | 11.48x | 2.08x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 5,060.9 | wafer-pipeline | 3,948.7 | wafer-hybrid | 1.28x | 933.0 | pipeline | 341.4 | hybrid | 2.73x | 5.42x | 11.56x | 2.13x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 5,060.9 | wafer-pipeline | 3,945.2 | wafer-hybrid | 1.28x | 941.2 | pipeline | 338.7 | hybrid | 2.78x | 5.38x | 11.65x | 2.17x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 5,060.9 | wafer-pipeline | 3,934.1 | wafer-hybrid | 1.29x | 949.6 | pipeline | 333.5 | hybrid | 2.85x | 5.33x | 11.80x | 2.21x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 5,060.9 | wafer-pipeline | 3,936.2 | wafer-hybrid | 1.29x | 953.8 | pipeline | 333.1 | hybrid | 2.86x | 5.31x | 11.82x | 2.23x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 5,060.9 | wafer-pipeline | 3,934.1 | wafer-hybrid | 1.29x | 958.1 | pipeline | 333.1 | hybrid | 2.88x | 5.28x | 11.81x | 2.24x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.62x to 2.24x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x74 | 60,310 | 4,175.0 | 79,325.2 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x73-hybrid | 60,298 | 1.00x | hybrid | 1,266.05 | 337.6 | 3,376.0 | link_latency | 12.37x | 8.21x | 31.54x | 12.37x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x36 | 29,340 | 2,655.9 | 2,655.9 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x36-hybrid | 29,736 | 0.99x | hybrid | 1,249.34 | 338.2 | 1,691.2 | link_latency | 7.85x | 0.56x | 20.01x | 7.85x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x74 | 60,310 | 4,175.0 | 79,325.2 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x73-hybrid | 60,298 | 1.00x | hybrid | 1,266.05 | 337.6 | 3,376.0 | link_latency | 12.37x | 8.21x | 31.54x | 12.37x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x38 | 30,970 | 1,950.8 | 3,901.6 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 1,249.34 | 340.8 | 1,703.8 | link_latency | 5.72x | 0.79x | 14.70x | 5.72x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x74 | 60,310 | 4,175.0 | 79,325.2 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x73-hybrid | 60,298 | 1.00x | hybrid | 1,266.05 | 337.6 | 3,376.0 | link_latency | 12.37x | 8.21x | 31.54x | 12.37x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x38 | 30,970 | 1,505.0 | 6,020.2 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 1,249.34 | 340.8 | 1,703.8 | link_latency | 4.42x | 1.23x | 11.34x | 4.42x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x74 | 60,310 | 4,175.0 | 79,325.2 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x73-hybrid | 60,298 | 1.00x | hybrid | 1,266.05 | 337.6 | 3,376.0 | link_latency | 12.37x | 8.21x | 31.54x | 12.37x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x38 | 30,970 | 985.8 | 7,886.6 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 1,296.86 | 319.7 | 2,557.9 | link_latency | 3.08x | 1.61x | 7.43x | 3.08x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x74 | 60,310 | 4,175.0 | 79,325.2 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x73-hybrid | 60,298 | 1.00x | hybrid | 1,317.50 | 316.4 | 5,061.7 | link_latency | 13.20x | 8.21x | 31.54x | 13.20x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x38 | 30,970 | 580.3 | 9,284.2 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 1,423.57 | 275.3 | 4,404.9 | link_latency | 2.11x | 1.89x | 4.37x | 2.11x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill | 120,620 | 4,116.2 | 152,298.0 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x146-hybrid | 120,596 | 1.00x | hybrid | 1,362.87 | 314.6 | 10,067.9 | link_latency | 13.08x | 7.88x | 31.09x | 13.08x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x38 | 30,970 | 312.5 | 9,999.9 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 1,676.99 | 217.3 | 6,954.9 | weight_read | 1.44x | 1.44x | 2.36x | 1.44x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 4,098.7 | 348,386.5 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 1,439.87 | 313.9 | 20,088.7 | link_latency | 13.06x | 7.86x | 30.96x | 13.06x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x38 | 30,970 | 163.5 | 10,461.4 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 2,183.83 | 156.5 | 10,016.8 | weight_read | 1.04x | 1.04x | 1.47x | 1.04x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,261.4 | 834,918.7 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,640.51 | 269.0 | 68,856.0 | link_latency | 12.13x | 9.38x | 24.63x | 12.53x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x38 | 30,970 | 41.5 | 10,611.8 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 5,018.76 | 69.8 | 17,880.7 | weight_read | 0.59x | 0.59x | 0.78x | 0.59x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,776.8 | 1,819,472.2 | kv_read | DSV4-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,600.26 | 155.0 | 158,750.7 | weight_read | 11.46x | 11.46x | 15.32x | 12.20x |
| DeepSeek-V4-Flash-0731 | 1024 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x38 | 30,970 | 10.4 | 10,629.0 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 17,331.16 | 32.8 | 33,553.6 | link_latency | 0.32x | 0.32x | 0.51x | 0.32x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 567.0 | 2,322,541.3 | kv_read | DSV4-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 2,727.08 | 69.3 | 283,778.1 | weight_read | 8.18x | 8.18x | 9.87x | 8.65x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x38 | 30,970 | 2.6 | 10,591.2 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 29,201.38 | 17.5 | 71,644.6 | link_latency | 0.15x | 0.15x | 0.24x | 0.15x |

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
| DeepSeek-V4-Flash-0731 | 16 | 13,216 | 133.7 | 215.4 | 349.0 | hybrid | 1,239.32 | 43.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 18 | 14,868 | 133.6 | 209.1 | 321.0 | hybrid | 1,119.72 | 35.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 19 | 15,694 | 133.5 | 209.7 | 326.7 | hybrid | 1,242.66 | 40.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 20 | 16,520 | 133.5 | 210.2 | 331.7 | hybrid | 1,242.66 | 41.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 24 | 19,824 | 133.3 | 211.9 | 348.6 | hybrid | 1,242.66 | 43.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 27 | 22,302 | 133.2 | 208.7 | 332.5 | hybrid | 1,246.00 | 41.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 36 | 29,736 | 132.7 | 207.5 | 338.2 | hybrid | 1,249.34 | 42.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 37 | 30,562 | 132.7 | 207.5 | 340.8 | hybrid | 1,249.34 | 42.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 39 | 32,214 | 132.6 | 207.6 | 345.5 | hybrid | 1,249.34 | 43.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 42 | 34,692 | 132.4 | 206.0 | 335.2 | hybrid | 1,252.69 | 42.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 43 | 35,518 | 132.4 | 206.0 | 337.4 | hybrid | 1,252.69 | 42.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 44 | 36,344 | 132.4 | 206.0 | 339.5 | hybrid | 1,252.69 | 42.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 46 | 37,996 | 132.4 | 206.0 | 343.6 | hybrid | 1,252.69 | 43.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 52 | 42,952 | 132.4 | 204.6 | 340.3 | hybrid | 1,256.03 | 42.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 55 | 45,430 | 132.4 | 204.5 | 345.4 | hybrid | 1,256.03 | 43.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 56 | 46,256 | 132.4 | 204.4 | 347.0 | hybrid | 1,256.03 | 43.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 58 | 47,908 | 132.4 | 203.4 | 337.7 | hybrid | 1,259.37 | 42.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 60 | 49,560 | 132.4 | 203.3 | 340.8 | hybrid | 1,259.37 | 42.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 61 | 50,386 | 132.4 | 203.2 | 342.3 | hybrid | 1,259.37 | 43.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 63 | 52,038 | 132.4 | 203.0 | 345.2 | hybrid | 1,259.37 | 43.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 66 | 54,516 | 132.4 | 187.1 | 338.4 | hybrid | 1,262.71 | 42.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 68 | 56,168 | 132.4 | 186.9 | 341.1 | hybrid | 1,262.71 | 43.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 69 | 56,994 | 132.4 | 186.9 | 342.4 | hybrid | 1,262.71 | 43.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 73 | 60,298 | 132.4 | 186.1 | 337.6 | hybrid | 1,266.05 | 42.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 104 | 85,904 | 132.4 | 182.3 | 344.6 | hybrid | 1,276.07 | 44.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 110 | 90,860 | 132.4 | 181.4 | 342.6 | hybrid | 1,279.42 | 43.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 111 | 91,686 | 132.4 | 181.4 | 343.4 | hybrid | 1,279.42 | 43.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 112 | 92,512 | 132.4 | 181.3 | 344.2 | hybrid | 1,279.42 | 44.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 138 | 113,988 | 132.4 | 177.8 | 338.9 | hybrid | 1,292.78 | 43.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 146 | 120,596 | 132.4 | 176.9 | 338.7 | hybrid | 1,296.12 | 43.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 168 | 138,768 | 132.4 | 174.4 | 341.4 | hybrid | 1,302.81 | 44.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 224 | 185,024 | 132.4 | 168.2 | 338.7 | hybrid | 1,326.20 | 44.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 335 | 276,710 | 132.4 | 136.6 | 333.2 | hybrid | 1,372.97 | 45.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 336 | 277,536 | 132.4 | 136.5 | 333.5 | hybrid | 1,372.97 | 45.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 448 | 370,048 | 132.4 | 129.2 | 333.1 | hybrid | 1,376.32 | 45.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 672 | 555,072 | 132.4 | 116.7 | 333.1 | hybrid | 1,376.32 | 45.8% | link_latency |

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
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x62 | DeepSeek-V4-Flash-0731 | 62 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x40 | DeepSeek-V4-Flash-0731 | 40 | tensor | rom_package_ucie | rom_board_serdes | 172 | 59.93 us | 1,668.5 tok/s | 16,685.3 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 10 on rom_board_serdes (traversals 6.6) = 57.82 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x59 | DeepSeek-V4-Flash-0731 | 59 | hybrid | rom_package_ucie | rom_board_serdes | 100 | 3.58 us | 27,932.9 tok/s | 279,329.3 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 14 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.46 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x61 | DeepSeek-V4-Flash-0731 | 61 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-tensor-x36 | DeepSeek-V4-Flash-0731 | 36 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x43 | DeepSeek-V4-Flash-0731 | 43 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x70 | DeepSeek-V4-Flash-0731 | 70 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x43 | DeepSeek-V4-Flash-0731 | 43 | tensor | rom_package_ucie | rom_board_serdes | 172 | 59.94 us | 1,668.2 tok/s | 16,682.3 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 11 on rom_board_serdes (traversals 6.6) = 57.83 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x67 | DeepSeek-V4-Flash-0731 | 67 | hybrid | rom_package_ucie | rom_board_serdes | 102 | 3.79 us | 26,391.5 tok/s | 263,914.5 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 16 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.67 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x69 | DeepSeek-V4-Flash-0731 | 69 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2 | DeepSeek-V4-Flash-0731 | 2 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-tensor-x38 | DeepSeek-V4-Flash-0731 | 38 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4-Flash-0731 | 2 | tensor | on_wafer | rom_wafer_serdes | 172 | 184.65 us | 541.6 tok/s | 5,415.8 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us; 86 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 19.10 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x45 | DeepSeek-V4-Flash-0731 | 45 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | DeepSeek-V4-Flash-0731 | 2 | hybrid | on_wafer | rom_wafer_serdes | 87 | 165.65 us | 603.7 tok/s | 6,036.8 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Flash/a100_sxm_80gb-x16-pipeline | DeepSeek-V4-Flash-0731 | 16 | pipeline | nvlink3 | infiniband_hdr | 15 | 37.74 us | 2,649.7 tok/s | 26,497.1 tok/s | 14 x point_to_point span 2 on nvlink3 (traversals 1.0) = 35.38 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| DSV4-Flash/a100_sxm_80gb-x16-tensor | DeepSeek-V4-Flash-0731 | 16 | tensor | nvlink3 | infiniband_hdr | 172 | 827.60 us | 120.8 tok/s | 1,208.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 391.43 us |
| DSV4-Flash/a100_sxm_80gb-x16-hybrid | DeepSeek-V4-Flash-0731 | 16 | hybrid | nvlink3 | infiniband_hdr | 87 | 438.52 us | 228.0 tok/s | 2,280.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| DSV4-Flash/a100_sxm_80gb-x16-expert | DeepSeek-V4-Flash-0731 | 16 | expert | nvlink3 | infiniband_hdr | 172 | 618.23 us | 161.8 tok/s | 1,617.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 185.15 us |
| DSV4-Flash/a100_sxm_80gb-x18-pipeline | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink3 | infiniband_hdr | 17 | 42.62 us | 2,346.0 tok/s | 23,460.4 tok/s | 15 x point_to_point span 2 on nvlink3 (traversals 1.0) = 37.91 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x18-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x18-hybrid | DeepSeek-V4-Flash-0731 | 18 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x18-expert | DeepSeek-V4-Flash-0731 | 18 | expert | nvlink3 | infiniband_hdr | 172 | 617.06 us | 162.1 tok/s | 1,620.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 183.97 us |
| DSV4-Flash/a100_sxm_80gb-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink3 | infiniband_hdr | 18 | 45.15 us | 2,214.7 tok/s | 22,147.3 tok/s | 16 x point_to_point span 2 on nvlink3 (traversals 1.0) = 40.44 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x19-expert | DeepSeek-V4-Flash-0731 | 19 | expert | nvlink3 | infiniband_hdr | 172 | 616.56 us | 162.2 tok/s | 1,621.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 183.48 us |
| DSV4-Flash/a100_sxm_80gb-x20-pipeline | DeepSeek-V4-Flash-0731 | 20 | pipeline | nvlink3 | infiniband_hdr | 19 | 47.68 us | 2,097.3 tok/s | 20,973.3 tok/s | 17 x point_to_point span 2 on nvlink3 (traversals 1.0) = 42.96 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x20-tensor | DeepSeek-V4-Flash-0731 | 20 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x20-hybrid | DeepSeek-V4-Flash-0731 | 20 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x20-expert | DeepSeek-V4-Flash-0731 | 20 | expert | nvlink3 | infiniband_hdr | 172 | 616.12 us | 162.3 tok/s | 1,623.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 183.03 us |
| DSV4-Flash/a100_sxm_80gb-x24-pipeline | DeepSeek-V4-Flash-0731 | 24 | pipeline | nvlink3 | infiniband_hdr | 23 | 57.79 us | 1,730.4 tok/s | 17,304.4 tok/s | 21 x point_to_point span 2 on nvlink3 (traversals 1.0) = 53.07 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x24-tensor | DeepSeek-V4-Flash-0731 | 24 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x24-hybrid | DeepSeek-V4-Flash-0731 | 24 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x24-expert | DeepSeek-V4-Flash-0731 | 24 | expert | nvlink3 | infiniband_hdr | 172 | 613.68 us | 163.0 tok/s | 1,629.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 432.05 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 181.63 us |
| DSV4-Flash/a100_sxm_80gb-x27-pipeline | DeepSeek-V4-Flash-0731 | 27 | pipeline | nvlink3 | infiniband_hdr | 26 | 65.20 us | 1,533.7 tok/s | 15,337.2 tok/s | 23 x point_to_point span 2 on nvlink3 (traversals 1.0) = 58.13 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| DSV4-Flash/a100_sxm_80gb-x27-tensor | DeepSeek-V4-Flash-0731 | 27 | tensor | nvlink3 | infiniband_hdr | 172 | 848.73 us | 117.8 tok/s | 1,178.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 412.57 us |
| DSV4-Flash/a100_sxm_80gb-x27-hybrid | DeepSeek-V4-Flash-0731 | 27 | hybrid | nvlink3 | infiniband_hdr | 89 | 443.24 us | 225.6 tok/s | 2,256.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| DSV4-Flash/a100_sxm_80gb-x27-expert | DeepSeek-V4-Flash-0731 | 27 | expert | nvlink3 | infiniband_hdr | 172 | 612.90 us | 163.2 tok/s | 1,631.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 432.05 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 180.84 us |
| DSV4-Flash/a100_sxm_80gb-x36-pipeline | DeepSeek-V4-Flash-0731 | 36 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x36-tensor | DeepSeek-V4-Flash-0731 | 36 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x36-hybrid | DeepSeek-V4-Flash-0731 | 36 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x36-expert | DeepSeek-V4-Flash-0731 | 36 | expert | nvlink3 | infiniband_hdr | 172 | 610.82 us | 163.7 tok/s | 1,637.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 179.28 us |
| DSV4-Flash/a100_sxm_80gb-x37-pipeline | DeepSeek-V4-Flash-0731 | 37 | pipeline | nvlink3 | infiniband_hdr | 36 | 90.30 us | 1,107.4 tok/s | 11,073.6 tok/s | 32 x point_to_point span 2 on nvlink3 (traversals 1.0) = 80.87 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-tensor | DeepSeek-V4-Flash-0731 | 37 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x37-hybrid | DeepSeek-V4-Flash-0731 | 37 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-expert | DeepSeek-V4-Flash-0731 | 37 | expert | nvlink3 | infiniband_hdr | 172 | 610.69 us | 163.7 tok/s | 1,637.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 179.15 us |
| DSV4-Flash/a100_sxm_80gb-x39-pipeline | DeepSeek-V4-Flash-0731 | 39 | pipeline | nvlink3 | infiniband_hdr | 38 | 95.36 us | 1,048.7 tok/s | 10,486.7 tok/s | 34 x point_to_point span 2 on nvlink3 (traversals 1.0) = 85.93 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x39-tensor | DeepSeek-V4-Flash-0731 | 39 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x39-hybrid | DeepSeek-V4-Flash-0731 | 39 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x39-expert | DeepSeek-V4-Flash-0731 | 39 | expert | nvlink3 | infiniband_hdr | 172 | 610.46 us | 163.8 tok/s | 1,638.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.92 us |
| DSV4-Flash/a100_sxm_80gb-x42-pipeline | DeepSeek-V4-Flash-0731 | 42 | pipeline | nvlink3 | infiniband_hdr | 41 | 102.77 us | 973.0 tok/s | 9,730.3 tok/s | 36 x point_to_point span 2 on nvlink3 (traversals 1.0) = 90.98 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x42-tensor | DeepSeek-V4-Flash-0731 | 42 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x42-hybrid | DeepSeek-V4-Flash-0731 | 42 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x42-expert | DeepSeek-V4-Flash-0731 | 42 | expert | nvlink3 | infiniband_hdr | 172 | 609.84 us | 164.0 tok/s | 1,639.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.61 us |
| DSV4-Flash/a100_sxm_80gb-x43-pipeline | DeepSeek-V4-Flash-0731 | 43 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x43-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x43-hybrid | DeepSeek-V4-Flash-0731 | 43 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x43-expert | DeepSeek-V4-Flash-0731 | 43 | expert | nvlink3 | infiniband_hdr | 172 | 609.75 us | 164.0 tok/s | 1,640.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.51 us |
| DSV4-Flash/a100_sxm_80gb-x44-pipeline | DeepSeek-V4-Flash-0731 | 44 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x44-tensor | DeepSeek-V4-Flash-0731 | 44 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x44-hybrid | DeepSeek-V4-Flash-0731 | 44 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x44-expert | DeepSeek-V4-Flash-0731 | 44 | expert | nvlink3 | infiniband_hdr | 172 | 609.66 us | 164.0 tok/s | 1,640.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.42 us |
| DSV4-Flash/a100_sxm_80gb-x46-pipeline | DeepSeek-V4-Flash-0731 | 46 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x46-tensor | DeepSeek-V4-Flash-0731 | 46 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x46-hybrid | DeepSeek-V4-Flash-0731 | 46 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x46-expert | DeepSeek-V4-Flash-0731 | 46 | expert | nvlink3 | infiniband_hdr | 172 | 609.49 us | 164.1 tok/s | 1,640.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.26 us |
| DSV4-Flash/a100_sxm_80gb-x52-pipeline | DeepSeek-V4-Flash-0731 | 52 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x52-tensor | DeepSeek-V4-Flash-0731 | 52 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x52-hybrid | DeepSeek-V4-Flash-0731 | 52 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x52-expert | DeepSeek-V4-Flash-0731 | 52 | expert | nvlink3 | infiniband_hdr | 172 | 608.86 us | 164.2 tok/s | 1,642.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.83 us |
| DSV4-Flash/a100_sxm_80gb-x55-pipeline | DeepSeek-V4-Flash-0731 | 55 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x55-tensor | DeepSeek-V4-Flash-0731 | 55 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x55-hybrid | DeepSeek-V4-Flash-0731 | 55 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x55-expert | DeepSeek-V4-Flash-0731 | 55 | expert | nvlink3 | infiniband_hdr | 172 | 608.68 us | 164.3 tok/s | 1,642.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.65 us |
| DSV4-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Flash-0731 | 56 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Flash-0731 | 56 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Flash-0731 | 56 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x56-expert | DeepSeek-V4-Flash-0731 | 56 | expert | nvlink3 | infiniband_hdr | 172 | 608.48 us | 164.3 tok/s | 1,643.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.60 us |
| DSV4-Flash/a100_sxm_80gb-x58-pipeline | DeepSeek-V4-Flash-0731 | 58 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x58-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x58-hybrid | DeepSeek-V4-Flash-0731 | 58 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x58-expert | DeepSeek-V4-Flash-0731 | 58 | expert | nvlink3 | infiniband_hdr | 172 | 608.38 us | 164.4 tok/s | 1,643.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.50 us |
| DSV4-Flash/a100_sxm_80gb-x60-pipeline | DeepSeek-V4-Flash-0731 | 60 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x60-tensor | DeepSeek-V4-Flash-0731 | 60 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x60-hybrid | DeepSeek-V4-Flash-0731 | 60 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x60-expert | DeepSeek-V4-Flash-0731 | 60 | expert | nvlink3 | infiniband_hdr | 172 | 608.28 us | 164.4 tok/s | 1,644.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.40 us |
| DSV4-Flash/a100_sxm_80gb-x61-pipeline | DeepSeek-V4-Flash-0731 | 61 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x61-tensor | DeepSeek-V4-Flash-0731 | 61 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x61-hybrid | DeepSeek-V4-Flash-0731 | 61 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x61-expert | DeepSeek-V4-Flash-0731 | 61 | expert | nvlink3 | infiniband_hdr | 172 | 608.23 us | 164.4 tok/s | 1,644.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.35 us |
| DSV4-Flash/a100_sxm_80gb-x63-pipeline | DeepSeek-V4-Flash-0731 | 63 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x63-tensor | DeepSeek-V4-Flash-0731 | 63 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x63-hybrid | DeepSeek-V4-Flash-0731 | 63 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x63-expert | DeepSeek-V4-Flash-0731 | 63 | expert | nvlink3 | infiniband_hdr | 172 | 608.14 us | 164.4 tok/s | 1,644.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.26 us |
| DSV4-Flash/a100_sxm_80gb-x66-pipeline | DeepSeek-V4-Flash-0731 | 66 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x66-tensor | DeepSeek-V4-Flash-0731 | 66 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x66-hybrid | DeepSeek-V4-Flash-0731 | 66 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x66-expert | DeepSeek-V4-Flash-0731 | 66 | expert | nvlink3 | infiniband_hdr | 172 | 607.91 us | 164.5 tok/s | 1,645.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.77 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.14 us |
| DSV4-Flash/a100_sxm_80gb-x68-pipeline | DeepSeek-V4-Flash-0731 | 68 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x68-tensor | DeepSeek-V4-Flash-0731 | 68 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x68-hybrid | DeepSeek-V4-Flash-0731 | 68 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x68-expert | DeepSeek-V4-Flash-0731 | 68 | expert | nvlink3 | infiniband_hdr | 172 | 607.84 us | 164.5 tok/s | 1,645.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.77 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.07 us |
| DSV4-Flash/a100_sxm_80gb-x69-pipeline | DeepSeek-V4-Flash-0731 | 69 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x69-tensor | DeepSeek-V4-Flash-0731 | 69 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x69-hybrid | DeepSeek-V4-Flash-0731 | 69 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x69-expert | DeepSeek-V4-Flash-0731 | 69 | expert | nvlink3 | infiniband_hdr | 172 | 607.80 us | 164.5 tok/s | 1,645.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.77 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.03 us |
| DSV4-Flash/a100_sxm_80gb-x73-pipeline | DeepSeek-V4-Flash-0731 | 73 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x73-tensor | DeepSeek-V4-Flash-0731 | 73 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x73-hybrid | DeepSeek-V4-Flash-0731 | 73 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x73-expert | DeepSeek-V4-Flash-0731 | 73 | expert | nvlink3 | infiniband_hdr | 172 | 607.58 us | 164.6 tok/s | 1,645.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.68 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.90 us |
| DSV4-Flash/a100_sxm_80gb-x104-pipeline | DeepSeek-V4-Flash-0731 | 104 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x104-tensor | DeepSeek-V4-Flash-0731 | 104 | tensor | nvlink3 | infiniband_hdr | 172 | 863.36 us | 115.8 tok/s | 1,158.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 427.20 us |
| DSV4-Flash/a100_sxm_80gb-x104-hybrid | DeepSeek-V4-Flash-0731 | 104 | hybrid | nvlink3 | infiniband_hdr | 98 | 464.46 us | 215.3 tok/s | 2,153.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.29 us |
| DSV4-Flash/a100_sxm_80gb-x104-expert | DeepSeek-V4-Flash-0731 | 104 | expert | nvlink3 | infiniband_hdr | 172 | 606.68 us | 164.8 tok/s | 1,648.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.47 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.21 us |
| DSV4-Flash/a100_sxm_80gb-x110-pipeline | DeepSeek-V4-Flash-0731 | 110 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x110-tensor | DeepSeek-V4-Flash-0731 | 110 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x110-hybrid | DeepSeek-V4-Flash-0731 | 110 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x110-expert | DeepSeek-V4-Flash-0731 | 110 | expert | nvlink3 | infiniband_hdr | 172 | 606.59 us | 164.9 tok/s | 1,648.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.47 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.12 us |
| DSV4-Flash/a100_sxm_80gb-x111-pipeline | DeepSeek-V4-Flash-0731 | 111 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x111-tensor | DeepSeek-V4-Flash-0731 | 111 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x111-hybrid | DeepSeek-V4-Flash-0731 | 111 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x111-expert | DeepSeek-V4-Flash-0731 | 111 | expert | nvlink3 | infiniband_hdr | 172 | 606.58 us | 164.9 tok/s | 1,648.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.47 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.10 us |
| DSV4-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Flash-0731 | 112 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Flash-0731 | 112 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Flash-0731 | 112 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x112-expert | DeepSeek-V4-Flash-0731 | 112 | expert | nvlink3 | infiniband_hdr | 172 | 606.53 us | 164.9 tok/s | 1,648.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.44 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.09 us |
| DSV4-Flash/a100_sxm_80gb-x138-pipeline | DeepSeek-V4-Flash-0731 | 138 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x138-tensor | DeepSeek-V4-Flash-0731 | 138 | tensor | nvlink3 | infiniband_hdr | 172 | 865.17 us | 115.6 tok/s | 1,155.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 429.00 us |
| DSV4-Flash/a100_sxm_80gb-x138-hybrid | DeepSeek-V4-Flash-0731 | 138 | hybrid | nvlink3 | infiniband_hdr | 103 | 476.25 us | 210.0 tok/s | 2,099.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| DSV4-Flash/a100_sxm_80gb-x138-expert | DeepSeek-V4-Flash-0731 | 138 | expert | nvlink3 | infiniband_hdr | 172 | 606.17 us | 165.0 tok/s | 1,649.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.36 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.81 us |
| DSV4-Flash/a100_sxm_80gb-x146-pipeline | DeepSeek-V4-Flash-0731 | 146 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x146-tensor | DeepSeek-V4-Flash-0731 | 146 | tensor | nvlink3 | infiniband_hdr | 172 | 865.42 us | 115.6 tok/s | 1,155.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 429.25 us |
| DSV4-Flash/a100_sxm_80gb-x146-hybrid | DeepSeek-V4-Flash-0731 | 146 | hybrid | nvlink3 | infiniband_hdr | 104 | 478.60 us | 208.9 tok/s | 2,089.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 42.44 us |
| DSV4-Flash/a100_sxm_80gb-x146-expert | DeepSeek-V4-Flash-0731 | 146 | expert | nvlink3 | infiniband_hdr | 172 | 606.08 us | 165.0 tok/s | 1,649.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.34 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.74 us |
| DSV4-Flash/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Flash-0731 | 168 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Flash-0731 | 168 | tensor | nvlink3 | infiniband_hdr | 172 | 865.84 us | 115.5 tok/s | 1,154.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 429.68 us |
| DSV4-Flash/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Flash-0731 | 168 | hybrid | nvlink3 | infiniband_hdr | 106 | 483.32 us | 206.9 tok/s | 2,069.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.15 us |
| DSV4-Flash/a100_sxm_80gb-x168-expert | DeepSeek-V4-Flash-0731 | 168 | expert | nvlink3 | infiniband_hdr | 172 | 605.88 us | 165.0 tok/s | 1,650.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.29 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.59 us |
| DSV4-Flash/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Flash-0731 | 224 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Flash-0731 | 224 | tensor | nvlink3 | infiniband_hdr | 172 | 866.85 us | 115.4 tok/s | 1,153.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 430.68 us |
| DSV4-Flash/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Flash-0731 | 224 | hybrid | nvlink3 | infiniband_hdr | 113 | 499.82 us | 200.1 tok/s | 2,000.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.66 us |
| DSV4-Flash/a100_sxm_80gb-x224-expert | DeepSeek-V4-Flash-0731 | 224 | expert | nvlink3 | infiniband_hdr | 172 | 605.55 us | 165.1 tok/s | 1,651.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.22 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.33 us |
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
| DSV4-Flash/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Flash-0731 | 672 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Flash-0731 | 672 | tensor | nvlink3 | infiniband_hdr | 172 | 1,218.02 us | 82.1 tok/s | 821.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 781.85 us |
| DSV4-Flash/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Flash-0731 | 672 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x672-expert | DeepSeek-V4-Flash-0731 | 672 | expert | nvlink3 | infiniband_hdr | 172 | 604.90 us | 165.3 tok/s | 1,653.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.07 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 174.83 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 1 | array | array | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x57 | 46,455 | 4,053.7 | 0.087 | 4,053.7 (46,455) | 3,951.3 (92,450) | 0.97x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 2 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x64-romfill | 52,160 | 4,107.5 | 0.079 | 4,107.5 (52,160) | 3,951.3 (92,450) | 0.96x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 4 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x64-romfill | 52,160 | 4,107.5 | 0.079 | 4,107.5 (52,160) | 3,951.3 (92,450) | 0.96x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 8 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x64-romfill | 52,160 | 4,107.5 | 0.079 | 4,107.5 (52,160) | 3,951.3 (92,450) | 0.96x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 16 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x64-romfill | 52,160 | 4,107.5 | 0.079 | 4,107.5 (52,160) | 3,948.7 (138,675) | 0.96x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill | 90,465 | 3,926.7 | 0.043 | 3,926.7 (90,465) | 3,741.8 (138,675) | 0.95x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 64 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill | 185,005 | 3,905.7 | 0.021 | 3,905.7 (185,005) | 3,741.8 (277,350) | 0.96x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 256 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,261.4 | 0.006 | 2,917.5 (277,100) | 3,261.4 (554,700) | 1.12x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 1024 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,776.8 | 0.003 | 1,290.7 (277,100) | 1,776.8 (554,700) | 1.38x | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 567.0 | 0.001 | 378.6 (277,100) | 567.0 (554,700) | 1.50x | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | sram | 364,975.8 | 27,644.6 | 27,644.6 | 13.20x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 364,975.8 | 27,644.6 | 27,644.6 | 13.20x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 364,975.8 | 27,644.6 | 27,644.6 | 13.20x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 364,975.8 | 27,644.6 | 27,644.6 | 13.20x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 364,975.8 | 27,644.6 | 33,810.9 | 13.20x | 1.22x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 364,975.8 | 27,644.6 | 54,753.1 | 13.20x | 1.98x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 364,975.8 | 27,872.4 | 86,452.9 | 13.09x | 3.10x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 518,771.0 | 29,014.6 | 166,425.6 | 17.88x | 5.74x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 998,600.9 | 26,113.2 | 267,597.6 | 38.24x | 10.25x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 1,662,432.6 | 26,113.2 | 381,073.7 | 63.66x | 14.59x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 1,589,028.5 | 137,397.1 | 137,397.1 | 11.57x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 1,589,028.5 | 137,397.1 | 137,397.1 | 11.57x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 1,589,028.5 | 137,397.1 | 137,397.1 | 11.57x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 1,589,028.5 | 137,397.1 | 137,397.1 | 11.57x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 1,589,028.5 | 137,397.1 | 137,397.1 | 11.57x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 1,589,028.5 | 137,397.1 | 137,397.1 | 11.57x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 1,589,028.5 | 137,397.1 | 165,219.3 | 11.57x | 1.20x | kv_read | weight_read | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 256 | rom | 1,589,028.5 | 153,483.3 | 330,032.7 | 10.35x | 2.15x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 1,819,472.2 | 165,133.8 | 404,148.7 | 11.02x | 2.45x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 2,322,541.3 | 166,403.6 | 421,784.7 | 13.96x | 2.53x | kv_read | weight_read | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 364,975.8 | 0.658 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,589,028.5 | 2.865 | kv_read | 4.35x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,644.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,644.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 364,975.8 | 0.658 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,589,028.5 | 2.865 | kv_read | 4.35x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,644.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,644.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 364,975.8 | 0.658 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,589,028.5 | 2.865 | kv_read | 4.35x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,644.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,644.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 364,975.8 | 0.658 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,589,028.5 | 2.865 | kv_read | 4.35x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,644.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,644.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 364,975.8 | 0.658 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,589,028.5 | 2.865 | kv_read | 4.35x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,644.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x20-perregion | 16,300 | 1.00 | 1.39 | 33,810.9 | 2.074 | weight_read | 0.09x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 364,975.8 | 0.658 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,589,028.5 | 2.865 | kv_read | 4.35x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,644.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.13 | 54,753.1 | 0.592 | weight_read | 0.15x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 364,975.8 | 0.658 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,589,028.5 | 2.865 | kv_read | 4.35x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 27,872.4 | 0.603 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.37 | 1.00 | 137,397.1 | 1.486 | weight_read | 0.38x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.88 | 86,452.9 | 0.935 | weight_read | 0.24x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 6.37 | 1.63 | 165,219.3 | 1.787 | layer_fixed_latency | 0.45x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 518,771.0 | 1.870 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,589,028.5 | 2.865 | kv_read | 3.06x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 29,014.6 | 0.628 | weight_read | 0.06x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.37 | 2.25 | 153,483.3 | 1.660 | weight_read | 0.30x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 4.03 | 166,425.6 | 1.800 | weight_read | 0.32x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 6.37 | 1.67 | 330,032.7 | 3.570 | kv_read | 0.64x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 998,600.9 | 1.800 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,819,472.2 | 3.280 | kv_read | 1.82x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 8.98 | 26,113.2 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.37 | 8.98 | 165,133.8 | 1.786 | weight_read | 0.17x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 6.05 | 267,597.6 | 2.895 | weight_read | 0.27x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.37 | 2.22 | 404,148.7 | 4.372 | kv_read | 0.40x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 1,662,432.6 | 2.997 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 2,322,541.3 | 4.187 | kv_read | 1.40x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 35.93 | 26,113.2 | 0.282 | weight_read | 0.02x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.37 | 35.93 | 166,403.6 | 1.800 | weight_read | 0.10x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 9.36 | 381,073.7 | 4.122 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.37 | 4.28 | 421,784.7 | 4.562 | kv_read | 0.25x |

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
| DeepSeek-V4-Flash-0731 | 1 | 18 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 57 | 1.12 | 1.001 | 1.014 | 1.01x |
| DeepSeek-V4-Flash-0731 | 256 | 57 | 4.49 | 1.042 | 1.670 | 1.60x |
| DeepSeek-V4-Flash-0731 | 1024 | 20 | 51.20 | 1.707 | 5.155 | 3.02x |
| DeepSeek-V4-Flash-0731 | 4096 | 20 | 204.80 | 4.838 | 11.909 | 2.46x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 2 | 16 | 8.56 | 4.83 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 16 | 12.41 | 6.15 | 2.02x |
| DeepSeek-V4-Flash-0731 | 8 | 16 | 15.08 | 7.51 | 2.01x |
| DeepSeek-V4-Flash-0731 | 16 | 16 | 15.91 | 8.79 | 1.81x |
| DeepSeek-V4-Flash-0731 | 32 | 16 | 16.00 | 9.86 | 1.62x |
| DeepSeek-V4-Flash-0731 | 64 | 16 | 16.00 | 10.60 | 1.51x |
| DeepSeek-V4-Flash-0731 | 256 | 16 | 16.00 | 11.05 | 1.45x |
| DeepSeek-V4-Flash-0731 | 1024 | 16 | 16.00 | 11.05 | 1.45x |
| DeepSeek-V4-Flash-0731 | 4096 | 16 | 16.00 | 11.05 | 1.45x |
| DeepSeek-V4-Flash-0731 | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 8.86 | 5.03 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 13.21 | 6.47 | 2.04x |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 16.56 | 7.99 | 2.07x |
| DeepSeek-V4-Flash-0731 | 16 | 18 | 17.82 | 9.44 | 1.89x |
| DeepSeek-V4-Flash-0731 | 32 | 18 | 17.99 | 10.67 | 1.69x |
| DeepSeek-V4-Flash-0731 | 64 | 18 | 18.00 | 11.53 | 1.56x |
| DeepSeek-V4-Flash-0731 | 256 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 1024 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 4096 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 2 | 19 | 8.99 | 5.12 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 19 | 13.57 | 6.62 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 19 | 17.26 | 8.21 | 2.10x |
| DeepSeek-V4-Flash-0731 | 16 | 19 | 18.76 | 9.75 | 1.92x |
| DeepSeek-V4-Flash-0731 | 32 | 19 | 18.99 | 11.05 | 1.72x |
| DeepSeek-V4-Flash-0731 | 64 | 19 | 19.00 | 11.97 | 1.59x |
| DeepSeek-V4-Flash-0731 | 256 | 19 | 19.00 | 12.53 | 1.52x |
| DeepSeek-V4-Flash-0731 | 1024 | 19 | 19.00 | 12.53 | 1.52x |
| DeepSeek-V4-Flash-0731 | 4096 | 19 | 19.00 | 12.53 | 1.52x |
| DeepSeek-V4-Flash-0731 | 1 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 2 | 20 | 9.11 | 5.21 | 1.75x |
| DeepSeek-V4-Flash-0731 | 4 | 20 | 13.91 | 6.76 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 20 | 17.93 | 8.43 | 2.13x |
| DeepSeek-V4-Flash-0731 | 16 | 20 | 19.68 | 10.04 | 1.96x |
| DeepSeek-V4-Flash-0731 | 32 | 20 | 19.98 | 11.42 | 1.75x |
| DeepSeek-V4-Flash-0731 | 64 | 20 | 20.00 | 12.40 | 1.61x |
| DeepSeek-V4-Flash-0731 | 256 | 20 | 20.00 | 13.00 | 1.54x |
| DeepSeek-V4-Flash-0731 | 1024 | 20 | 20.00 | 13.00 | 1.54x |
| DeepSeek-V4-Flash-0731 | 4096 | 20 | 20.00 | 13.00 | 1.54x |
| DeepSeek-V4-Flash-0731 | 1 | 24 | 5.41 | 4.10 | 1.32x |
| DeepSeek-V4-Flash-0731 | 2 | 24 | 9.51 | 5.51 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 24 | 15.05 | 7.28 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 24 | 20.35 | 9.21 | 2.21x |
| DeepSeek-V4-Flash-0731 | 16 | 24 | 23.23 | 11.14 | 2.09x |
| DeepSeek-V4-Flash-0731 | 32 | 24 | 23.93 | 12.82 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 24 | 24.00 | 14.03 | 1.71x |
| DeepSeek-V4-Flash-0731 | 256 | 24 | 24.00 | 14.78 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1024 | 24 | 24.00 | 14.79 | 1.62x |
| DeepSeek-V4-Flash-0731 | 4096 | 24 | 24.00 | 14.79 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1 | 27 | 5.47 | 4.22 | 1.30x |
| DeepSeek-V4-Flash-0731 | 2 | 27 | 9.74 | 5.70 | 1.71x |
| DeepSeek-V4-Flash-0731 | 4 | 27 | 15.74 | 7.62 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 27 | 21.92 | 9.74 | 2.25x |
| DeepSeek-V4-Flash-0731 | 16 | 27 | 25.72 | 11.88 | 2.16x |
| DeepSeek-V4-Flash-0731 | 32 | 27 | 26.84 | 13.78 | 1.95x |
| DeepSeek-V4-Flash-0731 | 64 | 27 | 26.99 | 15.16 | 1.78x |
| DeepSeek-V4-Flash-0731 | 256 | 27 | 27.00 | 16.02 | 1.68x |
| DeepSeek-V4-Flash-0731 | 1024 | 27 | 27.00 | 16.03 | 1.68x |
| DeepSeek-V4-Flash-0731 | 4096 | 27 | 27.00 | 16.03 | 1.68x |
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
| DeepSeek-V4-Flash-0731 | 1 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 2 | 37 | 10.26 | 6.23 | 1.65x |
| DeepSeek-V4-Flash-0731 | 4 | 37 | 17.39 | 8.55 | 2.03x |
| DeepSeek-V4-Flash-0731 | 8 | 37 | 25.99 | 11.20 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 37 | 32.96 | 14.00 | 2.35x |
| DeepSeek-V4-Flash-0731 | 32 | 37 | 36.11 | 16.57 | 2.18x |
| DeepSeek-V4-Flash-0731 | 64 | 37 | 36.85 | 18.50 | 1.99x |
| DeepSeek-V4-Flash-0731 | 256 | 37 | 36.97 | 19.73 | 1.87x |
| DeepSeek-V4-Flash-0731 | 1024 | 37 | 36.97 | 19.74 | 1.87x |
| DeepSeek-V4-Flash-0731 | 4096 | 37 | 36.97 | 19.74 | 1.87x |
| DeepSeek-V4-Flash-0731 | 1 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 2 | 39 | 10.34 | 6.32 | 1.64x |
| DeepSeek-V4-Flash-0731 | 4 | 39 | 17.64 | 8.71 | 2.03x |
| DeepSeek-V4-Flash-0731 | 8 | 39 | 26.64 | 11.45 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 39 | 34.22 | 14.37 | 2.38x |
| DeepSeek-V4-Flash-0731 | 32 | 39 | 37.86 | 17.07 | 2.22x |
| DeepSeek-V4-Flash-0731 | 64 | 39 | 38.78 | 19.11 | 2.03x |
| DeepSeek-V4-Flash-0731 | 256 | 39 | 38.95 | 20.40 | 1.91x |
| DeepSeek-V4-Flash-0731 | 1024 | 39 | 38.95 | 20.41 | 1.91x |
| DeepSeek-V4-Flash-0731 | 4096 | 39 | 38.95 | 20.41 | 1.91x |
| DeepSeek-V4-Flash-0731 | 1 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 42 | 10.44 | 6.45 | 1.62x |
| DeepSeek-V4-Flash-0731 | 4 | 42 | 17.97 | 8.93 | 2.01x |
| DeepSeek-V4-Flash-0731 | 8 | 42 | 27.54 | 11.80 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 42 | 36.01 | 14.90 | 2.42x |
| DeepSeek-V4-Flash-0731 | 32 | 42 | 40.42 | 17.79 | 2.27x |
| DeepSeek-V4-Flash-0731 | 64 | 42 | 41.66 | 19.97 | 2.09x |
| DeepSeek-V4-Flash-0731 | 256 | 42 | 41.91 | 21.37 | 1.96x |
| DeepSeek-V4-Flash-0731 | 1024 | 42 | 41.91 | 21.39 | 1.96x |
| DeepSeek-V4-Flash-0731 | 4096 | 42 | 41.91 | 21.39 | 1.96x |
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
| DeepSeek-V4-Flash-0731 | 1 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 44 | 10.50 | 6.53 | 1.61x |
| DeepSeek-V4-Flash-0731 | 4 | 44 | 18.17 | 9.06 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 44 | 28.09 | 12.03 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 44 | 37.14 | 15.23 | 2.44x |
| DeepSeek-V4-Flash-0731 | 32 | 44 | 42.08 | 18.24 | 2.31x |
| DeepSeek-V4-Flash-0731 | 64 | 44 | 43.56 | 20.53 | 2.12x |
| DeepSeek-V4-Flash-0731 | 256 | 44 | 43.88 | 22.00 | 1.99x |
| DeepSeek-V4-Flash-0731 | 1024 | 44 | 43.88 | 22.01 | 1.99x |
| DeepSeek-V4-Flash-0731 | 4096 | 44 | 43.88 | 22.01 | 1.99x |
| DeepSeek-V4-Flash-0731 | 1 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 46 | 10.55 | 6.61 | 1.60x |
| DeepSeek-V4-Flash-0731 | 4 | 46 | 18.36 | 9.19 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 46 | 28.60 | 12.24 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 46 | 38.22 | 15.56 | 2.46x |
| DeepSeek-V4-Flash-0731 | 32 | 46 | 43.69 | 18.69 | 2.34x |
| DeepSeek-V4-Flash-0731 | 64 | 46 | 45.43 | 21.07 | 2.16x |
| DeepSeek-V4-Flash-0731 | 256 | 46 | 45.83 | 22.61 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1024 | 46 | 45.83 | 22.63 | 2.03x |
| DeepSeek-V4-Flash-0731 | 4096 | 46 | 45.83 | 22.63 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 2 | 52 | 10.70 | 6.83 | 1.57x |
| DeepSeek-V4-Flash-0731 | 4 | 52 | 18.84 | 9.55 | 1.97x |
| DeepSeek-V4-Flash-0731 | 8 | 52 | 29.98 | 12.84 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 52 | 41.18 | 16.47 | 2.50x |
| DeepSeek-V4-Flash-0731 | 32 | 52 | 48.30 | 19.94 | 2.42x |
| DeepSeek-V4-Flash-0731 | 64 | 52 | 50.93 | 22.62 | 2.25x |
| DeepSeek-V4-Flash-0731 | 256 | 52 | 51.64 | 24.35 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1024 | 52 | 51.64 | 24.37 | 2.12x |
| DeepSeek-V4-Flash-0731 | 4096 | 52 | 51.64 | 24.37 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 55 | 10.76 | 6.93 | 1.55x |
| DeepSeek-V4-Flash-0731 | 4 | 55 | 19.05 | 9.71 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 55 | 30.58 | 13.11 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 55 | 42.52 | 16.89 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 55 | 50.48 | 20.52 | 2.46x |
| DeepSeek-V4-Flash-0731 | 64 | 55 | 53.60 | 23.34 | 2.30x |
| DeepSeek-V4-Flash-0731 | 256 | 55 | 54.49 | 25.18 | 2.16x |
| DeepSeek-V4-Flash-0731 | 1024 | 55 | 54.50 | 25.19 | 2.16x |
| DeepSeek-V4-Flash-0731 | 4096 | 55 | 54.50 | 25.19 | 2.16x |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 10.77 | 6.96 | 1.55x |
| DeepSeek-V4-Flash-0731 | 4 | 56 | 19.11 | 9.76 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 56 | 30.77 | 13.20 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 56 | 42.95 | 17.03 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 56 | 51.18 | 20.71 | 2.47x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 54.47 | 23.58 | 2.31x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 55.44 | 25.44 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1024 | 56 | 55.44 | 25.46 | 2.18x |
| DeepSeek-V4-Flash-0731 | 4096 | 56 | 55.44 | 25.46 | 2.18x |
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
| DeepSeek-V4-Flash-0731 | 1 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 60 | 10.84 | 7.08 | 1.53x |
| DeepSeek-V4-Flash-0731 | 4 | 60 | 19.35 | 9.95 | 1.95x |
| DeepSeek-V4-Flash-0731 | 8 | 60 | 31.48 | 13.54 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 60 | 44.58 | 17.56 | 2.54x |
| DeepSeek-V4-Flash-0731 | 32 | 60 | 53.91 | 21.45 | 2.51x |
| DeepSeek-V4-Flash-0731 | 64 | 60 | 57.91 | 24.50 | 2.36x |
| DeepSeek-V4-Flash-0731 | 256 | 60 | 59.18 | 26.49 | 2.23x |
| DeepSeek-V4-Flash-0731 | 1024 | 60 | 59.19 | 26.51 | 2.23x |
| DeepSeek-V4-Flash-0731 | 4096 | 60 | 59.19 | 26.51 | 2.23x |
| DeepSeek-V4-Flash-0731 | 1 | 61 | 5.76 | 4.95 | 1.16x |
| DeepSeek-V4-Flash-0731 | 2 | 61 | 10.86 | 7.12 | 1.53x |
| DeepSeek-V4-Flash-0731 | 4 | 61 | 19.41 | 10.00 | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | 61 | 31.64 | 13.62 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 61 | 44.97 | 17.68 | 2.54x |
| DeepSeek-V4-Flash-0731 | 32 | 61 | 54.57 | 21.63 | 2.52x |
| DeepSeek-V4-Flash-0731 | 64 | 61 | 58.76 | 24.72 | 2.38x |
| DeepSeek-V4-Flash-0731 | 256 | 61 | 60.10 | 26.74 | 2.25x |
| DeepSeek-V4-Flash-0731 | 1024 | 61 | 60.11 | 26.76 | 2.25x |
| DeepSeek-V4-Flash-0731 | 4096 | 61 | 60.11 | 26.76 | 2.25x |
| DeepSeek-V4-Flash-0731 | 1 | 63 | 5.77 | 4.97 | 1.16x |
| DeepSeek-V4-Flash-0731 | 2 | 63 | 10.89 | 7.17 | 1.52x |
| DeepSeek-V4-Flash-0731 | 4 | 63 | 19.51 | 10.08 | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | 63 | 31.96 | 13.78 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 63 | 45.72 | 17.93 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 63 | 55.87 | 21.98 | 2.54x |
| DeepSeek-V4-Flash-0731 | 64 | 63 | 60.43 | 25.16 | 2.40x |
| DeepSeek-V4-Flash-0731 | 256 | 63 | 61.94 | 27.24 | 2.27x |
| DeepSeek-V4-Flash-0731 | 1024 | 63 | 61.95 | 27.26 | 2.27x |
| DeepSeek-V4-Flash-0731 | 4096 | 63 | 61.95 | 27.26 | 2.27x |
| DeepSeek-V4-Flash-0731 | 1 | 66 | 5.78 | 5.01 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 66 | 10.93 | 7.26 | 1.51x |
| DeepSeek-V4-Flash-0731 | 4 | 66 | 19.66 | 10.21 | 1.93x |
| DeepSeek-V4-Flash-0731 | 8 | 66 | 32.41 | 14.01 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 66 | 46.79 | 18.29 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 66 | 57.74 | 22.49 | 2.57x |
| DeepSeek-V4-Flash-0731 | 64 | 66 | 62.88 | 25.80 | 2.44x |
| DeepSeek-V4-Flash-0731 | 256 | 66 | 64.66 | 27.97 | 2.31x |
| DeepSeek-V4-Flash-0731 | 1024 | 66 | 64.68 | 28.00 | 2.31x |
| DeepSeek-V4-Flash-0731 | 4096 | 66 | 64.68 | 28.00 | 2.31x |
| DeepSeek-V4-Flash-0731 | 1 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 68 | 10.96 | 7.32 | 1.50x |
| DeepSeek-V4-Flash-0731 | 4 | 68 | 19.76 | 10.29 | 1.92x |
| DeepSeek-V4-Flash-0731 | 8 | 68 | 32.69 | 14.16 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 68 | 47.47 | 18.53 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 68 | 58.95 | 22.82 | 2.58x |
| DeepSeek-V4-Flash-0731 | 64 | 68 | 64.48 | 26.21 | 2.46x |
| DeepSeek-V4-Flash-0731 | 256 | 68 | 66.45 | 28.45 | 2.34x |
| DeepSeek-V4-Flash-0731 | 1024 | 68 | 66.47 | 28.47 | 2.33x |
| DeepSeek-V4-Flash-0731 | 4096 | 68 | 66.47 | 28.47 | 2.33x |
| DeepSeek-V4-Flash-0731 | 1 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 69 | 10.97 | 7.34 | 1.49x |
| DeepSeek-V4-Flash-0731 | 4 | 69 | 19.80 | 10.33 | 1.92x |
| DeepSeek-V4-Flash-0731 | 8 | 69 | 32.83 | 14.23 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 69 | 47.80 | 18.64 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 69 | 59.55 | 22.98 | 2.59x |
| DeepSeek-V4-Flash-0731 | 64 | 69 | 65.27 | 26.42 | 2.47x |
| DeepSeek-V4-Flash-0731 | 256 | 69 | 67.34 | 28.68 | 2.35x |
| DeepSeek-V4-Flash-0731 | 1024 | 69 | 67.36 | 28.71 | 2.35x |
| DeepSeek-V4-Flash-0731 | 4096 | 69 | 67.36 | 28.71 | 2.35x |
| DeepSeek-V4-Flash-0731 | 1 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 2 | 73 | 11.02 | 7.45 | 1.48x |
| DeepSeek-V4-Flash-0731 | 4 | 73 | 19.97 | 10.48 | 1.90x |
| DeepSeek-V4-Flash-0731 | 8 | 73 | 33.34 | 14.52 | 2.30x |
| DeepSeek-V4-Flash-0731 | 16 | 73 | 49.06 | 19.09 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 73 | 61.84 | 23.61 | 2.62x |
| DeepSeek-V4-Flash-0731 | 64 | 73 | 68.37 | 27.22 | 2.51x |
| DeepSeek-V4-Flash-0731 | 256 | 73 | 70.85 | 29.60 | 2.39x |
| DeepSeek-V4-Flash-0731 | 1024 | 73 | 70.86 | 29.62 | 2.39x |
| DeepSeek-V4-Flash-0731 | 4096 | 73 | 70.86 | 29.62 | 2.39x |
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
| DeepSeek-V4-Flash-0731 | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 110 | 11.29 | 8.23 | 1.37x |
| DeepSeek-V4-Flash-0731 | 4 | 110 | 20.98 | 11.57 | 1.81x |
| DeepSeek-V4-Flash-0731 | 8 | 110 | 36.56 | 16.69 | 2.19x |
| DeepSeek-V4-Flash-0731 | 16 | 110 | 57.43 | 22.44 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 110 | 78.28 | 28.44 | 2.75x |
| DeepSeek-V4-Flash-0731 | 64 | 110 | 92.27 | 33.39 | 2.76x |
| DeepSeek-V4-Flash-0731 | 256 | 110 | 99.32 | 36.75 | 2.70x |
| DeepSeek-V4-Flash-0731 | 1024 | 110 | 99.38 | 36.78 | 2.70x |
| DeepSeek-V4-Flash-0731 | 4096 | 110 | 99.38 | 36.78 | 2.70x |
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
| DeepSeek-V4-Flash-0731 | 1 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 2 | 146 | 11.43 | 8.76 | 1.30x |
| DeepSeek-V4-Flash-0731 | 4 | 146 | 21.49 | 12.35 | 1.74x |
| DeepSeek-V4-Flash-0731 | 8 | 146 | 38.28 | 18.17 | 2.11x |
| DeepSeek-V4-Flash-0731 | 16 | 146 | 62.23 | 24.74 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 146 | 88.72 | 31.93 | 2.78x |
| DeepSeek-V4-Flash-0731 | 64 | 146 | 109.04 | 37.99 | 2.87x |
| DeepSeek-V4-Flash-0731 | 256 | 146 | 120.77 | 42.16 | 2.86x |
| DeepSeek-V4-Flash-0731 | 1024 | 146 | 120.87 | 42.20 | 2.86x |
| DeepSeek-V4-Flash-0731 | 4096 | 146 | 120.87 | 42.20 | 2.86x |
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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 894.40 | 31.2% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 190.81 | 79.7% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4-Flash-0731 | sram | interleaved | 128 B | 1.00x |
| DeepSeek-V4-Flash-0731 | hbm | interleaved | 32 B | 1.00x |

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
| DeepSeek-V4-Flash-0731 | 1 | 18 | 32.17% | 15.33 | 2.65 |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 32.17% | 15.33 | 2.65 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 0.38% | 0.57 | 2.65 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 0.38% | 0.57 | 2.65 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 0.38% | 0.57 | 2.65 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 0.38% | 0.57 | 2.65 |
| DeepSeek-V4-Flash-0731 | 64 | 1 | 0.42% | 0.64 | 2.65 |
| DeepSeek-V4-Flash-0731 | 256 | 1 | 1.69% | 2.55 | 2.65 |

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
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 271.3 | 10,309.9 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 271.3 | 10,309.9 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 271.3 | 10,309.9 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 271.3 | 10,309.9 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 271.3 | 10,309.9 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 271.3 | 10,309.9 |
| DeepSeek-V4-Flash-0731 | 64 | 3.92% | 13.5 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 163.5 | 10,461.4 |
| DeepSeek-V4-Flash-0731 | 256 | 14.77% | 29.5 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 41.5 | 10,611.8 |
| DeepSeek-V4-Flash-0731 | 1024 | 47.22% | 77.3 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 10.4 | 10,629.0 |
| DeepSeek-V4-Flash-0731 | 4096 | 92.24% | 143.5 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2.6 | 10,591.2 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 2 |
| gpu | link_latency | 949 |
| gpu | weight_read | 489 |
| rom | compute | 566 |
| rom | infeasible | 2552 |
| rom | kv_read | 137 |
| rom | layer_fixed_latency | 857 |
| rom | link_latency | 1006 |
| rom | weight_read | 462 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2552 |

## Mechanical consistency audit

**FAIL** over 143,119 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x36', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x40', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x43', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x53', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x59', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x61', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x62', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x70', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x105', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x140', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x36', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x40', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x43', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x53', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x59', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x61', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x62', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x70', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x105', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x140', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x36', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x40', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x43', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x53', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x59', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x61', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x62', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x70', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x105', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x140', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x36', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x40', 'DeepSeek-V4-Flash-0731', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 75 |
| derived | 49 |
| assumed | 84 |

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

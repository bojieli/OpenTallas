# Area-constrained roofline: n6_vs_a100-flash-8k

> CONTEXT-LADDER RUNG of n6_vs_a100: DeepSeek-V4-Flash-0731 at 8,192 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 13x (ROM-N6-native-SRAMKV-wafer-pipeline-x12-romfill, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 45 devices. On the GPU side the correction reaches 7x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 20 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Flash-0731 takes 41 x 815 mm2 (33,415 mm2, array, KV in SRAM) at 3,181 tok/s per user and 95 tok/s per 1,000 mm2, holding 1 session, against 40 copies of one unified HBM die at the same silicon: 9.1x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Flash-0731 on 60,310 mm2 of ROM silicon at 3,436 tok/s per user against 60,298 mm2 of a100_sxm_80gb-x73-hybrid at 339 tok/s: **10.1x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 85,939 resident sessions against the GPU cluster's 82,086. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on DeepSeek-V4-Flash-0731 at batch 1, the iso-area GPU cluster is 672 devices. Cut as one serial pipeline that is 84 stages and 1,462 us of link latency per token; but the model has 43 layers, so at most 43 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 1,365 us. The iso-area per-user ratio at that point falls from 9.6x to 9.3x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 2.63x to it.** At 33,415 mm2 on DeepSeek-V4-Flash-0731 the pipeline-only GPU delivers 132.94 tok/s and the same silicon running hybrid delivers 350 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.00x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 12.06x (DeepSeek-V4-Flash-0731, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 293 to 11,493 tok/s, and its rate with every slot occupied from 11,143 to 11,493. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 38 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,218 us over NVLink, capping per-user decode at 821 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 165.6 us and cap it at 6,040 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 5.2x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 10 operating points and an array 8; on tokens per second per square millimetre the same points go 6 to the array and 4 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 53 of 4286 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 58.9x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 11.54x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.03x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4-Flash-0731 at 8,192 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-hybrid-x41`** -- 41 x 815 mm2 reticle dies, 33,415 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **3,181.4 tok/s per user** (0.31 ms/token), binding on `layer_fixed_latency`
- **95.2 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 3,181 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 2,065 W at 0.062 W/mm2, 649.2 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 40 copies of one unified HBM die -- `a100_sxm_80gb-x40-hybrid`, 33,040 mm2, area ratio 1.0113 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 33,415 | 33,040 | 1.0113 |
| user tok/s | 3,181.4 | 349.5 | 9.10x |
| aggregate tok/s | 3,181 | 1,748 | 0.60x |
| resident sessions | 1 | 43,762 | -- |
| J/token | 0.6492 | 17.7075 | 27.3x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 43,762 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x40-hybrid` at 33,040 mm2 and 349.5 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-array-hw-hybrid-x45` | 36,675 | 3,298.5 | 89.9 | 52,260 | 9.67x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 3,440.9 | 62.1 | 78,971 | 10.08x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x36` | 29,340 | 2,654.4 | 90.5 | 1 | 7.81x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-hybrid-x41` | 33,415 | 3,181.4 | 95.2 | 1 | 9.10x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x41` | 33,415 | 3,181.4 | 95.2 | -- | 95.2 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x44` | 35,860 | 3,240.6 | 90.4 | 24.2 | 95.2 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x45` | 36,675 | 3,298.5 | 89.9 | 35.9 | 95.2 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x47` | 38,305 | 3,330.6 | 86.9 | 30.5 | 95.2 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x53` | 43,195 | 3,342.1 | 77.4 | 16.4 | 95.2 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x55` | 44,825 | 3,375.2 | 75.3 | 17.0 | 95.2 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x56` | 45,640 | 3,379.7 | 74.1 | 16.2 | 95.2 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x67` | 54,605 | 3,436.8 | 62.9 | 12.1 | 95.2 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 3,440.9 | 62.1 | 11.8 | 95.2 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x41` **<-- recommended** | 33,415 | 41 | 3,181.4 | 3,181 | 95.2 | 1 | `layer_fixed_latency` | 2,065 | 649.2 | `a100_sxm_80gb-x40-hybrid` | 9.10x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x44` | 35,860 | 44 | 3,240.6 | 3,241 | 90.4 | 1 | `layer_fixed_latency` | 2,341 | 722.3 | `a100_sxm_80gb-x43-hybrid` | 9.56x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x45` | 36,675 | 45 | 3,298.5 | 19,791 | 89.9 | 52,260 | `layer_fixed_latency` | 3,229 | 940.3 | `a100_sxm_80gb-x44-hybrid` | 9.67x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x47` | 38,305 | 47 | 3,330.6 | 19,984 | 86.9 | 54,583 | `layer_fixed_latency` | 3,495 | 1,010.6 | `a100_sxm_80gb-x46-hybrid` | 9.65x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x53` | 43,195 | 53 | 3,342.1 | 3,342 | 77.4 | 1 | `layer_fixed_latency` | 3,405 | 1,018.7 | `a100_sxm_80gb-x52-hybrid` | 9.77x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x55` | 44,825 | 55 | 3,375.2 | 23,626 | 75.3 | 63,874 | `layer_fixed_latency` | 4,581 | 1,310.7 | `a100_sxm_80gb-x54-hybrid` | 9.77x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x56` | 45,640 | 56 | 3,379.7 | 23,658 | 74.1 | 65,035 | `layer_fixed_latency` | 4,713 | 1,348.1 | `a100_sxm_80gb-x55-hybrid` | 9.74x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x67` | 54,605 | 67 | 3,436.8 | 58,426 | 62.9 | 77,810 | `layer_fixed_latency` | 6,437 | 1,748.8 | `a100_sxm_80gb-x66-hybrid` | 10.11x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 68 | 3,440.9 | 58,495 | 62.1 | 78,971 | `layer_fixed_latency` | 6,569 | 1,785.2 | `a100_sxm_80gb-x67-hybrid` | 10.08x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 354 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x41` | 33,415 | 3,181.4 | 95.2 | 1 |
| array | 354 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 3,440.9 | 62.1 | 78,971 |
| array | 354 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x36` | 29,340 | 2,654.4 | 90.5 | 1 |
| wafer | 80 | densest | `ROM-N6-native-HBMKV-wafer-pipeline-x1` | 46,225 | 2,698.3 | 58.4 | 9,987 |
| wafer | 80 | fastest | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,133.6 | 33.9 | 19,975 |
| wafer | 80 | smallest | `ROM-N6-native-HBMKV-wafer-pipeline-x1` | 46,225 | 2,698.3 | 58.4 | 9,987 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 3,440.9 | 58,495 | 78,971 | 6,569 | 1,785.2 | `layer_fixed_latency` | `a100_sxm_80gb-x67-hybrid` | 341.4 | 75,118 | 29,516.1 | 1.001 | 10.08x | 16.5x |
| 1 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,133.6 | 90,874 | 19,975 | 9,301 | 2,751.1 | `layer_fixed_latency` | `a100_sxm_80gb-x112-hybrid` | 345.9 | 127,378 | 47,935.8 | 0.999 | 9.06x | 17.4x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill` | 90,465 | 3,419.5 | 95,747 | 128,909 | 10,789 | 2,946.0 | `layer_fixed_latency` | `a100_sxm_80gb-x110-hybrid` | 344.3 | 125,056 | 47,311.4 | 0.996 | 9.93x | 16.1x |
| 1 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,133.6 | -- | 19,975 | -- | 2,751.1 | -- | -- | -- | -- | -- | 0.979 | 0.92x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 3,440.9 | 58,495 | 78,971 | 6,569 | 896.5 | `layer_fixed_latency` | `a100_sxm_80gb-x67-hybrid` | 341.4 | 75,118 | 15,350.1 | 1.001 | 10.08x | 17.1x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,133.6 | 90,874 | 19,975 | 9,301 | 1,379.4 | `layer_fixed_latency` | `a100_sxm_80gb-x112-hybrid` | 345.9 | 127,378 | 24,560.0 | 0.999 | 9.06x | 17.8x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill` | 90,465 | 3,419.5 | 95,747 | 128,909 | 10,789 | 1,476.9 | `layer_fixed_latency` | `a100_sxm_80gb-x110-hybrid` | 344.3 | 125,056 | 24,247.8 | 0.996 | 9.93x | 16.4x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,133.6 | -- | 19,975 | -- | 1,379.4 | -- | -- | -- | -- | -- | 0.979 | 0.92x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 3,440.9 | 58,495 | 78,971 | 6,569 | 452.1 | `layer_fixed_latency` | `a100_sxm_80gb-x67-hybrid` | 341.4 | 75,118 | 8,267.1 | 1.001 | 10.08x | 18.3x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,133.6 | 90,874 | 19,975 | 9,301 | 693.6 | `layer_fixed_latency` | `a100_sxm_80gb-x112-hybrid` | 345.9 | 127,378 | 12,872.1 | 0.999 | 9.06x | 18.6x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill` | 90,465 | 3,419.5 | 95,747 | 128,909 | 10,789 | 742.3 | `layer_fixed_latency` | `a100_sxm_80gb-x110-hybrid` | 344.3 | 125,056 | 12,716.0 | 0.996 | 9.93x | 17.1x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,133.6 | -- | 19,975 | -- | 693.6 | -- | -- | -- | -- | -- | 0.979 | 0.92x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 3,440.9 | 58,495 | 78,971 | 6,569 | 229.9 | `layer_fixed_latency` | `a100_sxm_80gb-x67-hybrid` | 341.4 | 75,118 | 4,725.6 | 1.001 | 10.08x | 20.6x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,133.6 | 90,874 | 19,975 | 9,301 | 350.7 | `layer_fixed_latency` | `a100_sxm_80gb-x112-hybrid` | 345.9 | 127,378 | 7,028.1 | 0.999 | 9.06x | 20.0x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill` | 90,465 | 3,419.5 | 95,747 | 128,909 | 10,789 | 375.0 | `layer_fixed_latency` | `a100_sxm_80gb-x110-hybrid` | 344.3 | 125,056 | 6,950.1 | 0.996 | 9.93x | 18.5x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,133.6 | -- | 19,975 | -- | 350.7 | -- | -- | -- | -- | -- | 0.979 | 0.92x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 3,440.9 | 58,495 | 78,971 | 6,569 | 118.8 | `layer_fixed_latency` | `a100_sxm_80gb-x67-hybrid` | 315.0 | 75,118 | 2,743.1 | 1.001 | 10.92x | 23.1x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,133.6 | 90,874 | 19,975 | 9,301 | 179.2 | `layer_fixed_latency` | `a100_sxm_80gb-x112-hybrid` | 340.8 | 127,378 | 4,047.1 | 0.999 | 9.19x | 22.6x |
| 16 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill` | 90,465 | 3,419.5 | 95,747 | 128,909 | 10,789 | 191.4 | `layer_fixed_latency` | `a100_sxm_80gb-x110-hybrid` | 339.2 | 125,056 | 4,007.8 | 0.996 | 10.08x | 20.9x |
| 16 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 3,133.6 | -- | 19,975 | -- | 179.2 | -- | -- | -- | -- | -- | 0.979 | 0.92x wafer/array | -- |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 120,620 | 3,402.5 | 125,891 | 171,879 | 14,372 | 130.8 | `layer_fixed_latency` | `a100_sxm_80gb-x146-hybrid` | 316.9 | 166,864 | 2,928.5 | 1.000 | 10.74x | 22.4x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 3,105.4 | 177,009 | 39,950 | 18,565 | 180.8 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 335.2 | 257,449 | 4,097.0 | 0.999 | 9.27x | 22.7x |
| 32 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 3,390.0 | 193,231 | 263,625 | 22,045 | 197.2 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 335.2 | 257,449 | 4,097.0 | 1.000 | 10.11x | 20.8x |
| 32 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 3,105.4 | -- | 39,950 | -- | 180.8 | -- | -- | -- | -- | -- | 1.001 | 0.92x wafer/array | -- |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 3,390.5 | 288,193 | 394,857 | 33,009 | 149.6 | `layer_fixed_latency` | `a100_sxm_80gb-x335-hybrid` | 316.0 | 386,359 | 3,292.6 | 1.001 | 10.73x | 22.0x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 3,105.4 | 354,019 | 79,900 | 37,129 | 180.8 | `layer_fixed_latency` | `a100_sxm_80gb-x448-hybrid` | 329.3 | 517,591 | 4,150.5 | 0.999 | 9.43x | 23.0x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 2,971.8 | 760,776 | 394,857 | 36,052 | 47.4 | `layer_fixed_latency` | `a100_sxm_80gb-x335-hybrid` | 214.1 | 386,359 | 1,363.1 | 1.001 | 13.88x | 28.8x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,064.1 | 1,044,870 | 119,850 | 59,677 | 73.5 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 271.7 | 777,732 | 2,021.7 | 0.999 | 11.28x | 27.5x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 1,387.9 | 1,421,223 | 394,857 | 39,470 | 27.8 | `compute` | `a100_sxm_80gb-x335-hybrid` | 107.3 | 386,359 | 830.8 | 1.001 | 12.93x | 29.9x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 2,330.5 | 2,386,433 | 119,850 | 68,135 | 28.6 | `compute` | `a100_sxm_80gb-x672-hybrid` | 155.9 | 777,732 | 1,088.6 | 0.999 | 14.95x | 38.1x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 412.3 | 1,688,661 | 394,857 | 39,919 | 23.6 | `compute` | `a100_sxm_80gb-x335-hybrid` | 46.4 | 386,359 | 493.6 | 1.001 | 8.88x | 20.9x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 843.4 | 3,454,700 | 119,850 | 71,208 | 20.6 | `compute` | `a100_sxm_80gb-x672-hybrid` | 69.9 | 777,732 | 655.8 | 0.999 | 12.06x | 31.8x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x41` | 33,415 | array | SRAM | 1 |
| 2 | `ROM-N6-native-HBMKV-array-hw-hybrid-x41` | 33,415 | array | HBM | 47,615 |
| 4-8 | `ROM-N6-native-HBMKV-array-hw-hybrid-x45` | 36,675 | array | HBM | 52,260 |
| 16 | `ROM-N6-native-HBMKV-array-hw-hybrid-x47` | 38,305 | array | HBM | 54,583 |
| 32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x55` | 44,825 | array | HBM | 63,874 |
| 64-256 | `ROM-N6-native-HBMKV-wafer-pipeline-x1` | 46,225 | wafer | HBM | 9,987 |
| 1024-4096 | `ROM-N6-native-HBMKV-wafer-pipeline-x2` | 92,450 | wafer | HBM | 19,975 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 38, 41, 45, 47, 55, 56, 57, 67, 74, 111, 113, 148, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 38, 41, 45, 47, 55, 56, 57, 67, 68, 74, 111, 113, 148, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 36, 41, 44, 46, 50, 53, 57, 70, 105, 113, 140, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 36, 41, 44, 46, 50, 53, 57, 70, 105, 113, 140, 170, 227, 340 |

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
| DeepSeek-V4-Flash-0731 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x41` | 1 | 16 | 6.51 | hierarchical, one_shot | 247.85 | 43.43 | 34.73 | 34.52 | 3,181.4 |
| DeepSeek-V4-Flash-0731 | `a100_sxm_80gb-x40-hybrid` | 1 | 8 | 5.51 | measured_floor | 894.40 | 1,237.87 | 851.19 | 457.99 | 349.5 |
| DeepSeek-V4-Flash-0731 | `a100_sxm_80gb-x40-hybrid` | 64 | 8 | 5.51 | measured_floor | 946.40 | 1,790.23 | 3,532.36 | 546.20 | 166.9 |

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

- **0 of 4,286 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 81% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 400 | 0 | 49.0% | 80.7% | 0.391 | 79% |
| gpu | small array (1,600-5,000 mm2) | 30 | 0 | 60.3% | 80.4% | 0.389 | 60% |
| gpu | wafer (>=40,000 mm2) | 840 | 0 | 48.5% | 80.0% | 0.387 | 89% |
| rom | large array (5,000-40,000 mm2) | 960 | 0 | 17.9% | 34.9% | 0.175 | 96% |
| rom | wafer (>=40,000 mm2) | 2,056 | 0 | 23.9% | 38.4% | 0.192 | 96% |

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
| DeepSeek-V4-Flash-0731 | 1 | 36,675 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x45` | 0.940255 | 3,229.3 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x44-hybrid` | 19.805681 | 8,776.8 | link_latency | 21.06x |
| DeepSeek-V4-Flash-0731 | 2 | 36,675 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x45` | 0.474003 | 3,229.3 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x44-hybrid` | 10.494913 | 8,776.8 | link_latency | 22.14x |
| DeepSeek-V4-Flash-0731 | 4 | 36,675 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x45` | 0.240877 | 3,229.3 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x44-hybrid` | 5.839529 | 8,776.8 | link_latency | 24.24x |
| DeepSeek-V4-Flash-0731 | 8 | 44,825 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x55` | 0.171301 | 4,762.4 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x54-hybrid` | 3.944535 | 10,741.8 | link_latency | 23.03x |
| DeepSeek-V4-Flash-0731 | 16 | 44,825 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x55` | 0.090976 | 4,789.8 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x54-hybrid` | 2.319102 | 11,303.0 | link_latency | 25.49x |
| DeepSeek-V4-Flash-0731 | 32 | 54,605 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x67` | 0.064956 | 6,845.2 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x66-hybrid` | 1.702351 | 14,538.6 | weight_read | 26.21x |
| DeepSeek-V4-Flash-0731 | 64 | 120,620 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 0.071626 | 15,276.0 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x146-hybrid` | 1.814538 | 31,495.8 | weight_read | 25.33x |
| DeepSeek-V4-Flash-0731 | 256 | 277,100 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.047389 | 36,052.0 | layer_fixed_latency | `DSV4-Flash/a100_sxm_80gb-x335-hybrid` | 1.363130 | 74,710.0 | weight_read | 28.76x |
| DeepSeek-V4-Flash-0731 | 1024 | 554,700 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 0.028551 | 68,134.6 | compute | `DSV4-Flash/a100_sxm_80gb-x672-hybrid` | 1.088568 | 173,729.5 | weight_read | 38.13x |
| DeepSeek-V4-Flash-0731 | 4096 | 554,700 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 0.020612 | 71,207.9 | compute | `DSV4-Flash/a100_sxm_80gb-x672-hybrid` | 0.655837 | 187,887.7 | weight_read | 31.82x |

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
| DeepSeek-V4-Flash-0731 | 8,192 | 284 B | 166.9 GB | 4.70 | 0.029 GB | 0.062 GB | 387.3 |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 3,682.7 | wafer-pipeline | 2,698.3 | wafer-pipeline | 1.36x | 872.3 | pipeline | 348.7 | hybrid | 2.50x | 4.22x | 7.74x | 1.83x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 3,680.6 | wafer-pipeline | 3,133.6 | wafer-hybrid | 1.17x | 917.1 | pipeline | 345.9 | hybrid | 2.65x | 4.01x | 9.06x | 2.26x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 3,680.8 | wafer-pipeline | 3,103.9 | wafer-hybrid | 1.19x | 933.1 | pipeline | 343.1 | hybrid | 2.72x | 3.94x | 9.05x | 2.29x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 3,680.8 | wafer-pipeline | 3,105.4 | wafer-hybrid | 1.19x | 941.3 | pipeline | 340.4 | hybrid | 2.77x | 3.91x | 9.12x | 2.33x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 3,680.8 | wafer-pipeline | 3,103.9 | wafer-hybrid | 1.19x | 949.6 | pipeline | 335.0 | hybrid | 2.83x | 3.88x | 9.26x | 2.39x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 3,680.8 | wafer-pipeline | 3,105.4 | wafer-hybrid | 1.19x | 953.9 | pipeline | 334.7 | hybrid | 2.85x | 3.86x | 9.28x | 2.40x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 3,680.8 | wafer-pipeline | 3,105.4 | wafer-hybrid | 1.19x | 958.1 | pipeline | 334.7 | hybrid | 2.86x | 3.84x | 9.28x | 2.42x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.83x to 2.42x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 3,440.9 | 58,495.5 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x67-hybrid | 55,342 | 1.00x | hybrid | 1,251.24 | 341.4 | 3,073.0 | link_latency | 10.08x | 6.58x | 25.91x | 10.08x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x36 | 29,340 | 2,654.4 | 2,654.4 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x36-hybrid | 29,736 | 0.99x | hybrid | 1,126.41 | 339.7 | 1,698.6 | link_latency | 7.81x | 0.55x | 19.94x | 7.81x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 3,440.9 | 58,495.5 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x67-hybrid | 55,342 | 1.00x | hybrid | 1,251.24 | 341.4 | 3,073.0 | link_latency | 10.08x | 6.58x | 25.91x | 10.08x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x38 | 30,970 | 2,043.7 | 4,087.5 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 1,126.41 | 342.4 | 1,712.2 | link_latency | 5.97x | 0.83x | 15.36x | 5.97x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 3,440.9 | 58,495.5 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x67-hybrid | 55,342 | 1.00x | hybrid | 1,251.24 | 341.4 | 3,073.0 | link_latency | 10.08x | 6.58x | 25.91x | 10.08x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x38 | 30,970 | 1,601.7 | 6,406.7 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 1,126.41 | 342.4 | 1,712.2 | link_latency | 4.68x | 1.30x | 12.04x | 4.68x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 3,440.9 | 58,495.5 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x67-hybrid | 55,342 | 1.00x | hybrid | 1,251.24 | 341.4 | 3,073.0 | link_latency | 10.08x | 6.58x | 25.91x | 10.08x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x38 | 30,970 | 1,053.0 | 8,424.1 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 1,160.16 | 321.7 | 2,573.8 | link_latency | 3.27x | 1.71x | 7.91x | 3.27x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 3,440.9 | 58,495.5 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x67-hybrid | 55,342 | 1.00x | hybrid | 1,187.61 | 315.0 | 5,039.7 | link_latency | 10.92x | 6.58x | 25.91x | 10.92x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x38 | 30,970 | 622.8 | 9,965.1 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 1,250.17 | 277.8 | 4,445.1 | weight_read | 2.24x | 2.02x | 4.68x | 2.24x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill | 120,620 | 3,402.5 | 125,891.2 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x146-hybrid | 120,596 | 1.00x | hybrid | 1,224.24 | 316.9 | 10,139.4 | link_latency | 10.74x | 6.49x | 25.62x | 10.74x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x38 | 30,970 | 337.2 | 10,791.8 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 1,430.19 | 220.4 | 7,051.4 | weight_read | 1.53x | 1.53x | 2.53x | 1.53x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 3,390.5 | 288,192.6 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 1,422.40 | 316.0 | 20,226.8 | link_latency | 10.73x | 6.48x | 25.53x | 10.73x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x38 | 30,970 | 177.0 | 11,328.7 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 1,790.23 | 159.9 | 10,232.5 | weight_read | 1.11x | 1.11x | 1.59x | 1.11x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,064.1 | 1,044,870.3 | layer_fixed_latency | DSV4-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,470.61 | 271.7 | 69,565.9 | link_latency | 11.28x | 11.71x | 23.08x | 11.66x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x38 | 30,970 | 45.0 | 11,518.8 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 4,431.55 | 73.7 | 18,858.1 | weight_read | 0.61x | 0.61x | 0.84x | 0.61x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2,330.5 | 2,386,433.1 | compute | DSV4-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,600.26 | 155.9 | 159,594.4 | weight_read | 14.95x | 14.95x | 20.01x | 15.93x |
| DeepSeek-V4-Flash-0731 | 1024 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x38 | 30,970 | 11.3 | 11,543.5 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 14,982.35 | 36.3 | 37,168.6 | link_latency | 0.31x | 0.31x | 0.54x | 0.31x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 843.4 | 3,454,699.6 | compute | DSV4-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 2,727.08 | 69.9 | 286,485.6 | weight_read | 12.06x | 12.06x | 14.57x | 12.75x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x38 | 30,970 | 2.8 | 11,493.1 | compute | DSV4-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 25,174.85 | 19.7 | 80,841.5 | link_latency | 0.14x | 0.14x | 0.25x | 0.14x |

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
| DeepSeek-V4-Flash-0731 | 6 | 4,956 | 134.6 | 322.6 | — | tensor | 1,108.10 | 35.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 18 | 14,868 | 134.0 | 214.4 | 321.4 | hybrid | 1,119.72 | 36.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 20 | 16,520 | 133.9 | 215.6 | 332.6 | hybrid | 1,119.72 | 37.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 22 | 18,172 | 133.8 | 216.5 | 342.3 | hybrid | 1,119.72 | 38.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 36 | 29,736 | 133.1 | 213.6 | 339.7 | hybrid | 1,126.41 | 38.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 37 | 30,562 | 133.1 | 213.6 | 342.4 | hybrid | 1,126.41 | 38.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 40 | 33,040 | 132.9 | 213.7 | 349.5 | hybrid | 1,237.87 | 43.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 43 | 35,518 | 132.8 | 212.3 | 338.9 | hybrid | 1,129.75 | 38.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 44 | 36,344 | 132.8 | 212.3 | 341.2 | hybrid | 1,129.75 | 38.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 45 | 37,170 | 132.8 | 212.3 | 343.3 | hybrid | 1,241.22 | 42.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 46 | 37,996 | 132.8 | 212.2 | 345.3 | hybrid | 1,241.22 | 42.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 49 | 40,474 | 132.8 | 211.1 | 336.1 | hybrid | 1,133.09 | 38.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 52 | 42,952 | 132.8 | 210.9 | 342.0 | hybrid | 1,244.56 | 42.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 54 | 44,604 | 132.8 | 210.8 | 345.5 | hybrid | 1,244.56 | 43.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 55 | 45,430 | 132.8 | 210.8 | 347.1 | hybrid | 1,244.56 | 43.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 56 | 46,256 | 132.8 | 210.7 | 348.7 | hybrid | 1,244.56 | 43.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 66 | 54,516 | 132.8 | 192.5 | 340.0 | hybrid | 1,139.77 | 38.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 67 | 55,342 | 132.8 | 192.5 | 341.4 | hybrid | 1,251.24 | 42.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 69 | 56,994 | 132.8 | 192.3 | 344.1 | hybrid | 1,251.24 | 43.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 73 | 60,298 | 132.8 | 191.5 | 339.2 | hybrid | 1,143.11 | 38.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 104 | 85,904 | 132.8 | 187.6 | 346.3 | hybrid | 1,264.61 | 43.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 110 | 90,860 | 132.8 | 186.8 | 344.3 | hybrid | 1,267.95 | 43.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 111 | 91,686 | 132.8 | 186.7 | 345.1 | hybrid | 1,267.95 | 43.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 112 | 92,512 | 132.8 | 186.6 | 345.9 | hybrid | 1,267.95 | 43.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 138 | 113,988 | 132.8 | 183.1 | 340.6 | hybrid | 1,281.31 | 43.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 146 | 120,596 | 132.8 | 182.1 | 340.4 | hybrid | 1,284.65 | 43.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 168 | 138,768 | 132.8 | 179.5 | 343.1 | hybrid | 1,291.34 | 44.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 224 | 185,024 | 132.8 | 173.0 | 340.4 | hybrid | 1,314.73 | 44.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 335 | 276,710 | 132.8 | 139.7 | 334.8 | hybrid | 1,361.51 | 45.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 336 | 277,536 | 132.8 | 139.7 | 335.0 | hybrid | 1,361.51 | 45.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 448 | 370,048 | 132.8 | 132.0 | 334.7 | hybrid | 1,364.85 | 45.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 672 | 555,072 | 132.8 | 119.0 | 334.7 | hybrid | 1,364.85 | 45.7% | link_latency |

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
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x50 | DeepSeek-V4-Flash-0731 | 50 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x41 | DeepSeek-V4-Flash-0731 | 41 | tensor | rom_package_ucie | rom_board_serdes | 172 | 59.94 us | 1,668.2 tok/s | 16,682.3 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 11 on rom_board_serdes (traversals 6.6) = 57.83 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x46 | DeepSeek-V4-Flash-0731 | 46 | hybrid | rom_package_ucie | rom_board_serdes | 97 | 3.27 us | 30,615.2 tok/s | 306,152.1 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 11 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.15 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x50 | DeepSeek-V4-Flash-0731 | 50 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-tensor-x36 | DeepSeek-V4-Flash-0731 | 36 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x41 | DeepSeek-V4-Flash-0731 | 41 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x68 | DeepSeek-V4-Flash-0731 | 68 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x41 | DeepSeek-V4-Flash-0731 | 41 | tensor | rom_package_ucie | rom_board_serdes | 172 | 59.94 us | 1,668.2 tok/s | 16,682.3 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 11 on rom_board_serdes (traversals 6.6) = 57.83 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x55 | DeepSeek-V4-Flash-0731 | 55 | hybrid | rom_package_ucie | rom_board_serdes | 99 | 3.48 us | 28,773.2 tok/s | 287,732.3 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 13 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.36 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x67 | DeepSeek-V4-Flash-0731 | 67 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-tensor-x38 | DeepSeek-V4-Flash-0731 | 38 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x45 | DeepSeek-V4-Flash-0731 | 45 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x6-pipeline | DeepSeek-V4-Flash-0731 | 6 | pipeline | nvlink3 | infiniband_hdr | 5 | 12.64 us | 7,913.6 tok/s | 79,135.6 tok/s | 5 x point_to_point span 2 on nvlink3 (traversals 1.0) = 12.64 us |
| DSV4-Flash/a100_sxm_80gb-x6-tensor | DeepSeek-V4-Flash-0731 | 6 | tensor | nvlink3 | infiniband_hdr | 86 | 435.87 us | 229.4 tok/s | 2,294.3 tok/s | 86 x all_reduce span 6 on nvlink3 (traversals 2.0) = 435.87 us |
| DSV4-Flash/a100_sxm_80gb-x6-expert | DeepSeek-V4-Flash-0731 | 6 | expert | nvlink3 | infiniband_hdr | 172 | 653.22 us | 153.1 tok/s | 1,530.9 tok/s | 86 x all_reduce span 6 on nvlink3 (traversals 2.0) = 435.87 us; 86 x point_to_point span 2 on nvlink3 (traversals 1.0) = 217.35 us |
| DSV4-Flash/a100_sxm_80gb-x18-pipeline | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink3 | infiniband_hdr | 17 | 42.62 us | 2,346.0 tok/s | 23,460.4 tok/s | 15 x point_to_point span 2 on nvlink3 (traversals 1.0) = 37.91 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x18-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x18-hybrid | DeepSeek-V4-Flash-0731 | 18 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x18-expert | DeepSeek-V4-Flash-0731 | 18 | expert | nvlink3 | infiniband_hdr | 172 | 617.06 us | 162.1 tok/s | 1,620.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 183.97 us |
| DSV4-Flash/a100_sxm_80gb-x20-pipeline | DeepSeek-V4-Flash-0731 | 20 | pipeline | nvlink3 | infiniband_hdr | 19 | 47.68 us | 2,097.3 tok/s | 20,973.3 tok/s | 17 x point_to_point span 2 on nvlink3 (traversals 1.0) = 42.96 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x20-tensor | DeepSeek-V4-Flash-0731 | 20 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x20-hybrid | DeepSeek-V4-Flash-0731 | 20 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x20-expert | DeepSeek-V4-Flash-0731 | 20 | expert | nvlink3 | infiniband_hdr | 172 | 616.12 us | 162.3 tok/s | 1,623.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 183.03 us |
| DSV4-Flash/a100_sxm_80gb-x22-pipeline | DeepSeek-V4-Flash-0731 | 22 | pipeline | nvlink3 | infiniband_hdr | 21 | 52.73 us | 1,896.3 tok/s | 18,963.0 tok/s | 19 x point_to_point span 2 on nvlink3 (traversals 1.0) = 48.02 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x22-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x22-hybrid | DeepSeek-V4-Flash-0731 | 22 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x22-expert | DeepSeek-V4-Flash-0731 | 22 | expert | nvlink3 | infiniband_hdr | 172 | 615.35 us | 162.5 tok/s | 1,625.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 182.27 us |
| DSV4-Flash/a100_sxm_80gb-x36-pipeline | DeepSeek-V4-Flash-0731 | 36 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x36-tensor | DeepSeek-V4-Flash-0731 | 36 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x36-hybrid | DeepSeek-V4-Flash-0731 | 36 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x36-expert | DeepSeek-V4-Flash-0731 | 36 | expert | nvlink3 | infiniband_hdr | 172 | 610.82 us | 163.7 tok/s | 1,637.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 179.28 us |
| DSV4-Flash/a100_sxm_80gb-x37-pipeline | DeepSeek-V4-Flash-0731 | 37 | pipeline | nvlink3 | infiniband_hdr | 36 | 90.30 us | 1,107.4 tok/s | 11,073.6 tok/s | 32 x point_to_point span 2 on nvlink3 (traversals 1.0) = 80.87 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-tensor | DeepSeek-V4-Flash-0731 | 37 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x37-hybrid | DeepSeek-V4-Flash-0731 | 37 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-expert | DeepSeek-V4-Flash-0731 | 37 | expert | nvlink3 | infiniband_hdr | 172 | 610.69 us | 163.7 tok/s | 1,637.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 179.15 us |
| DSV4-Flash/a100_sxm_80gb-x40-pipeline | DeepSeek-V4-Flash-0731 | 40 | pipeline | nvlink3 | infiniband_hdr | 39 | 97.89 us | 1,021.6 tok/s | 10,215.9 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.46 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x40-tensor | DeepSeek-V4-Flash-0731 | 40 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x40-hybrid | DeepSeek-V4-Flash-0731 | 40 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x40-expert | DeepSeek-V4-Flash-0731 | 40 | expert | nvlink3 | infiniband_hdr | 172 | 610.04 us | 163.9 tok/s | 1,639.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.81 us |
| DSV4-Flash/a100_sxm_80gb-x43-pipeline | DeepSeek-V4-Flash-0731 | 43 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x43-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x43-hybrid | DeepSeek-V4-Flash-0731 | 43 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x43-expert | DeepSeek-V4-Flash-0731 | 43 | expert | nvlink3 | infiniband_hdr | 172 | 609.75 us | 164.0 tok/s | 1,640.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.51 us |
| DSV4-Flash/a100_sxm_80gb-x44-pipeline | DeepSeek-V4-Flash-0731 | 44 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x44-tensor | DeepSeek-V4-Flash-0731 | 44 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x44-hybrid | DeepSeek-V4-Flash-0731 | 44 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x44-expert | DeepSeek-V4-Flash-0731 | 44 | expert | nvlink3 | infiniband_hdr | 172 | 609.66 us | 164.0 tok/s | 1,640.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.42 us |
| DSV4-Flash/a100_sxm_80gb-x45-pipeline | DeepSeek-V4-Flash-0731 | 45 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x45-tensor | DeepSeek-V4-Flash-0731 | 45 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x45-hybrid | DeepSeek-V4-Flash-0731 | 45 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x45-expert | DeepSeek-V4-Flash-0731 | 45 | expert | nvlink3 | infiniband_hdr | 172 | 609.57 us | 164.0 tok/s | 1,640.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.34 us |
| DSV4-Flash/a100_sxm_80gb-x46-pipeline | DeepSeek-V4-Flash-0731 | 46 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x46-tensor | DeepSeek-V4-Flash-0731 | 46 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x46-hybrid | DeepSeek-V4-Flash-0731 | 46 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x46-expert | DeepSeek-V4-Flash-0731 | 46 | expert | nvlink3 | infiniband_hdr | 172 | 609.49 us | 164.1 tok/s | 1,640.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.26 us |
| DSV4-Flash/a100_sxm_80gb-x49-pipeline | DeepSeek-V4-Flash-0731 | 49 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x49-tensor | DeepSeek-V4-Flash-0731 | 49 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x49-hybrid | DeepSeek-V4-Flash-0731 | 49 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x49-expert | DeepSeek-V4-Flash-0731 | 49 | expert | nvlink3 | infiniband_hdr | 172 | 609.06 us | 164.2 tok/s | 1,641.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.03 us |
| DSV4-Flash/a100_sxm_80gb-x52-pipeline | DeepSeek-V4-Flash-0731 | 52 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x52-tensor | DeepSeek-V4-Flash-0731 | 52 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x52-hybrid | DeepSeek-V4-Flash-0731 | 52 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x52-expert | DeepSeek-V4-Flash-0731 | 52 | expert | nvlink3 | infiniband_hdr | 172 | 608.86 us | 164.2 tok/s | 1,642.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.83 us |
| DSV4-Flash/a100_sxm_80gb-x54-pipeline | DeepSeek-V4-Flash-0731 | 54 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x54-tensor | DeepSeek-V4-Flash-0731 | 54 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x54-hybrid | DeepSeek-V4-Flash-0731 | 54 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x54-expert | DeepSeek-V4-Flash-0731 | 54 | expert | nvlink3 | infiniband_hdr | 172 | 608.74 us | 164.3 tok/s | 1,642.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.71 us |
| DSV4-Flash/a100_sxm_80gb-x55-pipeline | DeepSeek-V4-Flash-0731 | 55 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x55-tensor | DeepSeek-V4-Flash-0731 | 55 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x55-hybrid | DeepSeek-V4-Flash-0731 | 55 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x55-expert | DeepSeek-V4-Flash-0731 | 55 | expert | nvlink3 | infiniband_hdr | 172 | 608.68 us | 164.3 tok/s | 1,642.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.65 us |
| DSV4-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Flash-0731 | 56 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Flash-0731 | 56 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Flash-0731 | 56 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x56-expert | DeepSeek-V4-Flash-0731 | 56 | expert | nvlink3 | infiniband_hdr | 172 | 608.48 us | 164.3 tok/s | 1,643.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.60 us |
| DSV4-Flash/a100_sxm_80gb-x66-pipeline | DeepSeek-V4-Flash-0731 | 66 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x66-tensor | DeepSeek-V4-Flash-0731 | 66 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x66-hybrid | DeepSeek-V4-Flash-0731 | 66 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x66-expert | DeepSeek-V4-Flash-0731 | 66 | expert | nvlink3 | infiniband_hdr | 172 | 607.91 us | 164.5 tok/s | 1,645.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.77 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.14 us |
| DSV4-Flash/a100_sxm_80gb-x67-pipeline | DeepSeek-V4-Flash-0731 | 67 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x67-tensor | DeepSeek-V4-Flash-0731 | 67 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x67-hybrid | DeepSeek-V4-Flash-0731 | 67 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x67-expert | DeepSeek-V4-Flash-0731 | 67 | expert | nvlink3 | infiniband_hdr | 172 | 607.87 us | 164.5 tok/s | 1,645.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.77 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.10 us |
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
| DeepSeek-V4-Flash-0731 | 1 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x45 | 36,675 | 3,298.5 | 0.090 | 3,298.5 (36,675) | 3,133.6 (92,450) | 0.95x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 2 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x45 | 36,675 | 3,298.5 | 0.090 | 3,298.5 (36,675) | 3,133.6 (92,450) | 0.95x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 4 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x45 | 36,675 | 3,298.5 | 0.090 | 3,298.5 (36,675) | 3,133.6 (92,450) | 0.95x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 8 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x55 | 44,825 | 3,361.1 | 0.075 | 3,361.1 (44,825) | 3,133.6 (92,450) | 0.93x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 16 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x55 | 44,825 | 3,290.5 | 0.073 | 3,290.5 (44,825) | 3,133.6 (92,450) | 0.95x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x67 | 54,605 | 3,268.8 | 0.060 | 3,268.8 (54,605) | 3,062.6 (92,450) | 0.94x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 64 | array | wafer | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill | 120,620 | 3,277.0 | 0.027 | 3,277.0 (120,620) | 2,967.7 (92,450) | 0.91x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 256 | array | wafer | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 2,971.8 | 0.011 | 2,971.8 (277,100) | 2,967.3 (369,800) | 1.00x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 1024 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2,330.5 | 0.004 | 1,387.9 (277,100) | 2,330.5 (554,700) | 1.68x | compute |
| DeepSeek-V4-Flash-0731 | 4096 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 843.4 | 0.002 | 412.3 (277,100) | 843.4 (554,700) | 2.05x | compute |

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
| DeepSeek-V4-Flash-0731 | 1 | sram | 365,593.6 | 27,637.6 | 27,637.6 | 13.23x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 365,593.6 | 27,637.6 | 27,637.6 | 13.23x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 365,593.6 | 27,637.6 | 27,637.6 | 13.23x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 365,593.6 | 27,637.6 | 27,637.6 | 13.23x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 365,593.6 | 27,637.6 | 34,176.3 | 13.23x | 1.24x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 365,593.6 | 27,637.6 | 51,775.4 | 13.23x | 1.87x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 365,593.6 | 27,869.1 | 77,327.3 | 13.12x | 2.77x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 523,889.0 | 29,014.6 | 133,078.3 | 18.06x | 4.59x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 976,308.4 | 29,014.6 | 206,657.5 | 33.65x | 7.12x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 1,707,600.7 | 29,014.6 | 334,697.9 | 58.85x | 11.54x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 1,898,917.1 | 74,928.6 | 74,928.6 | 25.34x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 1,898,917.1 | 74,928.6 | 74,928.6 | 25.34x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 1,898,917.1 | 74,928.6 | 74,928.6 | 25.34x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 1,898,917.1 | 74,928.6 | 74,928.6 | 25.34x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 1,898,917.1 | 74,928.6 | 74,928.6 | 25.34x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 1,898,917.1 | 74,928.6 | 74,928.6 | 25.34x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 1,898,917.1 | 76,678.0 | 83,155.6 | 24.76x | 1.08x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 1,898,917.1 | 89,507.1 | 218,504.6 | 21.22x | 2.44x | layer_fixed_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 2,386,433.1 | 92,446.4 | 502,958.1 | 25.81x | 5.44x | compute | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 3,454,699.6 | 92,446.4 | 525,418.6 | 37.37x | 5.68x | compute | weight_read | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,593.6 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,898,917.1 | 3.423 | layer_fixed_latency | 5.19x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,637.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.00 | 74,928.6 | 1.621 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,637.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 1.00 | 74,928.6 | 1.621 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,593.6 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,898,917.1 | 3.423 | layer_fixed_latency | 5.19x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,637.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.00 | 74,928.6 | 1.621 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,637.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 1.00 | 74,928.6 | 1.621 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,593.6 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,898,917.1 | 3.423 | layer_fixed_latency | 5.19x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,637.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.00 | 74,928.6 | 1.621 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,637.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 1.00 | 74,928.6 | 1.621 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,593.6 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,898,917.1 | 3.423 | layer_fixed_latency | 5.19x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,637.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.00 | 74,928.6 | 1.621 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,637.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 1.00 | 74,928.6 | 1.621 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,593.6 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,898,917.1 | 3.423 | layer_fixed_latency | 5.19x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,637.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.00 | 74,928.6 | 1.621 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x20-perregion | 16,300 | 1.00 | 1.39 | 34,176.3 | 2.097 | weight_read | 0.09x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 1.00 | 74,928.6 | 1.621 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,593.6 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,898,917.1 | 3.423 | layer_fixed_latency | 5.19x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,637.6 | 0.598 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.00 | 74,928.6 | 1.621 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x20-perregion | 16,300 | 1.00 | 1.97 | 51,775.4 | 3.176 | weight_read | 0.14x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 1.00 | 74,928.6 | 1.621 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 365,593.6 | 0.659 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,898,917.1 | 3.423 | layer_fixed_latency | 5.19x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 27,869.1 | 0.603 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.12 | 76,678.0 | 1.659 | weight_read | 0.21x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x20-perregion | 16,300 | 1.00 | 2.57 | 77,327.3 | 4.744 | weight_read | 0.21x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 1.01 | 83,155.6 | 1.799 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x148 | 120,620 | 1.00 | 1.00 | 523,889.0 | 4.343 | layer_fixed_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 1,898,917.1 | 3.423 | layer_fixed_latency | 3.62x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 29,014.6 | 0.628 | weight_read | 0.06x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 4.49 | 89,507.1 | 1.936 | weight_read | 0.17x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x20-perregion | 16,300 | 1.00 | 3.59 | 133,078.3 | 8.164 | weight_read | 0.25x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 1.67 | 218,504.6 | 4.727 | weight_read | 0.42x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 976,308.4 | 5.280 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 2,386,433.1 | 4.302 | compute | 2.44x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 17.96 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 17.96 | 92,446.4 | 2.000 | weight_read | 0.09x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x20-perregion | 16,300 | 1.00 | 7.67 | 206,657.5 | 12.678 | weight_read | 0.21x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 3.05 | 502,958.1 | 10.881 | kv_read | 0.52x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 1,707,600.7 | 4.618 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 3,454,699.6 | 6.228 | compute | 2.02x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 71.86 | 29,014.6 | 0.628 | weight_read | 0.02x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 71.86 | 92,446.4 | 2.000 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 6.23 | 334,697.9 | 7.241 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 6.23 | 525,418.6 | 11.367 | kv_read | 0.31x |

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
| DeepSeek-V4-Flash-0731 | 4 | 18 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 1.00 | 1.000 | 1.000 | 1.00x |
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
| DeepSeek-V4-Flash-0731 | 1 | 6 | 3.99 | 2.71 | 1.47x |
| DeepSeek-V4-Flash-0731 | 2 | 6 | 5.31 | 3.23 | 1.64x |
| DeepSeek-V4-Flash-0731 | 4 | 6 | 5.91 | 3.73 | 1.59x |
| DeepSeek-V4-Flash-0731 | 8 | 6 | 6.00 | 4.17 | 1.44x |
| DeepSeek-V4-Flash-0731 | 16 | 6 | 6.00 | 4.54 | 1.32x |
| DeepSeek-V4-Flash-0731 | 32 | 6 | 6.00 | 4.81 | 1.25x |
| DeepSeek-V4-Flash-0731 | 64 | 6 | 6.00 | 4.99 | 1.20x |
| DeepSeek-V4-Flash-0731 | 256 | 6 | 6.00 | 5.09 | 1.18x |
| DeepSeek-V4-Flash-0731 | 1024 | 6 | 6.00 | 5.09 | 1.18x |
| DeepSeek-V4-Flash-0731 | 4096 | 6 | 6.00 | 5.09 | 1.18x |
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
| DeepSeek-V4-Flash-0731 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 22 | 9.33 | 5.36 | 1.74x |
| DeepSeek-V4-Flash-0731 | 4 | 22 | 14.51 | 7.03 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 22 | 19.19 | 8.83 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 22 | 21.49 | 10.61 | 2.03x |
| DeepSeek-V4-Flash-0731 | 32 | 22 | 21.96 | 12.14 | 1.81x |
| DeepSeek-V4-Flash-0731 | 64 | 22 | 22.00 | 13.24 | 1.66x |
| DeepSeek-V4-Flash-0731 | 256 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 1024 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 4096 | 22 | 22.00 | 13.91 | 1.58x |
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
| DeepSeek-V4-Flash-0731 | 1 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4-Flash-0731 | 2 | 40 | 10.37 | 6.37 | 1.63x |
| DeepSeek-V4-Flash-0731 | 4 | 40 | 17.75 | 8.78 | 2.02x |
| DeepSeek-V4-Flash-0731 | 8 | 40 | 26.95 | 11.57 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 40 | 34.83 | 14.55 | 2.39x |
| DeepSeek-V4-Flash-0731 | 32 | 40 | 38.73 | 17.31 | 2.24x |
| DeepSeek-V4-Flash-0731 | 64 | 40 | 39.75 | 19.40 | 2.05x |
| DeepSeek-V4-Flash-0731 | 256 | 40 | 39.94 | 20.73 | 1.93x |
| DeepSeek-V4-Flash-0731 | 1024 | 40 | 39.94 | 20.74 | 1.93x |
| DeepSeek-V4-Flash-0731 | 4096 | 40 | 39.94 | 20.74 | 1.93x |
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
| DeepSeek-V4-Flash-0731 | 1 | 45 | 5.68 | 4.70 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 45 | 10.53 | 6.57 | 1.60x |
| DeepSeek-V4-Flash-0731 | 4 | 45 | 18.26 | 9.13 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 45 | 28.35 | 12.14 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 45 | 37.68 | 15.40 | 2.45x |
| DeepSeek-V4-Flash-0731 | 32 | 45 | 42.89 | 18.47 | 2.32x |
| DeepSeek-V4-Flash-0731 | 64 | 45 | 44.50 | 20.81 | 2.14x |
| DeepSeek-V4-Flash-0731 | 256 | 45 | 44.86 | 22.31 | 2.01x |
| DeepSeek-V4-Flash-0731 | 1024 | 45 | 44.86 | 22.32 | 2.01x |
| DeepSeek-V4-Flash-0731 | 4096 | 45 | 44.86 | 22.32 | 2.01x |
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
| DeepSeek-V4-Flash-0731 | 1 | 49 | 5.70 | 4.77 | 1.20x |
| DeepSeek-V4-Flash-0731 | 2 | 49 | 10.63 | 6.72 | 1.58x |
| DeepSeek-V4-Flash-0731 | 4 | 49 | 18.61 | 9.38 | 1.98x |
| DeepSeek-V4-Flash-0731 | 8 | 49 | 29.32 | 12.55 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 49 | 39.75 | 16.03 | 2.48x |
| DeepSeek-V4-Flash-0731 | 32 | 49 | 46.04 | 19.33 | 2.38x |
| DeepSeek-V4-Flash-0731 | 64 | 49 | 48.21 | 21.86 | 2.21x |
| DeepSeek-V4-Flash-0731 | 256 | 49 | 48.75 | 23.50 | 2.07x |
| DeepSeek-V4-Flash-0731 | 1024 | 49 | 48.75 | 23.51 | 2.07x |
| DeepSeek-V4-Flash-0731 | 4096 | 49 | 48.75 | 23.51 | 2.07x |
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
| DeepSeek-V4-Flash-0731 | 1 | 54 | 5.73 | 4.85 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 54 | 10.74 | 6.89 | 1.56x |
| DeepSeek-V4-Flash-0731 | 4 | 54 | 18.98 | 9.65 | 1.97x |
| DeepSeek-V4-Flash-0731 | 8 | 54 | 30.38 | 13.02 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 54 | 42.08 | 16.75 | 2.51x |
| DeepSeek-V4-Flash-0731 | 32 | 54 | 49.76 | 20.33 | 2.45x |
| DeepSeek-V4-Flash-0731 | 64 | 54 | 52.71 | 23.10 | 2.28x |
| DeepSeek-V4-Flash-0731 | 256 | 54 | 53.54 | 24.90 | 2.15x |
| DeepSeek-V4-Flash-0731 | 1024 | 54 | 53.55 | 24.92 | 2.15x |
| DeepSeek-V4-Flash-0731 | 4096 | 54 | 53.55 | 24.92 | 2.15x |
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
| DeepSeek-V4-Flash-0731 | 1 | 67 | 5.78 | 5.02 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 67 | 10.94 | 7.29 | 1.50x |
| DeepSeek-V4-Flash-0731 | 4 | 67 | 19.71 | 10.25 | 1.92x |
| DeepSeek-V4-Flash-0731 | 8 | 67 | 32.55 | 14.09 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 67 | 47.13 | 18.41 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 67 | 58.35 | 22.66 | 2.58x |
| DeepSeek-V4-Flash-0731 | 64 | 67 | 63.68 | 26.01 | 2.45x |
| DeepSeek-V4-Flash-0731 | 256 | 67 | 65.56 | 28.21 | 2.32x |
| DeepSeek-V4-Flash-0731 | 1024 | 67 | 65.57 | 28.23 | 2.32x |
| DeepSeek-V4-Flash-0731 | 4096 | 67 | 65.57 | 28.23 | 2.32x |
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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 894.40 | 31.3% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 275.85 | 94.9% |

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
| DeepSeek-V4-Flash-0731 | 1 | 18 | 8.63% | 6.74 | 4.34 |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 8.63% | 6.74 | 4.34 |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 8.63% | 6.74 | 4.34 |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 8.63% | 6.74 | 4.34 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 0.10% | 0.25 | 4.34 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 0.10% | 0.25 | 4.34 |
| DeepSeek-V4-Flash-0731 | 64 | 1 | 0.11% | 0.28 | 4.34 |
| DeepSeek-V4-Flash-0731 | 256 | 1 | 0.45% | 1.12 | 4.34 |

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
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 293.2 | 11,143.1 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 293.2 | 11,143.1 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 293.2 | 11,143.1 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 293.2 | 11,143.1 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 293.2 | 11,143.1 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 293.2 | 11,143.1 |
| DeepSeek-V4-Flash-0731 | 64 | 3.92% | 13.5 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 177.0 | 11,328.7 |
| DeepSeek-V4-Flash-0731 | 256 | 14.77% | 29.5 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 45.0 | 11,518.8 |
| DeepSeek-V4-Flash-0731 | 1024 | 47.22% | 77.3 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 11.3 | 11,543.5 |
| DeepSeek-V4-Flash-0731 | 4096 | 92.24% | 143.5 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2.8 | 11,493.1 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 1 |
| gpu | link_latency | 805 |
| gpu | weight_read | 464 |
| rom | compute | 565 |
| rom | infeasible | 2204 |
| rom | kv_read | 53 |
| rom | layer_fixed_latency | 854 |
| rom | link_latency | 1074 |
| rom | weight_read | 470 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2204 |

## Mechanical consistency audit

**FAIL** over 136,747 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x36', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x41', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x46', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x50', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x53', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x70', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x105', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x140', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x36', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x41', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x46', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x50', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x53', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x70', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x105', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x140', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x36', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x41', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x46', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x50', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x53', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x70', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x105', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x140', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x36', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x41', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x46', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x50', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x53', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x70', 'DeepSeek-V4-Flash-0731', 1)

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

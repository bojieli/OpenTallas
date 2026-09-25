# Area-constrained roofline: n6_vs_a100-deepseek-v41-flash-8k

> CANDIDATE MODEL under n6_vs_a100: DeepSeek-V4.1-Flash at 8,192 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 73x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 3 devices. On the GPU side the correction reaches 9x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 8 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash takes 2 x 46,225 mm2 (92,450 mm2, wafer, KV in HBM) at 4,004 tok/s per user and 43 tok/s per 1,000 mm2, holding 123,911 sessions, against 112 copies of one unified HBM die at the same silicon: 10.8x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash on 184,900 mm2 of ROM silicon at 5,233 tok/s per user against 185,024 mm2 of a100_sxm_80gb-x224-hybrid at 364 tok/s: **14.4x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 247,822 resident sessions against the GPU cluster's 1,562,671. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on DeepSeek-V4.1-Flash at batch 1, the iso-area GPU cluster is 672 devices. Cut as one serial pipeline that is 84 stages and 1,161 us of link latency per token; but the model has 40 layers, so at most 40 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 1,054 us. The iso-area per-user ratio at that point falls from 14.8x to 14.3x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 3.07x to it.** At 92,910 mm2 on DeepSeek-V4.1-Flash the pipeline-only GPU delivers 121.02 tok/s and the same silicon running hybrid delivers 372 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.01x (DeepSeek-V4.1-Flash, ROM binding on `link_latency`) to 13.91x (DeepSeek-V4.1-Flash, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 496 to 57,529 tok/s, and its rate with every slot occupied from 56,518 to 57,529. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 114 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,154 us over NVLink, capping per-user decode at 867 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 171.8 us and cap it at 5,821 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 10 of 10 operating points and an array 0; on tokens per second per square millimetre the same points go 1 to the array and 9 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 48 of 3770 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 101.9x of aggregate throughput (DeepSeek-V4.1-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 13.72x, on DeepSeek-V4.1-Flash at batch 4096, where the busiest region carries 3.17x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4.1-Flash at 8,192 tokens

**Recommended: `ROM-N6-native-HBMKV-wafer-hybrid-x2`** -- 2 x 46,225 mm2 wafers, 92,450 mm2 total, `hybrid`-parallel, KV in HBM, spare silicon to `sram`.

- **4,004.5 tok/s per user** (0.25 ms/token), binding on `layer_fixed_latency`
- **43.3 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 8,009 tok/s aggregate with every slot full, over 123,911 resident sessions (fill limited by `pipeline_slots`)
- 4,924 W at 0.053 W/mm2, 1,222.1 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 112 copies of one unified HBM die -- `a100_sxm_80gb-x112-hybrid`, 92,512 mm2, area ratio 0.9993 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 92,450 | 92,512 | 0.9993 |
| user tok/s | 4,004.5 | 371.7 | 10.77x |
| aggregate tok/s | 8,009 | 5,204 | 0.59x |
| resident sessions | 123,911 | 755,806 | -- |
| J/token | 1.2221 | 44.8781 | 36.7x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 123,911 sessions against one that holds 755,806 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x8-tensor` at 6,608 mm2 and 379.1 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 5,102.9 | 36.8 | 185,867 | 13.87x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | 28.3 | 247,822 | 14.36x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-hybrid-x108` | 88,020 | 2,411.1 | 27.4 | 1 | 6.59x |
| **after -- this report's rule** | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,004.5 | 43.3 | 123,911 | 10.77x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,004.5 | 43.3 | -- | 43.3 | ACCEPT |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x141` | 114,915 | 4,373.2 | 38.1 | 16.4 | 43.3 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x143` | 116,545 | 4,422.0 | 37.9 | 17.3 | 43.3 | stop |
| `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 5,102.9 | 36.8 | 23.8 | 43.3 | stop |
| `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | 28.3 | 13.3 | 43.3 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-HBMKV-wafer-hybrid-x2` **<-- recommended** | 92,450 | 2 | 4,004.5 | 8,009 | 43.3 | 123,911 | `layer_fixed_latency` | 4,924 | 1,222.1 | `a100_sxm_80gb-x112-hybrid` | 10.77x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x141` | 114,915 | 141 | 4,373.2 | 39,359 | 38.1 | 1,015,785 | `layer_fixed_latency` | 10,149 | 2,260.9 | `a100_sxm_80gb-x139-hybrid` | 11.97x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x143` | 116,545 | 143 | 4,422.0 | 39,798 | 37.9 | 1,030,193 | `layer_fixed_latency` | 10,416 | 2,295.8 | `a100_sxm_80gb-x141-hybrid` | 12.05x |
| `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3 | 5,102.9 | 56,131 | 36.8 | 185,867 | `layer_fixed_latency` | 12,107 | 2,297.8 | `a100_sxm_80gb-x168-hybrid` | 13.87x |
| `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4 | 5,233.2 | 151,762 | 28.3 | 247,822 | `layer_fixed_latency` | 19,644 | 3,544.5 | `a100_sxm_80gb-x224-hybrid` | 14.36x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 288 | densest | `ROM-N6-native-HBMKV-array-hw-hybrid-x141` | 114,915 | 4,373.2 | 38.1 | 1,015,785 |
| array | 288 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 201,305 | 5,026.9 | 25.0 | 1,779,424 |
| array | 288 | smallest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x108` | 88,020 | 2,411.1 | 27.4 | 1 |
| wafer | 72 | densest | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,004.5 | 43.3 | 123,911 |
| wafer | 72 | fastest | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | 28.3 | 247,822 |
| wafer | 72 | smallest | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,004.5 | 43.3 | 123,911 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 201,305 | 5,026.9 | 155,834 | 1,779,424 | 25,030 | 4,755.0 | `layer_fixed_latency` | `a100_sxm_80gb-x244-hybrid` | 361.0 | 1,706,754 | 98,976.0 | 0.999 | 13.93x | 20.8x |
| 1 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | 151,762 | 247,822 | 19,644 | 3,544.5 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 364.4 | 1,562,671 | 90,136.9 | 0.999 | 14.36x | 25.4x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | 4,976.6 | 144,322 | 1,642,546 | 22,433 | 4,298.3 | `layer_fixed_latency` | `a100_sxm_80gb-x225-hybrid` | 360.3 | 1,569,875 | 91,542.5 | 1.000 | 13.81x | 21.3x |
| 1 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | -- | 247,822 | -- | 3,544.5 | -- | -- | -- | -- | -- | 1.005 | 1.05x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 201,305 | 5,026.9 | 155,834 | 1,779,424 | 25,030 | 2,381.2 | `layer_fixed_latency` | `a100_sxm_80gb-x244-hybrid` | 361.0 | 1,706,754 | 50,174.8 | 0.999 | 13.93x | 21.1x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | 151,762 | 247,822 | 19,644 | 1,776.0 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 364.4 | 1,562,671 | 45,755.3 | 0.999 | 14.36x | 25.8x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | 4,976.6 | 144,322 | 1,642,546 | 22,433 | 2,152.9 | `layer_fixed_latency` | `a100_sxm_80gb-x225-hybrid` | 360.3 | 1,569,875 | 46,458.1 | 1.000 | 13.81x | 21.6x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | -- | 247,822 | -- | 1,776.0 | -- | -- | -- | -- | -- | 1.005 | 1.05x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 201,305 | 5,026.9 | 155,834 | 1,779,424 | 25,030 | 1,194.3 | `layer_fixed_latency` | `a100_sxm_80gb-x244-hybrid` | 361.0 | 1,706,754 | 25,774.3 | 0.999 | 13.93x | 21.6x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | 151,762 | 247,822 | 19,644 | 891.7 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 364.4 | 1,562,671 | 23,564.5 | 0.999 | 14.36x | 26.4x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | 4,976.6 | 144,322 | 1,642,546 | 22,433 | 1,080.2 | `layer_fixed_latency` | `a100_sxm_80gb-x225-hybrid` | 360.3 | 1,569,875 | 23,915.9 | 1.000 | 13.81x | 22.1x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | -- | 247,822 | -- | 891.7 | -- | -- | -- | -- | -- | 1.005 | 1.05x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 201,305 | 5,026.9 | 155,834 | 1,779,424 | 25,030 | 600.9 | `layer_fixed_latency` | `a100_sxm_80gb-x244-hybrid` | 361.0 | 1,706,754 | 13,574.0 | 0.999 | 13.93x | 22.6x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | 151,762 | 247,822 | 19,644 | 449.6 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 364.4 | 1,562,671 | 12,469.1 | 0.999 | 14.36x | 27.7x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | 4,976.6 | 144,322 | 1,642,546 | 22,433 | 543.8 | `layer_fixed_latency` | `a100_sxm_80gb-x225-hybrid` | 360.3 | 1,569,875 | 12,644.8 | 1.000 | 13.81x | 23.3x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | -- | 247,822 | -- | 449.6 | -- | -- | -- | -- | -- | 1.005 | 1.05x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 201,305 | 5,026.9 | 155,834 | 1,779,424 | 25,030 | 304.2 | `layer_fixed_latency` | `a100_sxm_80gb-x244-hybrid` | 361.0 | 1,706,754 | 7,473.8 | 0.999 | 13.93x | 24.6x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | 151,762 | 247,822 | 19,644 | 228.5 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 364.4 | 1,562,671 | 6,921.4 | 0.999 | 14.36x | 30.3x |
| 16 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x228` | 185,820 | 4,976.6 | 144,322 | 1,642,546 | 22,433 | 275.7 | `layer_fixed_latency` | `a100_sxm_80gb-x225-hybrid` | 360.3 | 1,569,875 | 7,009.2 | 1.000 | 13.81x | 25.4x |
| 16 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,233.2 | -- | 247,822 | -- | 228.5 | -- | -- | -- | -- | -- | 1.005 | 1.05x wafer/array | -- |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x342-romfill` | 278,730 | 4,869.3 | 209,381 | 2,463,819 | 32,522 | 206.1 | `layer_fixed_latency` | `a100_sxm_80gb-x337-hybrid` | 356.0 | 2,376,740 | 5,645.4 | 1.001 | 13.68x | 27.4x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,116.8 | 291,657 | 495,645 | 36,565 | 217.5 | `layer_fixed_latency` | `a100_sxm_80gb-x448-hybrid` | 358.3 | 3,176,401 | 7,015.6 | 0.999 | 14.28x | 32.3x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x247` | 201,305 | 4,654.3 | 297,875 | 1,779,424 | 26,067 | 87.5 | `layer_fixed_latency` | `a100_sxm_80gb-x244-hybrid` | 315.5 | 1,706,754 | 2,652.7 | 0.999 | 14.75x | 30.3x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,112.2 | 439,648 | 743,468 | 54,864 | 165.1 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 358.3 | 4,790,130 | 5,605.1 | 0.999 | 14.27x | 33.9x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x342` | 278,730 | 3,166.8 | 810,694 | 2,463,819 | 41,042 | 50.6 | `layer_fixed_latency` | `a100_sxm_80gb-x337-hybrid` | 212.2 | 2,376,740 | 1,506.0 | 1.001 | 14.92x | 29.7x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,973.2 | 1,017,148 | 743,468 | 58,283 | 57.3 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 279.4 | 4,790,130 | 2,120.7 | 0.999 | 14.22x | 37.0x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 278,730 | 1,344.0 | 1,376,260 | 2,463,819 | 44,257 | 32.2 | `compute` | `a100_sxm_80gb-x337-hybrid` | 94.9 | 2,376,740 | 1,014.1 | 1.001 | 14.16x | 31.5x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,899.7 | 1,945,267 | 743,468 | 64,386 | 33.1 | `compute` | `a100_sxm_80gb-x672-hybrid` | 145.8 | 4,790,130 | 1,256.1 | 0.999 | 13.03x | 37.9x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x342` | 278,730 | 379.6 | 1,554,658 | 2,463,819 | 44,101 | 28.4 | `compute` | `a100_sxm_80gb-x337-hybrid` | 37.2 | 2,376,740 | 579.5 | 1.001 | 10.19x | 20.4x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 721.6 | 2,955,663 | 743,468 | 87,040 | 29.4 | `weight_read` | `a100_sxm_80gb-x672-hybrid` | 58.5 | 4,790,130 | 842.5 | 0.999 | 12.34x | 28.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-4 | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | wafer | HBM | 123,911 |
| 8 | `ROM-N6-native-HBMKV-array-hw-hybrid-x141` | 114,915 | array | HBM | 1,015,785 |
| 16-64 | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | wafer | HBM | 185,867 |
| 256 | `ROM-N6-native-HBMKV-wafer-pipeline-x4` | 184,900 | wafer | HBM | 247,822 |
| 1024 | `ROM-N6-native-HBMKV-wafer-pipeline-x6` | 277,350 | wafer | HBM | 371,734 |
| 4096 | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 369,800 | wafer | HBM | 495,645 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash | HBM | rom | 116, 119, 141, 143, 170, 171, 191, 205, 206, 227, 228, 340, 342 |
| DeepSeek-V4.1-Flash | HBM | sram | 116, 119, 141, 143, 170, 171, 215, 227, 228, 245, 247, 340, 342 |
| DeepSeek-V4.1-Flash | SRAM | rom | 108, 112, 113, 114, 132, 158, 170, 210, 227, 315, 340 |
| DeepSeek-V4.1-Flash | SRAM | sram | 108, 112, 113, 114, 132, 158, 170, 210, 227, 315, 340 |

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
| DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1 | 57 on `rom_wafer_express` | 6.25 | one_shot, rec_doubling | 136.92 | 83.15 | 34.77 | 47.31 | 4,004.5 |
| DeepSeek-V4.1-Flash | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 64 | 2 on `rom_wafer_express` | 5.25 | one_shot | 121.78 | 6.09 | 1,112.48 | 16.72 | 837.1 |
| DeepSeek-V4.1-Flash | `a100_sxm_80gb-x112-hybrid` | 1 | 8 | 5.25 | measured_floor | 860.60 | 953.29 | 987.57 | 448.93 | 371.7 |
| DeepSeek-V4.1-Flash | `a100_sxm_80gb-x112-hybrid` | 64 | 8 | 5.25 | measured_floor | 860.60 | 1,095.69 | 2,167.87 | 493.55 | 257.7 |

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

- **0 of 3,770 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 81% of its cooling budget, and the busiest wafer-scale ROM design 32%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 30 | 0 | 65.8% | 81.0% | 0.392 | 57% |
| gpu | wafer (>=40,000 mm2) | 1,200 | 0 | 51.5% | 79.8% | 0.387 | 85% |
| rom | wafer (>=40,000 mm2) | 2,540 | 0 | 19.9% | 31.8% | 0.159 | 98% |

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
| DeepSeek-V4.1-Flash | 1 | 138,675 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3` | 2.297771 | 12,106.6 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-hybrid` | 67.287872 | 34,872.5 | link_latency | 29.28x |
| DeepSeek-V4.1-Flash | 2 | 138,675 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3` | 1.152623 | 12,106.6 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-hybrid` | 34.330787 | 34,872.5 | link_latency | 29.78x |
| DeepSeek-V4.1-Flash | 4 | 138,675 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3` | 0.580049 | 12,106.6 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-hybrid` | 17.852244 | 34,872.5 | link_latency | 30.78x |
| DeepSeek-V4.1-Flash | 8 | 138,675 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3` | 0.293762 | 12,106.6 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-hybrid` | 9.612973 | 34,872.5 | link_latency | 32.72x |
| DeepSeek-V4.1-Flash | 16 | 184,900 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4` | 0.228542 | 19,644.4 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-hybrid` | 6.921404 | 46,356.8 | link_latency | 30.29x |
| DeepSeek-V4.1-Flash | 32 | 184,900 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4` | 0.125255 | 19,643.3 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-hybrid` | 4.088031 | 46,771.4 | link_latency | 32.64x |
| DeepSeek-V4.1-Flash | 64 | 554,700 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.165119 | 54,864.2 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid` | 5.605139 | 138,368.2 | link_latency | 33.95x |
| DeepSeek-V4.1-Flash | 256 | 554,700 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.057300 | 58,283.0 | layer_fixed_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid` | 2.120748 | 151,691.8 | weight_read | 37.01x |
| DeepSeek-V4.1-Flash | 1024 | 369,800 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8` | 0.029431 | 55,272.2 | weight_read | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-hybrid` | 1.097833 | 128,863.1 | weight_read | 37.30x |
| DeepSeek-V4.1-Flash | 4096 | 554,700 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 0.029449 | 87,040.4 | weight_read | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid` | 0.842491 | 201,728.5 | weight_read | 28.61x |

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
| DeepSeek-V4.1-Flash | 8,192 | 552 B | 510.3 GB | 7.40 | 0.012 GB | 0.010 GB | 1,092.9 |

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
| DeepSeek-V4.1-Flash | 2 | 92,450 | 6,402.8 | wafer-pipeline | 4,004.5 | wafer-hybrid | 1.60x | 977.3 | pipeline | 371.7 | hybrid | 2.63x | 6.55x | 10.77x | 1.64x |
| DeepSeek-V4.1-Flash | 3 | 138,675 | 6,668.5 | wafer-pipeline | 5,102.9 | wafer-hybrid | 1.31x | 997.6 | pipeline | 368.0 | hybrid | 2.71x | 6.68x | 13.87x | 2.07x |
| DeepSeek-V4.1-Flash | 4 | 184,900 | 6,680.7 | wafer-pipeline | 5,233.2 | wafer-hybrid | 1.28x | 1,008.1 | pipeline | 364.4 | hybrid | 2.77x | 6.63x | 14.36x | 2.17x |
| DeepSeek-V4.1-Flash | 6 | 277,350 | 6,683.7 | wafer-pipeline | 5,128.7 | wafer-hybrid | 1.30x | 1,018.8 | pipeline | 358.3 | hybrid | 2.84x | 6.56x | 14.31x | 2.18x |
| DeepSeek-V4.1-Flash | 8 | 369,800 | 6,686.3 | wafer-pipeline | 5,116.8 | wafer-hybrid | 1.31x | 1,024.3 | pipeline | 358.3 | hybrid | 2.86x | 6.53x | 14.28x | 2.19x |
| DeepSeek-V4.1-Flash | 12 | 554,700 | 6,687.6 | wafer-pipeline | 5,112.2 | wafer-hybrid | 1.31x | 1,029.8 | pipeline | 358.3 | hybrid | 2.87x | 6.49x | 14.27x | 2.20x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.64x to 2.20x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash | 1 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 5,233.2 | 151,761.7 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-hybrid | 185,024 | 1.00x | hybrid | 1,007.54 | 364.4 | 10,202.2 | link_latency | 14.36x | 5.60x | 43.24x | 14.36x |
| DeepSeek-V4.1-Flash | 1 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x108 | 88,020 | 2,411.1 | 2,411.1 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x107-hybrid | 88,382 | 1.00x | hybrid | 953.29 | 366.1 | 5,125.9 | link_latency | 6.59x | 0.19x | 19.92x | 6.59x |
| DeepSeek-V4.1-Flash | 2 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 5,233.2 | 151,761.7 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-hybrid | 185,024 | 1.00x | hybrid | 1,007.54 | 364.4 | 10,202.2 | link_latency | 14.36x | 5.60x | 43.24x | 14.36x |
| DeepSeek-V4.1-Flash | 2 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,004.5 | 8,009.0 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 953.29 | 371.7 | 5,203.9 | link_latency | 10.77x | 0.59x | 33.09x | 10.77x |
| DeepSeek-V4.1-Flash | 4 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 5,233.2 | 151,761.7 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-hybrid | 185,024 | 1.00x | hybrid | 1,007.54 | 364.4 | 10,202.2 | link_latency | 14.36x | 5.60x | 43.24x | 14.36x |
| DeepSeek-V4.1-Flash | 4 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 3,890.5 | 15,561.8 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 953.29 | 371.7 | 5,203.9 | link_latency | 10.47x | 1.15x | 32.15x | 10.47x |
| DeepSeek-V4.1-Flash | 8 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 5,233.2 | 151,761.7 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-hybrid | 185,024 | 1.00x | hybrid | 1,007.54 | 364.4 | 10,202.2 | link_latency | 14.36x | 5.60x | 43.24x | 14.36x |
| DeepSeek-V4.1-Flash | 8 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 3,354.9 | 26,839.5 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 953.29 | 371.7 | 5,203.9 | link_latency | 9.03x | 1.98x | 27.72x | 9.03x |
| DeepSeek-V4.1-Flash | 16 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 5,233.2 | 151,761.7 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-hybrid | 185,024 | 1.00x | hybrid | 1,007.54 | 364.4 | 10,202.2 | link_latency | 14.36x | 5.60x | 43.24x | 14.36x |
| DeepSeek-V4.1-Flash | 16 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 2,407.8 | 38,524.8 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 958.99 | 365.1 | 5,841.5 | link_latency | 6.59x | 2.84x | 19.90x | 6.59x |
| DeepSeek-V4.1-Flash | 32 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 5,116.8 | 291,657.4 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-hybrid | 370,048 | 1.00x | hybrid | 1,054.14 | 358.3 | 20,063.6 | link_latency | 14.28x | 5.38x | 42.28x | 14.48x |
| DeepSeek-V4.1-Flash | 32 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1,502.1 | 48,066.1 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 1,004.55 | 320.0 | 10,238.4 | weight_read | 4.69x | 3.55x | 12.41x | 4.69x |
| DeepSeek-V4.1-Flash | 64 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 5,112.2 | 439,647.6 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,054.14 | 358.3 | 30,095.4 | link_latency | 14.27x | 5.41x | 42.24x | 14.82x |
| DeepSeek-V4.1-Flash | 64 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 837.1 | 53,577.0 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 1,095.69 | 257.7 | 16,493.4 | weight_read | 3.25x | 3.25x | 6.92x | 3.25x |
| DeepSeek-V4.1-Flash | 256 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,973.2 | 1,017,148.1 | layer_fixed_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,234.22 | 279.4 | 71,527.5 | weight_read | 14.22x | 12.51x | 32.83x | 14.79x |
| DeepSeek-V4.1-Flash | 256 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2 | 92,450 | 224.7 | 57,529.0 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 1,642.50 | 125.8 | 32,215.8 | weight_read | 1.79x | 1.79x | 2.59x | 1.79x |
| DeepSeek-V4.1-Flash | 1024 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1,899.7 | 1,945,266.7 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 1,289.29 | 145.8 | 149,338.6 | weight_read | 13.03x | 13.03x | 18.24x | 13.91x |
| DeepSeek-V4.1-Flash | 1024 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2 | 92,450 | 56.2 | 57,529.0 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 3,616.63 | 52.5 | 53,712.1 | weight_read | 1.07x | 1.07x | 1.61x | 1.07x |
| DeepSeek-V4.1-Flash | 4096 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 721.6 | 2,955,662.7 | weight_read | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 2,026.60 | 58.5 | 239,442.8 | weight_read | 12.34x | 12.34x | 15.31x | 13.05x |
| DeepSeek-V4.1-Flash | 4096 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2 | 92,450 | 14.0 | 57,529.0 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 12,839.45 | 28.9 | 118,541.0 | weight_read | 0.49x | 0.49x | 1.15x | 0.49x |

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
| DeepSeek-V4.1-Flash | 8 | 6,608 | 122.3 | 379.1 | — | tensor | 900.98 | 34.2% | link_latency |
| DeepSeek-V4.1-Flash | 53 | 43,778 | 121.0 | 287.4 | 368.6 | hybrid | 926.32 | 34.1% | weight_read |
| DeepSeek-V4.1-Flash | 56 | 46,256 | 121.0 | 287.6 | 375.5 | hybrid | 926.32 | 34.8% | link_latency |
| DeepSeek-V4.1-Flash | 58 | 47,908 | 121.0 | 287.4 | 362.6 | hybrid | 930.12 | 33.7% | weight_read |
| DeepSeek-V4.1-Flash | 59 | 48,734 | 121.0 | 287.4 | 364.8 | hybrid | 930.12 | 33.9% | weight_read |
| DeepSeek-V4.1-Flash | 107 | 88,382 | 121.0 | 258.1 | 366.1 | hybrid | 953.29 | 34.9% | link_latency |
| DeepSeek-V4.1-Flash | 111 | 91,686 | 121.0 | 257.9 | 370.6 | hybrid | 953.29 | 35.3% | link_latency |
| DeepSeek-V4.1-Flash | 112 | 92,512 | 121.0 | 257.8 | 371.7 | hybrid | 953.29 | 35.4% | link_latency |
| DeepSeek-V4.1-Flash | 114 | 94,164 | 121.0 | 257.6 | 364.9 | hybrid | 957.26 | 34.9% | link_latency |
| DeepSeek-V4.1-Flash | 117 | 96,642 | 121.0 | 257.5 | 368.1 | hybrid | 957.26 | 35.2% | link_latency |
| DeepSeek-V4.1-Flash | 130 | 107,380 | 121.0 | 256.4 | 364.6 | hybrid | 965.03 | 35.2% | link_latency |
| DeepSeek-V4.1-Flash | 139 | 114,814 | 121.0 | 255.7 | 365.3 | hybrid | 968.83 | 35.4% | link_latency |
| DeepSeek-V4.1-Flash | 141 | 116,466 | 121.0 | 255.6 | 367.0 | hybrid | 968.83 | 35.6% | link_latency |
| DeepSeek-V4.1-Flash | 156 | 128,856 | 121.0 | 254.5 | 365.5 | hybrid | 976.60 | 35.7% | link_latency |
| DeepSeek-V4.1-Flash | 168 | 138,768 | 121.0 | 253.6 | 368.0 | hybrid | 980.40 | 36.1% | link_latency |
| DeepSeek-V4.1-Flash | 169 | 139,594 | 121.0 | 253.4 | 362.6 | hybrid | 984.36 | 35.7% | link_latency |
| DeepSeek-V4.1-Flash | 188 | 155,288 | 121.0 | 251.9 | 363.9 | hybrid | 992.13 | 36.1% | link_latency |
| DeepSeek-V4.1-Flash | 202 | 166,852 | 121.0 | 250.7 | 361.9 | hybrid | 999.90 | 36.2% | link_latency |
| DeepSeek-V4.1-Flash | 203 | 167,678 | 121.0 | 250.7 | 362.5 | hybrid | 999.90 | 36.2% | link_latency |
| DeepSeek-V4.1-Flash | 207 | 170,982 | 121.0 | 250.4 | 364.8 | hybrid | 999.90 | 36.5% | link_latency |
| DeepSeek-V4.1-Flash | 212 | 175,112 | 121.0 | 250.0 | 362.7 | hybrid | 1,003.57 | 36.4% | link_latency |
| DeepSeek-V4.1-Flash | 224 | 185,024 | 121.0 | 249.0 | 364.4 | hybrid | 1,007.54 | 36.7% | link_latency |
| DeepSeek-V4.1-Flash | 225 | 185,850 | 121.0 | 248.9 | 360.3 | hybrid | 1,011.34 | 36.4% | link_latency |
| DeepSeek-V4.1-Flash | 242 | 199,892 | 121.0 | 247.5 | 360.0 | hybrid | 1,019.11 | 36.7% | link_latency |
| DeepSeek-V4.1-Flash | 244 | 201,544 | 121.0 | 247.4 | 361.0 | hybrid | 1,019.11 | 36.8% | link_latency |
| DeepSeek-V4.1-Flash | 311 | 256,886 | 121.0 | 242.0 | 358.4 | hybrid | 1,050.18 | 37.6% | link_latency |
| DeepSeek-V4.1-Flash | 335 | 276,710 | 121.0 | 204.4 | 357.9 | hybrid | 1,054.14 | 37.7% | link_latency |
| DeepSeek-V4.1-Flash | 336 | 277,536 | 121.0 | 204.4 | 358.3 | hybrid | 1,054.14 | 37.8% | link_latency |
| DeepSeek-V4.1-Flash | 337 | 278,362 | 121.0 | 204.3 | 356.0 | hybrid | 1,054.14 | 37.5% | link_latency |
| DeepSeek-V4.1-Flash | 448 | 370,048 | 121.0 | 198.1 | 358.3 | hybrid | 1,054.14 | 37.8% | link_latency |
| DeepSeek-V4.1-Flash | 672 | 555,072 | 121.0 | 186.6 | 358.3 | hybrid | 1,054.14 | 37.8% | link_latency |

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
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x112 | DeepSeek-V4.1-Flash | 112 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x114 | DeepSeek-V4.1-Flash | 114 | tensor | rom_package_ucie | rom_board_serdes | 160 | 91.38 us | 1,094.3 tok/s | 10,943.4 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 29 on rom_board_serdes (traversals 11.0) = 89.32 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x114 | DeepSeek-V4.1-Flash | 114 | hybrid | rom_package_ucie | rom_board_serdes | 108 | 5.02 us | 19,920.0 tok/s | 199,199.7 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 28 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.96 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x112 | DeepSeek-V4.1-Flash | 112 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash | 2 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-tensor-x108 | DeepSeek-V4.1-Flash | 108 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash | 2 | tensor | on_wafer | rom_wafer_serdes | 160 | 171.80 us | 582.1 tok/s | 5,820.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 17.80 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hybrid-x112 | DeepSeek-V4.1-Flash | 112 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash | 2 | hybrid | on_wafer | rom_wafer_serdes | 81 | 154.10 us | 648.9 tok/s | 6,489.2 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x247 | DeepSeek-V4.1-Flash | 247 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x119 | DeepSeek-V4.1-Flash | 119 | tensor | rom_package_ucie | rom_board_serdes | 160 | 91.38 us | 1,094.3 tok/s | 10,943.2 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 30 on rom_board_serdes (traversals 11.0) = 89.32 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x215 | DeepSeek-V4.1-Flash | 215 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 6.18 us | 16,174.3 tok/s | 161,742.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.12 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-pipeline-x245 | DeepSeek-V4.1-Flash | 245 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4 | DeepSeek-V4.1-Flash | 4 | pipeline | on_wafer | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-tensor-x116 | DeepSeek-V4.1-Flash | 116 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash | 2 | tensor | on_wafer | rom_wafer_serdes | 160 | 171.80 us | 582.1 tok/s | 5,820.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 17.80 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hybrid-x141 | DeepSeek-V4.1-Flash | 141 | hybrid | nvlink3 | infiniband_hdr | 97 | 448.64 us | 222.9 tok/s | 2,229.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 41.47 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | DeepSeek-V4.1-Flash | 4 | hybrid | on_wafer | rom_wafer_serdes | 83 | 154.31 us | 648.1 tok/s | 6,480.7 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 3 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.31 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x8-pipeline | DeepSeek-V4.1-Flash | 8 | pipeline | nvlink3 | infiniband_hdr | 7 | 17.74 us | 5,637.3 tok/s | 56,373.2 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 17.74 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x8-tensor | DeepSeek-V4.1-Flash | 8 | tensor | nvlink3 | infiniband_hdr | 80 | 407.17 us | 245.6 tok/s | 2,456.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x8-expert | DeepSeek-V4.1-Flash | 8 | expert | nvlink3 | infiniband_hdr | 160 | 609.22 us | 164.1 tok/s | 1,641.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x point_to_point span 2 on nvlink3 (traversals 1.0) = 202.05 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x53-pipeline | DeepSeek-V4.1-Flash | 53 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x53-tensor | DeepSeek-V4.1-Flash | 53 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x53-hybrid | DeepSeek-V4.1-Flash | 53 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x53-expert | DeepSeek-V4.1-Flash | 53 | expert | nvlink3 | infiniband_hdr | 160 | 567.30 us | 176.3 tok/s | 1,762.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.19 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 166.11 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4.1-Flash | 56 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4.1-Flash | 56 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4.1-Flash | 56 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-expert | DeepSeek-V4.1-Flash | 56 | expert | nvlink3 | infiniband_hdr | 160 | 566.93 us | 176.4 tok/s | 1,763.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.91 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x58-pipeline | DeepSeek-V4.1-Flash | 58 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x58-tensor | DeepSeek-V4.1-Flash | 58 | tensor | nvlink3 | infiniband_hdr | 160 | 817.98 us | 122.3 tok/s | 1,222.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 410.82 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x58-hybrid | DeepSeek-V4.1-Flash | 58 | hybrid | nvlink3 | infiniband_hdr | 87 | 424.25 us | 235.7 tok/s | 2,357.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x58-expert | DeepSeek-V4.1-Flash | 58 | expert | nvlink3 | infiniband_hdr | 160 | 566.81 us | 176.4 tok/s | 1,764.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.79 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x59-pipeline | DeepSeek-V4.1-Flash | 59 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x59-tensor | DeepSeek-V4.1-Flash | 59 | tensor | nvlink3 | infiniband_hdr | 160 | 817.98 us | 122.3 tok/s | 1,222.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 410.82 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x59-hybrid | DeepSeek-V4.1-Flash | 59 | hybrid | nvlink3 | infiniband_hdr | 87 | 424.25 us | 235.7 tok/s | 2,357.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x59-expert | DeepSeek-V4.1-Flash | 59 | expert | nvlink3 | infiniband_hdr | 160 | 566.76 us | 176.4 tok/s | 1,764.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 401.02 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 165.73 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x107-pipeline | DeepSeek-V4.1-Flash | 107 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x107-tensor | DeepSeek-V4.1-Flash | 107 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x107-hybrid | DeepSeek-V4.1-Flash | 107 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x107-expert | DeepSeek-V4.1-Flash | 107 | expert | nvlink3 | infiniband_hdr | 160 | 564.79 us | 177.1 tok/s | 1,770.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.55 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.24 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-pipeline | DeepSeek-V4.1-Flash | 111 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-tensor | DeepSeek-V4.1-Flash | 111 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-hybrid | DeepSeek-V4.1-Flash | 111 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-expert | DeepSeek-V4.1-Flash | 111 | expert | nvlink3 | infiniband_hdr | 160 | 564.72 us | 177.1 tok/s | 1,770.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.55 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.17 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4.1-Flash | 112 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4.1-Flash | 112 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4.1-Flash | 112 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-expert | DeepSeek-V4.1-Flash | 112 | expert | nvlink3 | infiniband_hdr | 160 | 564.67 us | 177.1 tok/s | 1,771.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.16 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x114-pipeline | DeepSeek-V4.1-Flash | 114 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x114-tensor | DeepSeek-V4.1-Flash | 114 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x114-hybrid | DeepSeek-V4.1-Flash | 114 | hybrid | nvlink3 | infiniband_hdr | 94 | 441.32 us | 226.6 tok/s | 2,265.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 34.15 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x114-expert | DeepSeek-V4.1-Flash | 114 | expert | nvlink3 | infiniband_hdr | 160 | 564.64 us | 177.1 tok/s | 1,771.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.12 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x117-pipeline | DeepSeek-V4.1-Flash | 117 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x117-tensor | DeepSeek-V4.1-Flash | 117 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x117-hybrid | DeepSeek-V4.1-Flash | 117 | hybrid | nvlink3 | infiniband_hdr | 94 | 441.32 us | 226.6 tok/s | 2,265.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 34.15 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x117-expert | DeepSeek-V4.1-Flash | 117 | expert | nvlink3 | infiniband_hdr | 160 | 564.59 us | 177.1 tok/s | 1,771.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.51 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 164.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x130-pipeline | DeepSeek-V4.1-Flash | 130 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x130-tensor | DeepSeek-V4.1-Flash | 130 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x130-hybrid | DeepSeek-V4.1-Flash | 130 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x130-expert | DeepSeek-V4.1-Flash | 130 | expert | nvlink3 | infiniband_hdr | 160 | 564.36 us | 177.2 tok/s | 1,771.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.45 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.91 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x139-pipeline | DeepSeek-V4.1-Flash | 139 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x139-tensor | DeepSeek-V4.1-Flash | 139 | tensor | nvlink3 | infiniband_hdr | 160 | 824.81 us | 121.2 tok/s | 1,212.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 417.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x139-hybrid | DeepSeek-V4.1-Flash | 139 | hybrid | nvlink3 | infiniband_hdr | 97 | 448.64 us | 222.9 tok/s | 2,229.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 41.47 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x139-expert | DeepSeek-V4.1-Flash | 139 | expert | nvlink3 | infiniband_hdr | 160 | 564.24 us | 177.2 tok/s | 1,772.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.42 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.81 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-pipeline | DeepSeek-V4.1-Flash | 141 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-tensor | DeepSeek-V4.1-Flash | 141 | tensor | nvlink3 | infiniband_hdr | 160 | 824.81 us | 121.2 tok/s | 1,212.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 417.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-hybrid | DeepSeek-V4.1-Flash | 141 | hybrid | nvlink3 | infiniband_hdr | 97 | 448.64 us | 222.9 tok/s | 2,229.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 41.47 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-expert | DeepSeek-V4.1-Flash | 141 | expert | nvlink3 | infiniband_hdr | 160 | 564.22 us | 177.2 tok/s | 1,772.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.42 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.79 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x156-pipeline | DeepSeek-V4.1-Flash | 156 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x156-tensor | DeepSeek-V4.1-Flash | 156 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x156-hybrid | DeepSeek-V4.1-Flash | 156 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x156-expert | DeepSeek-V4.1-Flash | 156 | expert | nvlink3 | infiniband_hdr | 160 | 564.04 us | 177.3 tok/s | 1,772.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.38 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.66 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-pipeline | DeepSeek-V4.1-Flash | 168 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-tensor | DeepSeek-V4.1-Flash | 168 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-hybrid | DeepSeek-V4.1-Flash | 168 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-expert | DeepSeek-V4.1-Flash | 168 | expert | nvlink3 | infiniband_hdr | 160 | 563.91 us | 177.3 tok/s | 1,773.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.34 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-pipeline | DeepSeek-V4.1-Flash | 169 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-tensor | DeepSeek-V4.1-Flash | 169 | tensor | nvlink3 | infiniband_hdr | 160 | 825.80 us | 121.1 tok/s | 1,210.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 418.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-hybrid | DeepSeek-V4.1-Flash | 169 | hybrid | nvlink3 | infiniband_hdr | 101 | 458.40 us | 218.2 tok/s | 2,181.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 51.23 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-expert | DeepSeek-V4.1-Flash | 169 | expert | nvlink3 | infiniband_hdr | 160 | 563.90 us | 177.3 tok/s | 1,773.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.34 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.56 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x188-pipeline | DeepSeek-V4.1-Flash | 188 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x188-tensor | DeepSeek-V4.1-Flash | 188 | tensor | nvlink3 | infiniband_hdr | 160 | 826.18 us | 121.0 tok/s | 1,210.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 419.01 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x188-hybrid | DeepSeek-V4.1-Flash | 188 | hybrid | nvlink3 | infiniband_hdr | 103 | 463.28 us | 215.9 tok/s | 2,158.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 56.11 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x188-expert | DeepSeek-V4.1-Flash | 188 | expert | nvlink3 | infiniband_hdr | 160 | 563.76 us | 177.4 tok/s | 1,773.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.31 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.45 us |
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
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x212-pipeline | DeepSeek-V4.1-Flash | 212 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x212-tensor | DeepSeek-V4.1-Flash | 212 | tensor | nvlink3 | infiniband_hdr | 160 | 826.63 us | 121.0 tok/s | 1,209.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 419.46 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x212-hybrid | DeepSeek-V4.1-Flash | 212 | hybrid | nvlink3 | infiniband_hdr | 106 | 470.60 us | 212.5 tok/s | 2,125.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 26 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.43 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x212-expert | DeepSeek-V4.1-Flash | 212 | expert | nvlink3 | infiniband_hdr | 160 | 563.60 us | 177.4 tok/s | 1,774.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.28 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.33 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-pipeline | DeepSeek-V4.1-Flash | 224 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-tensor | DeepSeek-V4.1-Flash | 224 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-hybrid | DeepSeek-V4.1-Flash | 224 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-expert | DeepSeek-V4.1-Flash | 224 | expert | nvlink3 | infiniband_hdr | 160 | 563.53 us | 177.5 tok/s | 1,774.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.26 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.28 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-pipeline | DeepSeek-V4.1-Flash | 225 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-tensor | DeepSeek-V4.1-Flash | 225 | tensor | nvlink3 | infiniband_hdr | 160 | 826.88 us | 120.9 tok/s | 1,209.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 419.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-hybrid | DeepSeek-V4.1-Flash | 225 | hybrid | nvlink3 | infiniband_hdr | 108 | 475.48 us | 210.3 tok/s | 2,103.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 68.31 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-expert | DeepSeek-V4.1-Flash | 225 | expert | nvlink3 | infiniband_hdr | 160 | 563.53 us | 177.5 tok/s | 1,774.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.26 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.27 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x242-pipeline | DeepSeek-V4.1-Flash | 242 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x242-tensor | DeepSeek-V4.1-Flash | 242 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x242-hybrid | DeepSeek-V4.1-Flash | 242 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x242-expert | DeepSeek-V4.1-Flash | 242 | expert | nvlink3 | infiniband_hdr | 160 | 563.45 us | 177.5 tok/s | 1,774.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.24 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.21 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x244-pipeline | DeepSeek-V4.1-Flash | 244 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x244-tensor | DeepSeek-V4.1-Flash | 244 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x244-hybrid | DeepSeek-V4.1-Flash | 244 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x244-expert | DeepSeek-V4.1-Flash | 244 | expert | nvlink3 | infiniband_hdr | 160 | 563.44 us | 177.5 tok/s | 1,774.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 400.24 us; 80 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 163.21 us |
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
| DeepSeek-V4.1-Flash | 1 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 5,102.9 | 0.037 | 4,844.5 (155,665) | 5,102.9 (138,675) | 1.05x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 2 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 5,102.9 | 0.037 | 4,844.5 (155,665) | 5,102.9 (138,675) | 1.05x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 4 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 5,102.9 | 0.037 | 4,844.5 (155,665) | 5,102.9 (138,675) | 1.05x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 8 | wafer | array | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 5,102.9 | 0.037 | 4,844.5 (155,665) | 5,102.9 (138,675) | 1.05x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 16 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 5,233.2 | 0.028 | 4,844.3 (155,665) | 5,233.2 (184,900) | 1.08x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 32 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 4,900.8 | 0.027 | 4,648.0 (175,225) | 4,900.8 (184,900) | 1.05x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 64 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 5,112.2 | 0.009 | 4,433.2 (185,005) | 5,112.2 (554,700) | 1.15x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 256 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,973.2 | 0.007 | 3,104.3 (277,100) | 3,973.2 (554,700) | 1.28x | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 1024 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1,834.0 | 0.005 | 1,334.1 (277,100) | 1,834.0 (369,800) | 1.37x | weight_read |
| DeepSeek-V4.1-Flash | 4096 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 721.6 | 0.001 | 376.4 (277,100) | 721.6 (554,700) | 1.92x | weight_read |

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
| DeepSeek-V4.1-Flash | 1 | sram | 912,902.1 | 29,014.6 | 29,014.6 | 31.46x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | sram | 912,902.1 | 29,014.6 | 29,014.6 | 31.46x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | sram | 912,902.1 | 29,014.6 | 29,014.6 | 31.46x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 8 | sram | 912,902.1 | 29,014.6 | 29,014.6 | 31.46x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | sram | 912,902.1 | 29,014.6 | 37,308.5 | 31.46x | 1.29x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 32 | sram | 912,902.1 | 29,014.6 | 55,339.1 | 31.46x | 1.91x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | sram | 912,902.1 | 29,014.6 | 79,665.4 | 31.46x | 2.75x | weight_read | weight_read | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 256 | sram | 912,902.1 | 29,014.6 | 157,230.0 | 31.46x | 5.42x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1024 | sram | 1,878,042.9 | 29,014.6 | 262,503.0 | 64.73x | 9.05x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4096 | sram | 2,955,662.7 | 29,014.6 | 398,209.7 | 101.87x | 13.72x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1 | rom | 1,746,110.8 | 30,177.2 | 30,177.2 | 57.86x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | rom | 1,746,110.8 | 30,177.2 | 30,177.2 | 57.86x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | rom | 1,746,110.8 | 30,177.2 | 30,177.2 | 57.86x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 8 | rom | 1,746,110.8 | 30,177.2 | 30,177.2 | 57.86x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | rom | 1,746,110.8 | 30,177.2 | 37,458.0 | 57.86x | 1.24x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 32 | rom | 1,746,110.8 | 30,177.2 | 55,612.8 | 57.86x | 1.84x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | rom | 1,746,110.8 | 30,232.7 | 80,024.2 | 57.76x | 2.65x | compute | weight_read | layer_fixed_latency |
| DeepSeek-V4.1-Flash | 256 | rom | 1,746,110.8 | 30,232.7 | 158,199.0 | 57.76x | 5.23x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1024 | rom | 1,945,266.7 | 30,232.7 | 264,518.6 | 64.34x | 8.75x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4096 | rom | 2,318,090.6 | 30,232.7 | 414,927.2 | 76.67x | 13.72x | compute | weight_read | weight_read |

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
| DeepSeek-V4.1-Flash | 1 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 912,902.1 | 1.646 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,746,110.8 | 3.148 | compute | 1.91x |
| DeepSeek-V4.1-Flash | 1 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 1 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.04 | 1.00 | 30,177.2 | 0.653 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 1 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 1 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.04 | 1.00 | 30,177.2 | 0.653 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 2 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 912,902.1 | 1.646 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 2 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,746,110.8 | 3.148 | compute | 1.91x |
| DeepSeek-V4.1-Flash | 2 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 2 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.04 | 1.00 | 30,177.2 | 0.653 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 2 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 2 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.04 | 1.00 | 30,177.2 | 0.653 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 4 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 912,902.1 | 1.646 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 4 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,746,110.8 | 3.148 | compute | 1.91x |
| DeepSeek-V4.1-Flash | 4 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 4 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.04 | 1.00 | 30,177.2 | 0.653 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 4 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 4 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.04 | 1.00 | 30,177.2 | 0.653 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 8 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 912,902.1 | 1.646 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 8 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,746,110.8 | 3.148 | compute | 1.91x |
| DeepSeek-V4.1-Flash | 8 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 8 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.04 | 1.00 | 30,177.2 | 0.653 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 8 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 8 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.04 | 1.00 | 30,177.2 | 0.653 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 16 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 912,902.1 | 1.646 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 16 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,746,110.8 | 3.148 | compute | 1.91x |
| DeepSeek-V4.1-Flash | 16 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 16 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.04 | 1.00 | 30,177.2 | 0.653 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 16 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x54-perregion | 44,010 | 1.00 | 1.43 | 37,308.5 | 0.848 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 16 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion-romfill | 48,900 | 1.01 | 1.43 | 37,458.0 | 0.766 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 32 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 912,902.1 | 1.646 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 32 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,746,110.8 | 3.148 | compute | 1.91x |
| DeepSeek-V4.1-Flash | 32 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 32 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.04 | 1.00 | 30,177.2 | 0.653 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 32 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion | 48,900 | 1.00 | 1.99 | 55,339.1 | 1.132 | weight_read | 0.06x |
| DeepSeek-V4.1-Flash | 32 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion-romfill | 48,900 | 1.01 | 1.99 | 55,612.8 | 1.137 | weight_read | 0.06x |
| DeepSeek-V4.1-Flash | 64 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 912,902.1 | 1.646 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 64 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,746,110.8 | 3.148 | compute | 1.91x |
| DeepSeek-V4.1-Flash | 64 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 64 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.04 | 1.12 | 30,232.7 | 0.654 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 64 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion | 48,900 | 1.00 | 2.54 | 79,665.4 | 1.629 | layer_fixed_latency | 0.09x |
| DeepSeek-V4.1-Flash | 64 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion-romfill | 48,900 | 1.01 | 2.54 | 80,024.2 | 1.636 | layer_fixed_latency | 0.09x |
| DeepSeek-V4.1-Flash | 256 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 912,902.1 | 1.646 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 256 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,746,110.8 | 3.148 | compute | 1.91x |
| DeepSeek-V4.1-Flash | 256 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 29,014.6 | 0.628 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 256 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.04 | 4.49 | 30,232.7 | 0.654 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 256 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion | 48,900 | 1.00 | 3.49 | 157,230.0 | 3.215 | weight_read | 0.17x |
| DeepSeek-V4.1-Flash | 256 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion-romfill | 48,900 | 1.01 | 3.49 | 158,199.0 | 3.235 | weight_read | 0.17x |
| DeepSeek-V4.1-Flash | 1024 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 1,878,042.9 | 5.079 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1024 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 1,945,266.7 | 3.507 | compute | 1.04x |
| DeepSeek-V4.1-Flash | 1024 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 17.96 | 29,014.6 | 0.628 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash | 1024 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.04 | 17.96 | 30,232.7 | 0.654 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash | 1024 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion | 48,900 | 1.00 | 5.09 | 262,503.0 | 5.368 | weight_read | 0.14x |
| DeepSeek-V4.1-Flash | 1024 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x60-perregion-romfill | 48,900 | 1.01 | 5.09 | 264,518.6 | 5.409 | weight_read | 0.14x |
| DeepSeek-V4.1-Flash | 4096 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 2,955,662.7 | 5.328 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 4096 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 2,318,090.6 | 4.179 | compute | 0.78x |
| DeepSeek-V4.1-Flash | 4096 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 71.86 | 29,014.6 | 0.628 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash | 4096 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 1.04 | 71.86 | 30,232.7 | 0.654 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash | 4096 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 5.24 | 398,209.7 | 8.615 | weight_read | 0.13x |
| DeepSeek-V4.1-Flash | 4096 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 1.04 | 5.24 | 414,927.2 | 8.976 | weight_read | 0.14x |

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
| DeepSeek-V4.1-Flash | 4 | 54 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 8 | 54 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 16 | 54 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 32 | 54 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 64 | 57 | 1.12 | 1.001 | 1.009 | 1.01x |
| DeepSeek-V4.1-Flash | 256 | 57 | 4.49 | 1.028 | 1.519 | 1.48x |
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
| DeepSeek-V4.1-Flash | 1 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4.1-Flash | 2 | 8 | 6.37 | 3.69 | 1.73x |
| DeepSeek-V4.1-Flash | 4 | 8 | 7.65 | 4.39 | 1.74x |
| DeepSeek-V4.1-Flash | 8 | 8 | 7.98 | 5.05 | 1.58x |
| DeepSeek-V4.1-Flash | 16 | 8 | 8.00 | 5.63 | 1.42x |
| DeepSeek-V4.1-Flash | 32 | 8 | 8.00 | 6.09 | 1.31x |
| DeepSeek-V4.1-Flash | 64 | 8 | 8.00 | 6.42 | 1.25x |
| DeepSeek-V4.1-Flash | 256 | 8 | 8.00 | 6.68 | 1.20x |
| DeepSeek-V4.1-Flash | 1024 | 8 | 8.00 | 6.69 | 1.20x |
| DeepSeek-V4.1-Flash | 4096 | 8 | 8.00 | 6.69 | 1.20x |
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
| DeepSeek-V4.1-Flash | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4.1-Flash | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4.1-Flash | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4.1-Flash | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4.1-Flash | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4.1-Flash | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4.1-Flash | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash | 4096 | 58 | 57.93 | 29.20 | 1.98x |
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
| DeepSeek-V4.1-Flash | 1 | 107 | 5.86 | 5.32 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 107 | 11.32 | 8.19 | 1.38x |
| DeepSeek-V4.1-Flash | 4 | 107 | 21.14 | 11.57 | 1.83x |
| DeepSeek-V4.1-Flash | 8 | 107 | 37.17 | 16.77 | 2.22x |
| DeepSeek-V4.1-Flash | 16 | 107 | 59.07 | 22.82 | 2.59x |
| DeepSeek-V4.1-Flash | 32 | 107 | 81.33 | 29.45 | 2.76x |
| DeepSeek-V4.1-Flash | 64 | 107 | 96.16 | 35.61 | 2.70x |
| DeepSeek-V4.1-Flash | 256 | 107 | 103.90 | 41.71 | 2.49x |
| DeepSeek-V4.1-Flash | 1024 | 107 | 104.09 | 41.96 | 2.48x |
| DeepSeek-V4.1-Flash | 4096 | 107 | 104.09 | 41.96 | 2.48x |
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
| DeepSeek-V4.1-Flash | 1 | 114 | 5.87 | 5.36 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 114 | 11.35 | 8.31 | 1.37x |
| DeepSeek-V4.1-Flash | 4 | 114 | 21.27 | 11.74 | 1.81x |
| DeepSeek-V4.1-Flash | 8 | 114 | 37.62 | 17.11 | 2.20x |
| DeepSeek-V4.1-Flash | 16 | 114 | 60.34 | 23.37 | 2.58x |
| DeepSeek-V4.1-Flash | 32 | 114 | 84.13 | 30.29 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 114 | 100.70 | 36.74 | 2.74x |
| DeepSeek-V4.1-Flash | 256 | 114 | 109.89 | 43.18 | 2.55x |
| DeepSeek-V4.1-Flash | 1024 | 114 | 110.13 | 43.45 | 2.53x |
| DeepSeek-V4.1-Flash | 4096 | 114 | 110.13 | 43.45 | 2.53x |
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
| DeepSeek-V4.1-Flash | 1 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4.1-Flash | 2 | 139 | 11.45 | 8.69 | 1.32x |
| DeepSeek-V4.1-Flash | 4 | 139 | 21.64 | 12.29 | 1.76x |
| DeepSeek-V4.1-Flash | 8 | 139 | 38.89 | 18.19 | 2.14x |
| DeepSeek-V4.1-Flash | 16 | 139 | 64.04 | 25.07 | 2.55x |
| DeepSeek-V4.1-Flash | 32 | 139 | 92.62 | 32.95 | 2.81x |
| DeepSeek-V4.1-Flash | 64 | 139 | 115.10 | 40.42 | 2.85x |
| DeepSeek-V4.1-Flash | 256 | 139 | 129.87 | 47.97 | 2.71x |
| DeepSeek-V4.1-Flash | 1024 | 139 | 130.31 | 48.29 | 2.70x |
| DeepSeek-V4.1-Flash | 4096 | 139 | 130.31 | 48.29 | 2.70x |
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
| DeepSeek-V4.1-Flash | 1 | 188 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4.1-Flash | 2 | 188 | 11.57 | 9.23 | 1.25x |
| DeepSeek-V4.1-Flash | 4 | 188 | 22.10 | 13.19 | 1.67x |
| DeepSeek-V4.1-Flash | 8 | 188 | 40.47 | 19.71 | 2.05x |
| DeepSeek-V4.1-Flash | 16 | 188 | 68.86 | 27.66 | 2.49x |
| DeepSeek-V4.1-Flash | 32 | 188 | 104.43 | 37.13 | 2.81x |
| DeepSeek-V4.1-Flash | 64 | 188 | 136.79 | 46.29 | 2.96x |
| DeepSeek-V4.1-Flash | 256 | 188 | 162.85 | 55.79 | 2.92x |
| DeepSeek-V4.1-Flash | 1024 | 188 | 163.75 | 56.20 | 2.91x |
| DeepSeek-V4.1-Flash | 4096 | 188 | 163.75 | 56.20 | 2.91x |
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
| DeepSeek-V4.1-Flash | 1 | 212 | 5.93 | 5.63 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 212 | 11.60 | 9.44 | 1.23x |
| DeepSeek-V4.1-Flash | 4 | 212 | 22.24 | 13.58 | 1.64x |
| DeepSeek-V4.1-Flash | 8 | 212 | 41.00 | 20.26 | 2.02x |
| DeepSeek-V4.1-Flash | 16 | 212 | 70.52 | 28.75 | 2.45x |
| DeepSeek-V4.1-Flash | 32 | 212 | 108.68 | 38.88 | 2.80x |
| DeepSeek-V4.1-Flash | 64 | 212 | 145.07 | 48.74 | 2.98x |
| DeepSeek-V4.1-Flash | 256 | 212 | 176.37 | 59.06 | 2.99x |
| DeepSeek-V4.1-Flash | 1024 | 212 | 177.50 | 59.50 | 2.98x |
| DeepSeek-V4.1-Flash | 4096 | 212 | 177.50 | 59.50 | 2.98x |
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
| DeepSeek-V4.1-Flash | 1 | 242 | 5.94 | 5.67 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 242 | 11.64 | 9.65 | 1.21x |
| DeepSeek-V4.1-Flash | 4 | 242 | 22.39 | 14.02 | 1.60x |
| DeepSeek-V4.1-Flash | 8 | 242 | 41.52 | 20.82 | 1.99x |
| DeepSeek-V4.1-Flash | 16 | 242 | 72.17 | 30.00 | 2.41x |
| DeepSeek-V4.1-Flash | 32 | 242 | 113.04 | 40.85 | 2.77x |
| DeepSeek-V4.1-Flash | 64 | 242 | 153.83 | 51.48 | 2.99x |
| DeepSeek-V4.1-Flash | 256 | 242 | 191.24 | 62.77 | 3.05x |
| DeepSeek-V4.1-Flash | 1024 | 242 | 192.65 | 63.27 | 3.05x |
| DeepSeek-V4.1-Flash | 4096 | 242 | 192.65 | 63.27 | 3.05x |
| DeepSeek-V4.1-Flash | 1 | 244 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 244 | 11.64 | 9.67 | 1.20x |
| DeepSeek-V4.1-Flash | 4 | 244 | 22.40 | 14.05 | 1.59x |
| DeepSeek-V4.1-Flash | 8 | 244 | 41.55 | 20.86 | 1.99x |
| DeepSeek-V4.1-Flash | 16 | 244 | 72.27 | 30.08 | 2.40x |
| DeepSeek-V4.1-Flash | 32 | 244 | 113.30 | 40.97 | 2.77x |
| DeepSeek-V4.1-Flash | 64 | 244 | 154.36 | 51.65 | 2.99x |
| DeepSeek-V4.1-Flash | 256 | 244 | 192.16 | 63.01 | 3.05x |
| DeepSeek-V4.1-Flash | 1024 | 244 | 193.59 | 63.50 | 3.05x |
| DeepSeek-V4.1-Flash | 4096 | 244 | 193.59 | 63.50 | 3.05x |
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
| gpu | DeepSeek-V4.1-Flash | 1 | 860.60 | 32.6% |
| rom | DeepSeek-V4.1-Flash | 1 | 139.86 | 73.2% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash | sram | interleaved | 128 B | 1.42x |
| DeepSeek-V4.1-Flash | hbm | interleaved | 32 B | 1.12x |

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
| DeepSeek-V4.1-Flash | 1 | 54 | 1.78% | 15.14 | 15.79 |
| DeepSeek-V4.1-Flash | 2 | 54 | 1.78% | 15.14 | 15.79 |
| DeepSeek-V4.1-Flash | 4 | 54 | 1.78% | 15.14 | 15.79 |
| DeepSeek-V4.1-Flash | 8 | 54 | 1.78% | 15.14 | 15.79 |
| DeepSeek-V4.1-Flash | 16 | 54 | 1.78% | 15.14 | 15.79 |
| DeepSeek-V4.1-Flash | 32 | 54 | 1.78% | 15.14 | 15.79 |
| DeepSeek-V4.1-Flash | 64 | 1 | 0.23% | 2.09 | 15.79 |
| DeepSeek-V4.1-Flash | 256 | 1 | 0.93% | 8.37 | 15.79 |

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
| DeepSeek-V4.1-Flash | 1 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 495.8 | 56,517.9 |
| DeepSeek-V4.1-Flash | 2 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 495.8 | 56,517.9 |
| DeepSeek-V4.1-Flash | 4 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 495.8 | 56,517.9 |
| DeepSeek-V4.1-Flash | 8 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 495.8 | 56,517.9 |
| DeepSeek-V4.1-Flash | 16 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 495.8 | 56,517.9 |
| DeepSeek-V4.1-Flash | 32 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 495.8 | 56,517.9 |
| DeepSeek-V4.1-Flash | 64 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 495.8 | 56,517.9 |
| DeepSeek-V4.1-Flash | 256 | 3.47% | 18.6 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 224.7 | 57,529.0 |
| DeepSeek-V4.1-Flash | 1024 | 13.19% | 46.6 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 56.2 | 57,529.0 |
| DeepSeek-V4.1-Flash | 4096 | 43.21% | 133.3 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 14.0 | 57,529.0 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 2 |
| gpu | link_latency | 707 |
| gpu | weight_read | 521 |
| rom | compute | 776 |
| rom | infeasible | 1820 |
| rom | kv_read | 48 |
| rom | layer_fixed_latency | 631 |
| rom | link_latency | 771 |
| rom | weight_read | 314 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 1820 |

## Mechanical consistency audit

**FAIL** over 119,151 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x108', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x112', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x114', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x132', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x158', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x210', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x315', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x108', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x112', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x114', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x132', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x158', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x210', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x315', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x108', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x112', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x114', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x132', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x158', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x210', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x315', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x108', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x112', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x114', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x132', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x158', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x210', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x315', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4.1-Flash', 1)

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

# Area-constrained roofline: n6_vs_a100-mimo-v26-flash-8k

> CANDIDATE MODEL under n6_vs_a100: MiMo-V2.6-Flash at 8,192 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 60x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 63 devices. On the GPU side the correction reaches 8x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 15 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Flash takes 43 x 815 mm2 (35,045 mm2, array, KV in SRAM) at 5,773 tok/s per user and 165 tok/s per 1,000 mm2, holding 1 session, against 42 copies of one unified HBM die at the same silicon: 16.1x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Flash on 54,605 mm2 of ROM silicon at 6,797 tok/s per user against 54,516 mm2 of a100_sxm_80gb-x66-hybrid at 363 tok/s: **18.7x**, ROM binding on `layer_fixed_latency` and the GPU on `weight_read`. It holds 22,510 resident sessions against the GPU cluster's 21,367. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on MiMo-V2.6-Flash at batch 1, the iso-area GPU cluster is 672 devices. Cut as one serial pipeline that is 84 stages and 927 us of link latency per token; but the model has 48 layers, so at most 48 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 842 us. The iso-area per-user ratio at that point falls from 15.8x to 15.3x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 3.34x to it.** At 39,935 mm2 on MiMo-V2.6-Flash the pipeline-only GPU delivers 112.87 tok/s and the same silicon running hybrid delivers 377 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.03x (MiMo-V2.6-Flash, ROM binding on `link_latency`) to 7.06x (MiMo-V2.6-Flash, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Flash engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 659 to 28,583 tok/s, and its rate with every slot occupied from 27,028 to 28,583. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 41 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,360 us over NVLink, capping per-user decode at 735 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 206.1 us and cap it at 4,852 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 5.2x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 0 of 10 operating points and an array 10; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 280 of 4556 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 56.8x of aggregate throughput (MiMo-V2.6-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 5.06x, on MiMo-V2.6-Flash at batch 4096, where the busiest region carries 2.99x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### MiMo-V2.6-Flash at 8,192 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-hybrid-x43`** -- 43 x 815 mm2 reticle dies, 35,045 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **5,772.9 tok/s per user** (0.17 ms/token), binding on `layer_fixed_latency`
- **164.7 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 5,773 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 2,184 W at 0.062 W/mm2, 378.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 42 copies of one unified HBM die -- `a100_sxm_80gb-x42-hybrid`, 34,692 mm2, area ratio 1.0102 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 35,045 | 34,692 | 1.0102 |
| user tok/s | 5,772.9 | 357.8 | 16.14x |
| aggregate tok/s | 5,773 | 2,147 | 1.22x |
| resident sessions | 1 | 13,303 | -- |
| J/token | 0.3783 | 18.3063 | 48.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 13,303 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x40-hybrid` at 33,040 mm2 and 376.9 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-array-hw-hybrid-x63` | 51,345 | 6,764.9 | 131.8 | 21,166 | 18.21x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 63,570 | 6,845.8 | 107.7 | 26,205 | 18.51x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x38` | 30,970 | 4,314.5 | 139.3 | 1 | 11.79x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | 35,045 | 5,772.9 | 164.7 | 1 | 16.14x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | 35,045 | 5,772.9 | 164.7 | -- | 164.7 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x45` | 36,675 | 5,804.8 | 158.3 | 19.6 | 164.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x47` | 38,305 | 5,990.8 | 156.4 | 66.8 | 164.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x52` | 42,380 | 6,130.6 | 144.7 | 48.8 | 164.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x57` | 46,455 | 6,340.1 | 136.5 | 49.7 | 164.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x59` | 48,085 | 6,460.4 | 134.4 | 52.7 | 164.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x63` | 51,345 | 6,764.9 | 131.8 | 60.9 | 164.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x67` | 54,605 | 6,797.2 | 124.5 | 52.4 | 164.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 6,831.7 | 123.3 | 52.0 | 164.7 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 63,570 | 6,845.8 | 107.7 | 37.6 | 164.7 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` **<-- recommended** | 35,045 | 43 | 5,772.9 | 5,773 | 164.7 | 1 | `layer_fixed_latency` | 2,184 | 378.3 | `a100_sxm_80gb-x42-hybrid` | 16.14x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x45` | 36,675 | 45 | 5,804.8 | 5,805 | 158.3 | 1 | `layer_fixed_latency` | 2,367 | 407.7 | `a100_sxm_80gb-x44-hybrid` | 15.93x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x47` | 38,305 | 47 | 5,990.8 | 17,972 | 156.4 | 15,790 | `layer_fixed_latency` | 3,735 | 568.0 | `a100_sxm_80gb-x46-hybrid` | 16.16x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x52` | 42,380 | 52 | 6,130.6 | 24,522 | 144.7 | 17,470 | `layer_fixed_latency` | 4,578 | 663.5 | `a100_sxm_80gb-x51-hybrid` | 16.88x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x57` | 46,455 | 57 | 6,340.1 | 25,361 | 136.5 | 19,150 | `layer_fixed_latency` | 5,262 | 746.7 | `a100_sxm_80gb-x56-hybrid` | 16.85x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x59` | 48,085 | 59 | 6,460.4 | 51,683 | 134.4 | 19,822 | `layer_fixed_latency` | 6,258 | 774.2 | `a100_sxm_80gb-x58-hybrid` | 17.84x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x63` | 51,345 | 63 | 6,764.9 | 54,119 | 131.8 | 21,166 | `layer_fixed_latency` | 6,854 | 818.8 | `a100_sxm_80gb-x62-hybrid` | 18.21x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x67` | 54,605 | 67 | 6,797.2 | 61,174 | 124.5 | 22,510 | `layer_fixed_latency` | 7,579 | 892.8 | `a100_sxm_80gb-x66-hybrid` | 18.70x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 68 | 6,831.7 | 61,486 | 123.3 | 22,846 | `layer_fixed_latency` | 7,720 | 907.8 | `a100_sxm_80gb-x67-hybrid` | 18.69x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 63,570 | 78 | 6,845.8 | 68,458 | 107.7 | 26,205 | `layer_fixed_latency` | 8,962 | 1,059.1 | `a100_sxm_80gb-x77-hybrid` | 18.51x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 348 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | 35,045 | 5,772.9 | 164.7 | 1 |
| array | 348 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 63,570 | 6,845.8 | 107.7 | 26,205 |
| array | 348 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x38` | 30,970 | 4,314.5 | 139.3 | 1 |
| wafer | 76 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,526.8 | 119.6 | 1 |
| wafer | 76 | fastest | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,680.5 | 30.7 | 11,557 |
| wafer | 76 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,526.8 | 119.6 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 63,570 | 6,845.8 | 68,458 | 26,205 | 8,962 | 1,059.1 | `layer_fixed_latency` | `a100_sxm_80gb-x77-hybrid` | 369.9 | 25,063 | 31,409.2 | 0.999 | 18.51x | 29.7x |
| 1 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,680.5 | 45,444 | 11,557 | 25,578 | 4,308.4 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 369.3 | 74,451 | 88,925.5 | 0.999 | 15.38x | 20.6x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 6,745.4 | 195,616 | 76,265 | 25,980 | 3,073.9 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 369.3 | 74,451 | 88,925.5 | 1.000 | 18.26x | 28.9x |
| 1 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,680.5 | -- | 11,557 | -- | 4,308.4 | -- | -- | -- | -- | -- | 1.001 | 0.84x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 63,570 | 6,845.8 | 68,458 | 26,205 | 8,962 | 543.4 | `layer_fixed_latency` | `a100_sxm_80gb-x77-hybrid` | 369.9 | 25,063 | 16,383.0 | 0.999 | 18.51x | 30.1x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,680.5 | 45,444 | 11,557 | 25,578 | 2,168.1 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 369.3 | 74,451 | 45,141.2 | 0.999 | 15.38x | 20.8x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 6,745.4 | 195,616 | 76,265 | 25,980 | 1,550.8 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 369.3 | 74,451 | 45,141.2 | 1.000 | 18.26x | 29.1x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,680.5 | -- | 11,557 | -- | 2,168.1 | -- | -- | -- | -- | -- | 1.001 | 0.84x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 63,570 | 6,845.8 | 68,458 | 26,205 | 8,962 | 285.6 | `layer_fixed_latency` | `a100_sxm_80gb-x77-hybrid` | 369.9 | 25,063 | 8,869.9 | 0.999 | 18.51x | 31.1x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,680.5 | 45,444 | 11,557 | 25,578 | 1,097.9 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 369.3 | 74,451 | 23,249.0 | 0.999 | 15.38x | 21.2x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 6,745.4 | 195,616 | 76,265 | 25,980 | 789.3 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 369.3 | 74,451 | 23,249.0 | 1.000 | 18.26x | 29.5x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,680.5 | -- | 11,557 | -- | 1,097.9 | -- | -- | -- | -- | -- | 1.001 | 0.84x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill` | 63,570 | 6,845.8 | 68,458 | 26,205 | 8,962 | 156.7 | `layer_fixed_latency` | `a100_sxm_80gb-x77-hybrid` | 369.9 | 25,063 | 5,113.4 | 0.999 | 18.51x | 32.6x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,680.5 | 45,444 | 11,557 | 25,578 | 562.8 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 369.3 | 74,451 | 12,302.9 | 0.999 | 15.38x | 21.9x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 6,745.4 | 195,616 | 76,265 | 25,980 | 408.5 | `layer_fixed_latency` | `a100_sxm_80gb-x224-hybrid` | 369.3 | 74,451 | 12,302.9 | 1.000 | 18.26x | 30.1x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 5,680.5 | -- | 11,557 | -- | 562.8 | -- | -- | -- | -- | -- | 1.001 | 0.84x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 127,140 | 6,790.9 | 135,817 | 52,411 | 17,893 | 157.7 | `layer_fixed_latency` | `a100_sxm_80gb-x154-hybrid` | 366.7 | 50,932 | 5,146.2 | 0.999 | 18.52x | 32.6x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,547.9 | 122,053 | 34,672 | 54,968 | 608.8 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 363.0 | 224,967 | 18,061.9 | 0.999 | 15.28x | 29.7x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,679.9 | 287,236 | 114,230 | 38,753 | 171.7 | `layer_fixed_latency` | `a100_sxm_80gb-x335-hybrid` | 364.5 | 111,744 | 5,503.7 | 1.001 | 18.33x | 32.0x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,370.5 | 230,933 | 34,672 | 57,992 | 327.9 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 363.0 | 224,967 | 9,709.4 | 0.999 | 14.79x | 29.6x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,338.1 | 538,738 | 114,230 | 45,738 | 103.6 | `layer_fixed_latency` | `a100_sxm_80gb-x335-hybrid` | 337.9 | 111,744 | 3,312.6 | 1.001 | 18.75x | 32.0x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,465.8 | 384,062 | 34,672 | 62,244 | 208.2 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 363.0 | 224,967 | 5,533.1 | 0.999 | 12.30x | 26.6x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 3,960.9 | 1,013,984 | 114,230 | 58,117 | 57.3 | `compute` | `a100_sxm_80gb-x335-hybrid` | 212.3 | 111,744 | 1,534.6 | 1.001 | 18.65x | 26.8x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,332.7 | 597,164 | 34,672 | 67,686 | 113.3 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 279.3 | 224,967 | 2,157.5 | 0.999 | 8.35x | 19.0x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 1,434.4 | 1,468,799 | 114,230 | 69,172 | 47.1 | `compute` | `a100_sxm_80gb-x335-hybrid` | 101.5 | 111,744 | 897.1 | 1.001 | 14.14x | 19.0x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 723.5 | 740,899 | 34,672 | 71,558 | 96.6 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 148.4 | 224,967 | 1,174.6 | 0.999 | 4.88x | 12.2x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 396.7 | 1,625,078 | 114,230 | 71,983 | 44.3 | `compute` | `a100_sxm_80gb-x335-hybrid` | 56.2 | 111,744 | 408.8 | 1.001 | 7.06x | 9.2x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 190.0 | 778,375 | 34,672 | 71,567 | 91.9 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 71.9 | 224,967 | 644.1 | 0.999 | 2.64x | 7.0x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | 35,045 | array | SRAM | 1 |
| 2 | `ROM-N6-native-HBMKV-array-hw-hybrid-x47` | 38,305 | array | HBM | 15,790 |
| 4 | `ROM-N6-native-HBMKV-array-hw-hybrid-x49` | 39,935 | array | HBM | 16,462 |
| 8 | `ROM-N6-native-HBMKV-array-hw-hybrid-x57` | 46,455 | array | HBM | 19,150 |
| 16-32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x63` | 51,345 | array | HBM | 21,166 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x78` | 63,570 | array | HBM | 26,205 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x113` | 92,095 | array | HBM | 37,964 |
| 1024 | `ROM-N6-native-HBMKV-array-hw-pipeline-x113` | 92,095 | array | HBM | 37,964 |
| 4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x156` | 127,140 | array | HBM | 52,411 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Flash | HBM | rom | 41, 47, 49, 52, 57, 59, 63, 67, 68, 78, 113, 117, 156, 170, 227, 340 |
| MiMo-V2.6-Flash | HBM | sram | 41, 47, 49, 52, 57, 59, 63, 67, 68, 78, 113, 117, 156, 170, 227, 340 |
| MiMo-V2.6-Flash | SRAM | rom | 38, 42, 43, 45, 54, 57, 72, 108, 113, 144, 170, 227, 340 |
| MiMo-V2.6-Flash | SRAM | sram | 38, 42, 43, 45, 54, 57, 72, 108, 113, 144, 170, 227, 340 |

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
| MiMo-V2.6-Flash | `ROM-N6-native-SRAMKV-array-hw-hybrid-x43` | 1 | 16 | 3.00 | hierarchical | 111.80 | 36.82 | 32.19 | 35.51 | 5,772.9 |
| MiMo-V2.6-Flash | `a100_sxm_80gb-x42-hybrid` | 1 | 8 | 3.00 | measured_floor | 937.30 | 743.13 | 1,114.60 | 509.50 | 357.8 |
| MiMo-V2.6-Flash | `a100_sxm_80gb-x42-hybrid` | 64 | 8 | 3.00 | measured_floor | 937.30 | 849.02 | 4,856.20 | 591.86 | 150.5 |

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

- **0 of 4,556 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 520 | 0 | 52.1% | 80.3% | 0.389 | 69% |
| gpu | wafer (>=40,000 mm2) | 840 | 0 | 51.5% | 79.4% | 0.385 | 83% |
| rom | large array (5,000-40,000 mm2) | 972 | 0 | 20.8% | 55.0% | 0.275 | 78% |
| rom | wafer (>=40,000 mm2) | 2,224 | 0 | 27.1% | 70.8% | 0.354 | 87% |

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
| MiMo-V2.6-Flash | 1 | 51,345 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x63` | 0.818773 | 6,854.0 | layer_fixed_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x62-hybrid` | 25.454133 | 12,984.2 | layer_fixed_latency | 31.09x |
| MiMo-V2.6-Flash | 2 | 51,345 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x63` | 0.423273 | 6,854.0 | layer_fixed_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x62-hybrid` | 13.405493 | 12,984.2 | layer_fixed_latency | 31.67x |
| MiMo-V2.6-Flash | 4 | 51,345 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x63` | 0.225523 | 6,854.0 | layer_fixed_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x62-hybrid` | 7.381174 | 12,984.2 | layer_fixed_latency | 32.73x |
| MiMo-V2.6-Flash | 8 | 51,345 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x63` | 0.126648 | 6,854.0 | layer_fixed_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x62-hybrid` | 4.369014 | 12,984.2 | layer_fixed_latency | 34.50x |
| MiMo-V2.6-Flash | 16 | 55,420 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 0.085389 | 9,090.9 | layer_fixed_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x67-hybrid` | 2.853547 | 14,883.7 | weight_read | 33.42x |
| MiMo-V2.6-Flash | 32 | 127,140 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 0.096925 | 21,032.2 | layer_fixed_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x154-hybrid` | 3.119382 | 33,526.2 | weight_read | 32.18x |
| MiMo-V2.6-Flash | 64 | 185,005 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 0.080787 | 31,157.3 | layer_fixed_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x224-hybrid` | 2.523288 | 50,097.1 | weight_read | 31.23x |
| MiMo-V2.6-Flash | 256 | 277,100 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.057316 | 58,117.0 | compute | `MiMo-V2.6-Flash/a100_sxm_80gb-x335-hybrid` | 1.534603 | 83,422.9 | weight_read | 26.77x |
| MiMo-V2.6-Flash | 1024 | 277,100 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.047094 | 69,172.0 | compute | `MiMo-V2.6-Flash/a100_sxm_80gb-x335-hybrid` | 0.897088 | 93,216.8 | weight_read | 19.05x |
| MiMo-V2.6-Flash | 4096 | 277,100 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.044295 | 71,982.6 | compute | `MiMo-V2.6-Flash/a100_sxm_80gb-x335-hybrid` | 0.408782 | 94,126.2 | weight_read | 9.23x |

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
| MiMo-V2.6-Flash | 8,192 | 309 B | 172.9 GB | 4.48 | 0.214 GB | 0.214 GB | 59.1 |

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
| MiMo-V2.6-Flash | 1 | 46,225 | 8,486.3 | wafer-pipeline | 5,526.8 | wafer-tensor | 1.54x | 835.7 | pipeline | 376.2 | hybrid | 2.22x | 10.15x | 14.69x | 1.45x |
| MiMo-V2.6-Flash | 2 | 92,450 | 8,610.7 | wafer-pipeline | 5,620.3 | wafer-hybrid | 1.53x | 887.4 | pipeline | 373.9 | hybrid | 2.37x | 9.70x | 15.03x | 1.55x |
| MiMo-V2.6-Flash | 3 | 138,675 | 8,780.4 | wafer-pipeline | 5,667.7 | wafer-hybrid | 1.55x | 906.0 | pipeline | 371.6 | hybrid | 2.44x | 9.69x | 15.25x | 1.57x |
| MiMo-V2.6-Flash | 4 | 184,900 | 8,860.3 | wafer-pipeline | 5,680.5 | wafer-hybrid | 1.56x | 915.7 | pipeline | 369.3 | hybrid | 2.48x | 9.68x | 15.38x | 1.59x |
| MiMo-V2.6-Flash | 6 | 277,350 | 8,924.1 | wafer-pipeline | 5,680.3 | wafer-hybrid | 1.57x | 925.5 | pipeline | 364.9 | hybrid | 2.54x | 9.64x | 15.57x | 1.61x |
| MiMo-V2.6-Flash | 8 | 369,800 | 8,938.2 | wafer-pipeline | 5,555.2 | wafer-hybrid | 1.61x | 930.5 | pipeline | 363.0 | hybrid | 2.56x | 9.61x | 15.30x | 1.59x |
| MiMo-V2.6-Flash | 12 | 554,700 | 8,954.8 | wafer-pipeline | 5,547.9 | wafer-hybrid | 1.61x | 935.6 | pipeline | 363.0 | hybrid | 2.58x | 9.57x | 15.28x | 1.60x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.45x to 1.61x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Flash | 1 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill | 63,570 | 6,845.8 | 68,458.0 | layer_fixed_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x77-hybrid | 63,602 | 1.00x | hybrid | 752.56 | 369.9 | 3,699.4 | layer_fixed_latency | 18.51x | 7.88x | 60.65x | 18.51x |
| MiMo-V2.6-Flash | 1 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x38 | 30,970 | 4,314.5 | 4,314.5 | layer_fixed_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x37-hybrid | 30,562 | 1.01x | hybrid | 740.78 | 366.0 | 1,829.9 | layer_fixed_latency | 11.79x | 1.03x | 38.11x | 11.79x |
| MiMo-V2.6-Flash | 2 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill | 63,570 | 6,845.8 | 68,458.0 | layer_fixed_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x77-hybrid | 63,602 | 1.00x | hybrid | 752.56 | 369.9 | 3,699.4 | layer_fixed_latency | 18.51x | 7.88x | 60.65x | 18.51x |
| MiMo-V2.6-Flash | 2 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x41 | 33,415 | 4,145.2 | 8,290.3 | layer_fixed_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 740.78 | 376.9 | 1,884.4 | layer_fixed_latency | 11.00x | 1.83x | 36.64x | 11.00x |
| MiMo-V2.6-Flash | 4 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill | 63,570 | 6,845.8 | 68,458.0 | layer_fixed_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x77-hybrid | 63,602 | 1.00x | hybrid | 752.56 | 369.9 | 3,699.4 | layer_fixed_latency | 18.51x | 7.88x | 60.65x | 18.51x |
| MiMo-V2.6-Flash | 4 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x41 | 33,415 | 3,516.9 | 14,067.5 | layer_fixed_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 740.78 | 376.9 | 1,884.4 | layer_fixed_latency | 9.33x | 3.11x | 31.09x | 9.33x |
| MiMo-V2.6-Flash | 8 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x78-romfill | 63,570 | 6,845.8 | 68,458.0 | layer_fixed_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x77-hybrid | 63,602 | 1.00x | hybrid | 752.56 | 369.9 | 3,699.4 | layer_fixed_latency | 18.51x | 7.88x | 60.65x | 18.51x |
| MiMo-V2.6-Flash | 8 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x41 | 33,415 | 2,494.0 | 19,951.6 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 747.15 | 345.8 | 2,766.2 | weight_read | 7.21x | 4.41x | 22.05x | 7.21x |
| MiMo-V2.6-Flash | 16 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill | 127,140 | 6,790.9 | 135,817.0 | layer_fixed_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x154-hybrid | 127,204 | 1.00x | hybrid | 776.14 | 366.7 | 7,334.8 | layer_fixed_latency | 18.52x | 7.81x | 60.16x | 18.52x |
| MiMo-V2.6-Flash | 16 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x41 | 33,415 | 1,510.9 | 24,175.1 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 764.15 | 285.1 | 4,560.8 | weight_read | 5.30x | 5.30x | 13.36x | 5.30x |
| MiMo-V2.6-Flash | 32 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,679.9 | 287,235.6 | layer_fixed_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 828.01 | 364.5 | 15,308.9 | layer_fixed_latency | 18.33x | 7.60x | 59.18x | 18.33x |
| MiMo-V2.6-Flash | 32 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x41 | 33,415 | 823.0 | 26,335.6 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 798.16 | 214.7 | 6,872.0 | weight_read | 3.83x | 3.83x | 7.27x | 3.83x |
| MiMo-V2.6-Flash | 64 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,338.1 | 538,738.4 | layer_fixed_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 839.93 | 337.9 | 21,628.6 | weight_read | 18.75x | 14.25x | 56.15x | 18.75x |
| MiMo-V2.6-Flash | 64 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x41 | 33,415 | 431.0 | 27,583.1 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 866.17 | 150.3 | 9,616.1 | weight_read | 2.87x | 2.87x | 4.61x | 2.87x |
| MiMo-V2.6-Flash | 256 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 3,960.9 | 1,013,983.6 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 943.93 | 212.3 | 54,361.2 | weight_read | 18.65x | 18.65x | 35.09x | 18.65x |
| MiMo-V2.6-Flash | 256 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x41 | 33,415 | 110.8 | 28,362.4 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 1,274.23 | 74.6 | 19,104.5 | weight_read | 1.48x | 1.48x | 2.71x | 1.48x |
| MiMo-V2.6-Flash | 1024 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 1,434.4 | 1,468,799.1 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 1,359.94 | 101.5 | 103,910.3 | weight_read | 14.14x | 14.14x | 21.65x | 14.14x |
| MiMo-V2.6-Flash | 1024 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x41 | 33,415 | 27.9 | 28,559.3 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 2,906.45 | 50.2 | 51,447.2 | weight_read | 0.56x | 0.56x | 1.76x | 0.56x |
| MiMo-V2.6-Flash | 4096 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 396.7 | 1,625,077.6 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 3,023.99 | 56.2 | 230,260.3 | weight_read | 7.06x | 7.06x | 15.33x | 7.06x |
| MiMo-V2.6-Flash | 4096 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x41 | 33,415 | 7.0 | 28,582.8 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 9,435.36 | 27.5 | 112,445.2 | compute | 0.25x | 0.25x | 0.79x | 0.25x |

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
| MiMo-V2.6-Flash | 15 | 12,390 | 113.9 | 300.8 | 368.8 | hybrid | 733.70 | 27.1% | layer_fixed_latency |
| MiMo-V2.6-Flash | 19 | 15,694 | 113.8 | 309.0 | 344.2 | hybrid | 736.06 | 25.3% | weight_read |
| MiMo-V2.6-Flash | 20 | 16,520 | 113.8 | 311.0 | 351.7 | hybrid | 736.06 | 25.9% | weight_read |
| MiMo-V2.6-Flash | 21 | 17,346 | 113.7 | 312.8 | 358.7 | hybrid | 736.06 | 26.4% | weight_read |
| MiMo-V2.6-Flash | 22 | 18,172 | 113.7 | 314.4 | 365.3 | hybrid | 736.06 | 26.9% | weight_read |
| MiMo-V2.6-Flash | 30 | 24,780 | 113.5 | 323.0 | 368.2 | hybrid | 738.42 | 27.2% | layer_fixed_latency |
| MiMo-V2.6-Flash | 37 | 30,562 | 113.2 | 327.5 | 366.0 | hybrid | 740.78 | 27.1% | layer_fixed_latency |
| MiMo-V2.6-Flash | 40 | 33,040 | 113.1 | 329.2 | 376.9 | hybrid | 740.78 | 27.9% | layer_fixed_latency |
| MiMo-V2.6-Flash | 41 | 33,866 | 113.1 | 329.3 | 354.3 | hybrid | 743.13 | 26.3% | weight_read |
| MiMo-V2.6-Flash | 42 | 34,692 | 113.1 | 329.7 | 357.8 | hybrid | 743.13 | 26.6% | weight_read |
| MiMo-V2.6-Flash | 44 | 36,344 | 113.0 | 330.7 | 364.4 | hybrid | 743.13 | 27.1% | weight_read |
| MiMo-V2.6-Flash | 46 | 37,996 | 112.9 | 331.5 | 370.6 | hybrid | 743.13 | 27.5% | layer_fixed_latency |
| MiMo-V2.6-Flash | 48 | 39,648 | 112.9 | 332.3 | 376.5 | hybrid | 743.13 | 28.0% | layer_fixed_latency |
| MiMo-V2.6-Flash | 51 | 42,126 | 112.9 | 333.0 | 363.1 | hybrid | 745.49 | 27.1% | weight_read |
| MiMo-V2.6-Flash | 53 | 43,778 | 112.9 | 333.7 | 368.6 | hybrid | 745.49 | 27.5% | layer_fixed_latency |
| MiMo-V2.6-Flash | 56 | 46,256 | 112.9 | 334.5 | 376.2 | hybrid | 745.49 | 28.0% | layer_fixed_latency |
| MiMo-V2.6-Flash | 58 | 47,908 | 112.9 | 334.8 | 362.1 | hybrid | 747.85 | 27.1% | weight_read |
| MiMo-V2.6-Flash | 62 | 51,212 | 112.9 | 335.8 | 371.5 | hybrid | 747.85 | 27.8% | layer_fixed_latency |
| MiMo-V2.6-Flash | 66 | 54,516 | 112.9 | 336.5 | 363.4 | hybrid | 750.21 | 27.3% | weight_read |
| MiMo-V2.6-Flash | 67 | 55,342 | 112.9 | 336.7 | 365.6 | hybrid | 750.21 | 27.4% | layer_fixed_latency |
| MiMo-V2.6-Flash | 71 | 58,646 | 112.9 | 337.4 | 373.6 | hybrid | 750.21 | 28.0% | layer_fixed_latency |
| MiMo-V2.6-Flash | 77 | 63,602 | 112.9 | 338.2 | 369.9 | hybrid | 752.56 | 27.8% | layer_fixed_latency |
| MiMo-V2.6-Flash | 107 | 88,382 | 112.9 | 341.1 | 367.6 | hybrid | 762.00 | 28.0% | layer_fixed_latency |
| MiMo-V2.6-Flash | 111 | 91,686 | 112.9 | 341.4 | 372.7 | hybrid | 762.00 | 28.4% | layer_fixed_latency |
| MiMo-V2.6-Flash | 112 | 92,512 | 112.9 | 341.4 | 373.9 | hybrid | 762.00 | 28.5% | layer_fixed_latency |
| MiMo-V2.6-Flash | 115 | 94,990 | 112.9 | 341.6 | 367.7 | hybrid | 764.35 | 28.1% | layer_fixed_latency |
| MiMo-V2.6-Flash | 142 | 117,292 | 112.9 | 342.9 | 370.7 | hybrid | 771.43 | 28.6% | layer_fixed_latency |
| MiMo-V2.6-Flash | 154 | 127,204 | 112.9 | 343.4 | 366.7 | hybrid | 776.14 | 28.5% | layer_fixed_latency |
| MiMo-V2.6-Flash | 168 | 138,768 | 112.9 | 343.8 | 371.6 | hybrid | 778.50 | 28.9% | layer_fixed_latency |
| MiMo-V2.6-Flash | 224 | 185,024 | 112.9 | 345.0 | 369.3 | hybrid | 795.00 | 29.4% | layer_fixed_latency |
| MiMo-V2.6-Flash | 335 | 276,710 | 112.9 | 287.9 | 364.5 | hybrid | 828.01 | 30.2% | layer_fixed_latency |
| MiMo-V2.6-Flash | 336 | 277,536 | 112.9 | 287.9 | 364.9 | hybrid | 828.01 | 30.2% | layer_fixed_latency |
| MiMo-V2.6-Flash | 448 | 370,048 | 112.9 | 288.4 | 363.0 | hybrid | 842.16 | 30.6% | layer_fixed_latency |
| MiMo-V2.6-Flash | 672 | 555,072 | 112.9 | 288.8 | 363.0 | hybrid | 842.16 | 30.6% | layer_fixed_latency |

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
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x43 | MiMo-V2.6-Flash | 43 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x43 | MiMo-V2.6-Flash | 43 | tensor | rom_package_ucie | rom_board_serdes | 192 | 66.91 us | 1,494.5 tok/s | 14,944.6 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 96 x all_reduce span 11 on rom_board_serdes (traversals 6.6) = 64.55 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x43 | MiMo-V2.6-Flash | 43 | hybrid | rom_package_ucie | rom_board_serdes | 106 | 3.41 us | 29,343.8 tok/s | 293,437.6 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x43 | MiMo-V2.6-Flash | 43 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | MiMo-V2.6-Flash | 1 | pipeline | on_wafer | rom_wafer_serdes | 47 | 5.88 us | 17,021.2 tok/s | 170,212.3 tok/s | 47 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.88 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-tensor-x38 | MiMo-V2.6-Flash | 38 | tensor | nvlink3 | infiniband_hdr | 192 | 952.14 us | 105.0 tok/s | 1,050.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 465.26 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | MiMo-V2.6-Flash | 1 | tensor | on_wafer | rom_wafer_serdes | 96 | 184.80 us | 541.1 tok/s | 5,411.3 tok/s | 96 x all_reduce span 57 on on_wafer (traversals 15.4) = 184.80 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hybrid-x42 | MiMo-V2.6-Flash | 42 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x68 | MiMo-V2.6-Flash | 68 | pipeline | rom_package_ucie | rom_board_serdes | 47 | 1.58 us | 63,139.7 tok/s | 631,396.8 tok/s | 36 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.43 us; 11 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.15 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x47 | MiMo-V2.6-Flash | 47 | tensor | rom_package_ucie | rom_board_serdes | 192 | 66.92 us | 1,494.2 tok/s | 14,942.4 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 96 x all_reduce span 12 on rom_board_serdes (traversals 6.6) = 64.56 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x63 | MiMo-V2.6-Flash | 63 | hybrid | rom_package_ucie | rom_board_serdes | 111 | 3.93 us | 25,441.2 tok/s | 254,411.8 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.57 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-pipeline-x67 | MiMo-V2.6-Flash | 67 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2 | MiMo-V2.6-Flash | 2 | pipeline | on_wafer | rom_wafer_serdes | 47 | 5.88 us | 17,021.2 tok/s | 170,212.3 tok/s | 47 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.88 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-tensor-x41 | MiMo-V2.6-Flash | 41 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x2 | MiMo-V2.6-Flash | 2 | tensor | on_wafer | rom_wafer_serdes | 192 | 206.12 us | 485.2 tok/s | 4,851.6 tok/s | 96 x all_reduce span 57 on on_wafer (traversals 15.4) = 184.80 us; 96 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 21.32 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hybrid-x52 | MiMo-V2.6-Flash | 52 | hybrid | nvlink3 | infiniband_hdr | 102 | 501.03 us | 199.6 tok/s | 1,995.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | MiMo-V2.6-Flash | 3 | hybrid | on_wafer | rom_wafer_serdes | 98 | 185.00 us | 540.5 tok/s | 5,405.3 tok/s | 96 x all_reduce span 57 on on_wafer (traversals 15.4) = 184.80 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.20 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x15-pipeline | MiMo-V2.6-Flash | 15 | pipeline | nvlink3 | infiniband_hdr | 14 | 35.21 us | 2,839.9 tok/s | 28,398.9 tok/s | 13 x point_to_point span 2 on nvlink3 (traversals 1.0) = 32.85 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x15-tensor | MiMo-V2.6-Flash | 15 | tensor | nvlink3 | infiniband_hdr | 192 | 923.83 us | 108.2 tok/s | 1,082.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 436.95 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x15-hybrid | MiMo-V2.6-Flash | 15 | hybrid | nvlink3 | infiniband_hdr | 97 | 489.24 us | 204.4 tok/s | 2,044.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x15-expert | MiMo-V2.6-Flash | 15 | expert | nvlink3 | infiniband_hdr | 192 | 698.54 us | 143.2 tok/s | 1,431.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 211.66 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x19-pipeline | MiMo-V2.6-Flash | 19 | pipeline | nvlink3 | infiniband_hdr | 18 | 45.15 us | 2,214.7 tok/s | 22,147.3 tok/s | 16 x point_to_point span 2 on nvlink3 (traversals 1.0) = 40.44 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x19-tensor | MiMo-V2.6-Flash | 19 | tensor | nvlink3 | infiniband_hdr | 192 | 939.56 us | 106.4 tok/s | 1,064.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 452.67 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x19-hybrid | MiMo-V2.6-Flash | 19 | hybrid | nvlink3 | infiniband_hdr | 98 | 491.60 us | 203.4 tok/s | 2,034.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x19-expert | MiMo-V2.6-Flash | 19 | expert | nvlink3 | infiniband_hdr | 192 | 691.57 us | 144.6 tok/s | 1,446.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 483.44 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 208.13 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x20-pipeline | MiMo-V2.6-Flash | 20 | pipeline | nvlink3 | infiniband_hdr | 19 | 47.68 us | 2,097.3 tok/s | 20,973.3 tok/s | 17 x point_to_point span 2 on nvlink3 (traversals 1.0) = 42.96 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x20-tensor | MiMo-V2.6-Flash | 20 | tensor | nvlink3 | infiniband_hdr | 192 | 939.56 us | 106.4 tok/s | 1,064.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 452.67 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x20-hybrid | MiMo-V2.6-Flash | 20 | hybrid | nvlink3 | infiniband_hdr | 98 | 491.60 us | 203.4 tok/s | 2,034.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x20-expert | MiMo-V2.6-Flash | 20 | expert | nvlink3 | infiniband_hdr | 192 | 690.90 us | 144.7 tok/s | 1,447.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 483.44 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 207.46 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x21-pipeline | MiMo-V2.6-Flash | 21 | pipeline | nvlink3 | infiniband_hdr | 20 | 50.21 us | 1,991.8 tok/s | 19,917.6 tok/s | 18 x point_to_point span 2 on nvlink3 (traversals 1.0) = 45.49 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x21-tensor | MiMo-V2.6-Flash | 21 | tensor | nvlink3 | infiniband_hdr | 192 | 939.56 us | 106.4 tok/s | 1,064.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 452.67 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x21-hybrid | MiMo-V2.6-Flash | 21 | hybrid | nvlink3 | infiniband_hdr | 98 | 491.60 us | 203.4 tok/s | 2,034.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x21-expert | MiMo-V2.6-Flash | 21 | expert | nvlink3 | infiniband_hdr | 192 | 690.30 us | 144.9 tok/s | 1,448.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 483.44 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 206.86 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x22-pipeline | MiMo-V2.6-Flash | 22 | pipeline | nvlink3 | infiniband_hdr | 21 | 52.73 us | 1,896.3 tok/s | 18,963.0 tok/s | 19 x point_to_point span 2 on nvlink3 (traversals 1.0) = 48.02 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x22-tensor | MiMo-V2.6-Flash | 22 | tensor | nvlink3 | infiniband_hdr | 192 | 939.56 us | 106.4 tok/s | 1,064.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 452.67 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x22-hybrid | MiMo-V2.6-Flash | 22 | hybrid | nvlink3 | infiniband_hdr | 98 | 491.60 us | 203.4 tok/s | 2,034.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x22-expert | MiMo-V2.6-Flash | 22 | expert | nvlink3 | infiniband_hdr | 192 | 689.76 us | 145.0 tok/s | 1,449.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 483.44 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 206.32 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x30-pipeline | MiMo-V2.6-Flash | 30 | pipeline | nvlink3 | infiniband_hdr | 29 | 72.78 us | 1,373.9 tok/s | 13,739.5 tok/s | 26 x point_to_point span 2 on nvlink3 (traversals 1.0) = 65.71 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x30-tensor | MiMo-V2.6-Flash | 30 | tensor | nvlink3 | infiniband_hdr | 192 | 947.42 us | 105.5 tok/s | 1,055.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 460.54 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x30-hybrid | MiMo-V2.6-Flash | 30 | hybrid | nvlink3 | infiniband_hdr | 99 | 493.95 us | 202.4 tok/s | 2,024.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x30-expert | MiMo-V2.6-Flash | 30 | expert | nvlink3 | infiniband_hdr | 192 | 685.56 us | 145.9 tok/s | 1,458.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 482.29 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 203.27 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x37-pipeline | MiMo-V2.6-Flash | 37 | pipeline | nvlink3 | infiniband_hdr | 36 | 90.30 us | 1,107.4 tok/s | 11,073.6 tok/s | 32 x point_to_point span 2 on nvlink3 (traversals 1.0) = 80.87 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x37-tensor | MiMo-V2.6-Flash | 37 | tensor | nvlink3 | infiniband_hdr | 192 | 952.14 us | 105.0 tok/s | 1,050.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 465.26 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x37-hybrid | MiMo-V2.6-Flash | 37 | hybrid | nvlink3 | infiniband_hdr | 100 | 496.31 us | 201.5 tok/s | 2,014.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x37-expert | MiMo-V2.6-Flash | 37 | expert | nvlink3 | infiniband_hdr | 192 | 683.40 us | 146.3 tok/s | 1,463.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.72 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 201.68 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x40-pipeline | MiMo-V2.6-Flash | 40 | pipeline | nvlink3 | infiniband_hdr | 39 | 97.89 us | 1,021.6 tok/s | 10,215.9 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.46 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x40-tensor | MiMo-V2.6-Flash | 40 | tensor | nvlink3 | infiniband_hdr | 192 | 952.14 us | 105.0 tok/s | 1,050.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 465.26 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x40-hybrid | MiMo-V2.6-Flash | 40 | hybrid | nvlink3 | infiniband_hdr | 100 | 496.31 us | 201.5 tok/s | 2,014.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x40-expert | MiMo-V2.6-Flash | 40 | expert | nvlink3 | infiniband_hdr | 192 | 682.55 us | 146.5 tok/s | 1,465.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.38 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 201.17 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x41-pipeline | MiMo-V2.6-Flash | 41 | pipeline | nvlink3 | infiniband_hdr | 40 | 100.24 us | 997.6 tok/s | 9,975.6 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.46 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x41-tensor | MiMo-V2.6-Flash | 41 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x41-hybrid | MiMo-V2.6-Flash | 41 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x41-expert | MiMo-V2.6-Flash | 41 | expert | nvlink3 | infiniband_hdr | 192 | 682.39 us | 146.5 tok/s | 1,465.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.38 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 201.02 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x42-pipeline | MiMo-V2.6-Flash | 42 | pipeline | nvlink3 | infiniband_hdr | 41 | 102.77 us | 973.0 tok/s | 9,730.3 tok/s | 36 x point_to_point span 2 on nvlink3 (traversals 1.0) = 90.98 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x42-tensor | MiMo-V2.6-Flash | 42 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x42-hybrid | MiMo-V2.6-Flash | 42 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x42-expert | MiMo-V2.6-Flash | 42 | expert | nvlink3 | infiniband_hdr | 192 | 682.25 us | 146.6 tok/s | 1,465.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.38 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 200.87 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x44-pipeline | MiMo-V2.6-Flash | 44 | pipeline | nvlink3 | infiniband_hdr | 43 | 107.83 us | 927.4 tok/s | 9,274.2 tok/s | 38 x point_to_point span 2 on nvlink3 (traversals 1.0) = 96.04 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x44-tensor | MiMo-V2.6-Flash | 44 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x44-hybrid | MiMo-V2.6-Flash | 44 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x44-expert | MiMo-V2.6-Flash | 44 | expert | nvlink3 | infiniband_hdr | 192 | 681.98 us | 146.6 tok/s | 1,466.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.38 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 200.60 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x46-pipeline | MiMo-V2.6-Flash | 46 | pipeline | nvlink3 | infiniband_hdr | 45 | 112.88 us | 885.9 tok/s | 8,858.9 tok/s | 40 x point_to_point span 2 on nvlink3 (traversals 1.0) = 101.09 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x46-tensor | MiMo-V2.6-Flash | 46 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x46-hybrid | MiMo-V2.6-Flash | 46 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x46-expert | MiMo-V2.6-Flash | 46 | expert | nvlink3 | infiniband_hdr | 192 | 681.73 us | 146.7 tok/s | 1,466.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.38 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 200.35 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x48-pipeline | MiMo-V2.6-Flash | 48 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x48-tensor | MiMo-V2.6-Flash | 48 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x48-hybrid | MiMo-V2.6-Flash | 48 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x48-expert | MiMo-V2.6-Flash | 48 | expert | nvlink3 | infiniband_hdr | 192 | 681.27 us | 146.8 tok/s | 1,467.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.15 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 200.12 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x51-pipeline | MiMo-V2.6-Flash | 51 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x51-tensor | MiMo-V2.6-Flash | 51 | tensor | nvlink3 | infiniband_hdr | 192 | 957.53 us | 104.4 tok/s | 1,044.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 470.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x51-hybrid | MiMo-V2.6-Flash | 51 | hybrid | nvlink3 | infiniband_hdr | 102 | 501.03 us | 199.6 tok/s | 1,995.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x51-expert | MiMo-V2.6-Flash | 51 | expert | nvlink3 | infiniband_hdr | 192 | 680.96 us | 146.9 tok/s | 1,468.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.15 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 199.81 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x53-pipeline | MiMo-V2.6-Flash | 53 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x53-tensor | MiMo-V2.6-Flash | 53 | tensor | nvlink3 | infiniband_hdr | 192 | 957.53 us | 104.4 tok/s | 1,044.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 470.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x53-hybrid | MiMo-V2.6-Flash | 53 | hybrid | nvlink3 | infiniband_hdr | 102 | 501.03 us | 199.6 tok/s | 1,995.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x53-expert | MiMo-V2.6-Flash | 53 | expert | nvlink3 | infiniband_hdr | 192 | 680.78 us | 146.9 tok/s | 1,468.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.15 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 199.63 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x56-pipeline | MiMo-V2.6-Flash | 56 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x56-tensor | MiMo-V2.6-Flash | 56 | tensor | nvlink3 | infiniband_hdr | 192 | 957.53 us | 104.4 tok/s | 1,044.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 470.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x56-hybrid | MiMo-V2.6-Flash | 56 | hybrid | nvlink3 | infiniband_hdr | 102 | 501.03 us | 199.6 tok/s | 1,995.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x56-expert | MiMo-V2.6-Flash | 56 | expert | nvlink3 | infiniband_hdr | 192 | 680.36 us | 147.0 tok/s | 1,469.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.98 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 199.37 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x58-pipeline | MiMo-V2.6-Flash | 58 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x58-tensor | MiMo-V2.6-Flash | 58 | tensor | nvlink3 | infiniband_hdr | 192 | 959.22 us | 104.3 tok/s | 1,042.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 472.34 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x58-hybrid | MiMo-V2.6-Flash | 58 | hybrid | nvlink3 | infiniband_hdr | 103 | 503.39 us | 198.7 tok/s | 1,986.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x58-expert | MiMo-V2.6-Flash | 58 | expert | nvlink3 | infiniband_hdr | 192 | 680.20 us | 147.0 tok/s | 1,470.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.98 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 199.22 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x62-pipeline | MiMo-V2.6-Flash | 62 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x62-tensor | MiMo-V2.6-Flash | 62 | tensor | nvlink3 | infiniband_hdr | 192 | 959.22 us | 104.3 tok/s | 1,042.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 472.34 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x62-hybrid | MiMo-V2.6-Flash | 62 | hybrid | nvlink3 | infiniband_hdr | 103 | 503.39 us | 198.7 tok/s | 1,986.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x62-expert | MiMo-V2.6-Flash | 62 | expert | nvlink3 | infiniband_hdr | 192 | 679.92 us | 147.1 tok/s | 1,470.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.98 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.94 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x66-pipeline | MiMo-V2.6-Flash | 66 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x66-tensor | MiMo-V2.6-Flash | 66 | tensor | nvlink3 | infiniband_hdr | 192 | 960.53 us | 104.1 tok/s | 1,041.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 473.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x66-hybrid | MiMo-V2.6-Flash | 66 | hybrid | nvlink3 | infiniband_hdr | 104 | 505.74 us | 197.7 tok/s | 1,977.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x66-expert | MiMo-V2.6-Flash | 66 | expert | nvlink3 | infiniband_hdr | 192 | 679.55 us | 147.2 tok/s | 1,471.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.86 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.69 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x67-pipeline | MiMo-V2.6-Flash | 67 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x67-tensor | MiMo-V2.6-Flash | 67 | tensor | nvlink3 | infiniband_hdr | 192 | 960.53 us | 104.1 tok/s | 1,041.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 473.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x67-hybrid | MiMo-V2.6-Flash | 67 | hybrid | nvlink3 | infiniband_hdr | 104 | 505.74 us | 197.7 tok/s | 1,977.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x67-expert | MiMo-V2.6-Flash | 67 | expert | nvlink3 | infiniband_hdr | 192 | 679.50 us | 147.2 tok/s | 1,471.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.86 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.64 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x71-pipeline | MiMo-V2.6-Flash | 71 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x71-tensor | MiMo-V2.6-Flash | 71 | tensor | nvlink3 | infiniband_hdr | 192 | 960.53 us | 104.1 tok/s | 1,041.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 473.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x71-hybrid | MiMo-V2.6-Flash | 71 | hybrid | nvlink3 | infiniband_hdr | 104 | 505.74 us | 197.7 tok/s | 1,977.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x71-expert | MiMo-V2.6-Flash | 71 | expert | nvlink3 | infiniband_hdr | 192 | 679.28 us | 147.2 tok/s | 1,472.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.86 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.42 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x77-pipeline | MiMo-V2.6-Flash | 77 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x77-tensor | MiMo-V2.6-Flash | 77 | tensor | nvlink3 | infiniband_hdr | 192 | 961.58 us | 104.0 tok/s | 1,040.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 474.69 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x77-hybrid | MiMo-V2.6-Flash | 77 | hybrid | nvlink3 | infiniband_hdr | 105 | 508.10 us | 196.8 tok/s | 1,968.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x77-expert | MiMo-V2.6-Flash | 77 | expert | nvlink3 | infiniband_hdr | 192 | 678.91 us | 147.3 tok/s | 1,472.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.76 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x107-pipeline | MiMo-V2.6-Flash | 107 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x107-tensor | MiMo-V2.6-Flash | 107 | tensor | nvlink3 | infiniband_hdr | 192 | 964.27 us | 103.7 tok/s | 1,037.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 477.39 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x107-hybrid | MiMo-V2.6-Flash | 107 | hybrid | nvlink3 | infiniband_hdr | 109 | 517.53 us | 193.2 tok/s | 1,932.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x107-expert | MiMo-V2.6-Flash | 107 | expert | nvlink3 | infiniband_hdr | 192 | 677.76 us | 147.5 tok/s | 1,475.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.53 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.23 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x111-pipeline | MiMo-V2.6-Flash | 111 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x111-tensor | MiMo-V2.6-Flash | 111 | tensor | nvlink3 | infiniband_hdr | 192 | 964.27 us | 103.7 tok/s | 1,037.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 477.39 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x111-hybrid | MiMo-V2.6-Flash | 111 | hybrid | nvlink3 | infiniband_hdr | 109 | 517.53 us | 193.2 tok/s | 1,932.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x111-expert | MiMo-V2.6-Flash | 111 | expert | nvlink3 | infiniband_hdr | 192 | 677.68 us | 147.6 tok/s | 1,475.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.53 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x112-pipeline | MiMo-V2.6-Flash | 112 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x112-tensor | MiMo-V2.6-Flash | 112 | tensor | nvlink3 | infiniband_hdr | 192 | 964.27 us | 103.7 tok/s | 1,037.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 477.39 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x112-hybrid | MiMo-V2.6-Flash | 112 | hybrid | nvlink3 | infiniband_hdr | 109 | 517.53 us | 193.2 tok/s | 1,932.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x112-expert | MiMo-V2.6-Flash | 112 | expert | nvlink3 | infiniband_hdr | 192 | 677.62 us | 147.6 tok/s | 1,475.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.49 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.13 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x115-pipeline | MiMo-V2.6-Flash | 115 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x115-tensor | MiMo-V2.6-Flash | 115 | tensor | nvlink3 | infiniband_hdr | 192 | 964.72 us | 103.7 tok/s | 1,036.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 477.84 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x115-hybrid | MiMo-V2.6-Flash | 115 | hybrid | nvlink3 | infiniband_hdr | 110 | 519.89 us | 192.3 tok/s | 1,923.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.01 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x115-expert | MiMo-V2.6-Flash | 115 | expert | nvlink3 | infiniband_hdr | 192 | 677.56 us | 147.6 tok/s | 1,475.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.49 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.07 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x142-pipeline | MiMo-V2.6-Flash | 142 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x142-tensor | MiMo-V2.6-Flash | 142 | tensor | nvlink3 | infiniband_hdr | 192 | 965.77 us | 103.5 tok/s | 1,035.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 478.89 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x142-hybrid | MiMo-V2.6-Flash | 142 | hybrid | nvlink3 | infiniband_hdr | 113 | 526.96 us | 189.8 tok/s | 1,897.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x142-expert | MiMo-V2.6-Flash | 142 | expert | nvlink3 | infiniband_hdr | 192 | 677.06 us | 147.7 tok/s | 1,477.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.40 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x154-pipeline | MiMo-V2.6-Flash | 154 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x154-tensor | MiMo-V2.6-Flash | 154 | tensor | nvlink3 | infiniband_hdr | 192 | 966.29 us | 103.5 tok/s | 1,034.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 479.41 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x154-hybrid | MiMo-V2.6-Flash | 154 | hybrid | nvlink3 | infiniband_hdr | 115 | 531.68 us | 188.1 tok/s | 1,880.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 44.80 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x154-expert | MiMo-V2.6-Flash | 154 | expert | nvlink3 | infiniband_hdr | 192 | 676.88 us | 147.7 tok/s | 1,477.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.36 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.51 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x168-pipeline | MiMo-V2.6-Flash | 168 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x168-tensor | MiMo-V2.6-Flash | 168 | tensor | nvlink3 | infiniband_hdr | 192 | 966.52 us | 103.5 tok/s | 1,034.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 479.64 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x168-hybrid | MiMo-V2.6-Flash | 168 | hybrid | nvlink3 | infiniband_hdr | 116 | 534.03 us | 187.3 tok/s | 1,872.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x168-expert | MiMo-V2.6-Flash | 168 | expert | nvlink3 | infiniband_hdr | 192 | 676.71 us | 147.8 tok/s | 1,477.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.33 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.38 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x224-pipeline | MiMo-V2.6-Flash | 224 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x224-tensor | MiMo-V2.6-Flash | 224 | tensor | nvlink3 | infiniband_hdr | 192 | 967.64 us | 103.3 tok/s | 1,033.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 480.76 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x224-hybrid | MiMo-V2.6-Flash | 224 | hybrid | nvlink3 | infiniband_hdr | 123 | 550.54 us | 181.6 tok/s | 1,816.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.66 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x224-expert | MiMo-V2.6-Flash | 224 | expert | nvlink3 | infiniband_hdr | 192 | 676.25 us | 147.9 tok/s | 1,478.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.25 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.00 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x335-pipeline | MiMo-V2.6-Flash | 335 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x335-tensor | MiMo-V2.6-Flash | 335 | tensor | nvlink3 | infiniband_hdr | 192 | 1,358.53 us | 73.6 tok/s | 736.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 871.64 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x335-hybrid | MiMo-V2.6-Flash | 335 | hybrid | nvlink3 | infiniband_hdr | 137 | 583.55 us | 171.4 tok/s | 1,713.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x335-expert | MiMo-V2.6-Flash | 335 | expert | nvlink3 | infiniband_hdr | 192 | 675.80 us | 148.0 tok/s | 1,479.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.17 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.63 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x336-pipeline | MiMo-V2.6-Flash | 336 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x336-tensor | MiMo-V2.6-Flash | 336 | tensor | nvlink3 | infiniband_hdr | 192 | 1,358.53 us | 73.6 tok/s | 736.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 871.64 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x336-hybrid | MiMo-V2.6-Flash | 336 | hybrid | nvlink3 | infiniband_hdr | 137 | 583.55 us | 171.4 tok/s | 1,713.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x336-expert | MiMo-V2.6-Flash | 336 | expert | nvlink3 | infiniband_hdr | 192 | 675.79 us | 148.0 tok/s | 1,479.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.16 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.63 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x448-pipeline | MiMo-V2.6-Flash | 448 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x448-tensor | MiMo-V2.6-Flash | 448 | tensor | nvlink3 | infiniband_hdr | 192 | 1,359.09 us | 73.6 tok/s | 735.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 872.21 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x448-hybrid | MiMo-V2.6-Flash | 448 | hybrid | nvlink3 | infiniband_hdr | 143 | 597.69 us | 167.3 tok/s | 1,673.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 110.81 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x448-expert | MiMo-V2.6-Flash | 448 | expert | nvlink3 | infiniband_hdr | 192 | 675.56 us | 148.0 tok/s | 1,480.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.12 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.44 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x672-pipeline | MiMo-V2.6-Flash | 672 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x672-tensor | MiMo-V2.6-Flash | 672 | tensor | nvlink3 | infiniband_hdr | 192 | 1,359.65 us | 73.5 tok/s | 735.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 872.77 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x672-hybrid | MiMo-V2.6-Flash | 672 | hybrid | nvlink3 | infiniband_hdr | 143 | 597.69 us | 167.3 tok/s | 1,673.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 110.81 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x672-expert | MiMo-V2.6-Flash | 672 | expert | nvlink3 | infiniband_hdr | 192 | 675.34 us | 148.1 tok/s | 1,480.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.08 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.25 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Flash | 1 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x63 | 51,345 | 6,764.9 | 0.132 | 6,764.9 (51,345) | 5,526.8 (46,225) | 0.82x | layer_fixed_latency |
| MiMo-V2.6-Flash | 2 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x63 | 51,345 | 6,764.9 | 0.132 | 6,764.9 (51,345) | 5,620.3 (92,450) | 0.83x | layer_fixed_latency |
| MiMo-V2.6-Flash | 4 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x63 | 51,345 | 6,764.9 | 0.132 | 6,764.9 (51,345) | 5,620.3 (92,450) | 0.83x | layer_fixed_latency |
| MiMo-V2.6-Flash | 8 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x63 | 51,345 | 6,764.9 | 0.132 | 6,764.9 (51,345) | 5,525.5 (138,675) | 0.82x | layer_fixed_latency |
| MiMo-V2.6-Flash | 16 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 6,521.4 | 0.118 | 6,521.4 (55,420) | 5,409.9 (277,350) | 0.83x | layer_fixed_latency |
| MiMo-V2.6-Flash | 32 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill | 127,140 | 6,381.1 | 0.050 | 6,381.1 (127,140) | 5,370.5 (554,700) | 0.84x | layer_fixed_latency |
| MiMo-V2.6-Flash | 64 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill | 185,005 | 6,026.1 | 0.033 | 6,026.1 (185,005) | 4,465.8 (554,700) | 0.74x | layer_fixed_latency |
| MiMo-V2.6-Flash | 256 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 3,960.9 | 0.014 | 3,960.9 (277,100) | 2,332.7 (554,700) | 0.59x | compute |
| MiMo-V2.6-Flash | 1024 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 1,434.4 | 0.005 | 1,434.4 (277,100) | 723.5 (554,700) | 0.50x | compute |
| MiMo-V2.6-Flash | 4096 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 396.7 | 0.001 | 396.7 (277,100) | 190.0 (554,700) | 0.48x | compute |

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
| MiMo-V2.6-Flash | 256 | 628.4 MB | 137.8 mm2 | 24.81 mm2 (18.0%) | 35,280 mm2 | 6,350 mm2 | 37,926 mm2 = 46.5 reticles |

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
| MiMo-V2.6-Flash | 1 | sram | 340,496.7 | 27,662.6 | 27,662.6 | 12.31x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 2 | sram | 340,496.7 | 27,662.6 | 27,662.6 | 12.31x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 4 | sram | 340,496.7 | 27,662.6 | 27,662.6 | 12.31x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 8 | sram | 340,496.7 | 27,662.6 | 27,662.6 | 12.31x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 16 | sram | 340,496.7 | 27,662.6 | 42,410.5 | 12.31x | 1.53x | weight_read | weight_read | layer_fixed_latency |
| MiMo-V2.6-Flash | 32 | sram | 340,496.7 | 27,662.6 | 61,569.1 | 12.31x | 2.23x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 64 | sram | 340,496.7 | 27,803.1 | 91,012.2 | 12.25x | 3.27x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 256 | sram | 553,446.7 | 28,696.0 | 122,320.7 | 19.29x | 4.26x | weight_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 1024 | sram | 907,055.2 | 26,050.6 | 130,608.6 | 34.82x | 5.01x | weight_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 4096 | sram | 1,482,889.3 | 26,094.7 | 131,946.5 | 56.83x | 5.06x | layer_fixed_latency | weight_read | kv_read |
| MiMo-V2.6-Flash | 1 | rom | 1,111,290.9 | 119,986.6 | 119,986.6 | 9.26x | 1.00x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 2 | rom | 1,111,290.9 | 119,986.6 | 119,986.6 | 9.26x | 1.00x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 4 | rom | 1,111,290.9 | 119,986.6 | 119,986.6 | 9.26x | 1.00x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 8 | rom | 1,111,290.9 | 119,986.6 | 119,986.6 | 9.26x | 1.00x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 16 | rom | 1,111,290.9 | 119,986.6 | 119,986.6 | 9.26x | 1.00x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 32 | rom | 1,111,290.9 | 119,986.6 | 119,986.6 | 9.26x | 1.00x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 64 | rom | 1,111,290.9 | 119,986.6 | 119,986.6 | 9.26x | 1.00x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 256 | rom | 1,111,290.9 | 126,499.8 | 158,079.1 | 8.78x | 1.25x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 1024 | rom | 1,468,799.1 | 130,825.8 | 185,615.9 | 11.23x | 1.42x | compute | kv_read | kv_read |
| MiMo-V2.6-Flash | 4096 | rom | 1,625,077.6 | 131,946.5 | 187,699.3 | 12.32x | 1.42x | compute | kv_read | kv_read |

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
| MiMo-V2.6-Flash | 1 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 1 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,111,290.9 | 4.010 | weight_read | 3.26x |
| MiMo-V2.6-Flash | 1 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,662.6 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 1 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 1 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,662.6 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 1 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 2 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 2 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,111,290.9 | 4.010 | weight_read | 3.26x |
| MiMo-V2.6-Flash | 2 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,662.6 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 2 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 2 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,662.6 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 2 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 4 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 4 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,111,290.9 | 4.010 | weight_read | 3.26x |
| MiMo-V2.6-Flash | 4 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,662.6 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 4 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 4 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,662.6 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 4 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 8 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 8 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,111,290.9 | 4.010 | weight_read | 3.26x |
| MiMo-V2.6-Flash | 8 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,662.6 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 8 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 8 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,662.6 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 8 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 16 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 16 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,111,290.9 | 4.010 | weight_read | 3.26x |
| MiMo-V2.6-Flash | 16 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,662.6 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 16 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 16 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.34 | 42,410.5 | 0.459 | layer_fixed_latency | 0.12x |
| MiMo-V2.6-Flash | 16 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 32 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 32 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,111,290.9 | 4.010 | weight_read | 3.26x |
| MiMo-V2.6-Flash | 32 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,662.6 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 32 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 32 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.34 | 61,569.1 | 0.666 | weight_read | 0.18x |
| MiMo-V2.6-Flash | 32 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 64 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 64 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,111,290.9 | 4.010 | weight_read | 3.26x |
| MiMo-V2.6-Flash | 64 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 27,803.1 | 0.601 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 64 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 64 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 3.27 | 91,012.2 | 0.984 | weight_read | 0.27x |
| MiMo-V2.6-Flash | 64 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.15 | 1.00 | 119,986.6 | 1.298 | kv_read | 0.35x |
| MiMo-V2.6-Flash | 256 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x156 | 127,140 | 1.00 | 1.00 | 553,446.7 | 4.353 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 256 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,111,290.9 | 4.010 | weight_read | 2.01x |
| MiMo-V2.6-Flash | 256 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,696.0 | 0.621 | weight_read | 0.05x |
| MiMo-V2.6-Flash | 256 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 2.25 | 126,499.8 | 1.368 | kv_read | 0.23x |
| MiMo-V2.6-Flash | 256 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 3.36 | 122,320.7 | 1.323 | kv_read | 0.22x |
| MiMo-V2.6-Flash | 256 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x30-perregion-romfill | 24,450 | 1.49 | 4.64 | 158,079.1 | 6.465 | kv_read | 0.29x |
| MiMo-V2.6-Flash | 1024 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x170 | 138,550 | 1.00 | 1.00 | 907,055.2 | 6.547 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 1024 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,468,799.1 | 5.301 | compute | 1.62x |
| MiMo-V2.6-Flash | 1024 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 8.98 | 26,050.6 | 0.282 | weight_read | 0.03x |
| MiMo-V2.6-Flash | 1024 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 8.98 | 130,825.8 | 1.415 | kv_read | 0.14x |
| MiMo-V2.6-Flash | 1024 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x21-perregion | 17,115 | 1.00 | 5.85 | 130,608.6 | 7.631 | kv_read | 0.14x |
| MiMo-V2.6-Flash | 1024 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x30-perregion-romfill | 24,450 | 1.49 | 4.80 | 185,615.9 | 7.592 | kv_read | 0.20x |
| MiMo-V2.6-Flash | 4096 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 1,482,889.3 | 5.351 | layer_fixed_latency | 1.00x |
| MiMo-V2.6-Flash | 4096 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,625,077.6 | 5.865 | compute | 1.10x |
| MiMo-V2.6-Flash | 4096 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 35.93 | 26,094.7 | 0.282 | weight_read | 0.02x |
| MiMo-V2.6-Flash | 4096 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 35.93 | 131,946.5 | 1.427 | kv_read | 0.09x |
| MiMo-V2.6-Flash | 4096 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 4.94 | 131,946.5 | 1.427 | kv_read | 0.09x |
| MiMo-V2.6-Flash | 4096 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x30-perregion-romfill | 24,450 | 1.49 | 10.98 | 187,699.3 | 7.677 | kv_read | 0.13x |

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
| MiMo-V2.6-Flash | 1 | 19 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 2 | 19 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 4 | 19 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 64 | 57 | 1.12 | 1.002 | 1.027 | 1.02x |
| MiMo-V2.6-Flash | 256 | 57 | 4.49 | 1.056 | 1.885 | 1.78x |
| MiMo-V2.6-Flash | 1024 | 21 | 48.76 | 1.935 | 5.848 | 3.02x |
| MiMo-V2.6-Flash | 4096 | 21 | 195.05 | 6.108 | 13.947 | 2.28x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Flash | 1 | 15 | 6.36 | 4.06 | 1.57x |
| MiMo-V2.6-Flash | 2 | 15 | 9.94 | 5.24 | 1.90x |
| MiMo-V2.6-Flash | 4 | 15 | 13.17 | 6.51 | 2.02x |
| MiMo-V2.6-Flash | 8 | 15 | 14.71 | 7.78 | 1.89x |
| MiMo-V2.6-Flash | 16 | 15 | 14.99 | 8.90 | 1.68x |
| MiMo-V2.6-Flash | 32 | 15 | 15.00 | 9.77 | 1.54x |
| MiMo-V2.6-Flash | 64 | 15 | 15.00 | 10.30 | 1.46x |
| MiMo-V2.6-Flash | 256 | 15 | 15.00 | 10.54 | 1.42x |
| MiMo-V2.6-Flash | 1024 | 15 | 15.00 | 10.54 | 1.42x |
| MiMo-V2.6-Flash | 4096 | 15 | 15.00 | 10.54 | 1.42x |
| MiMo-V2.6-Flash | 1 | 19 | 6.67 | 4.36 | 1.53x |
| MiMo-V2.6-Flash | 2 | 19 | 10.89 | 5.74 | 1.90x |
| MiMo-V2.6-Flash | 4 | 19 | 15.35 | 7.29 | 2.11x |
| MiMo-V2.6-Flash | 8 | 19 | 18.15 | 8.87 | 2.05x |
| MiMo-V2.6-Flash | 16 | 19 | 18.92 | 10.33 | 1.83x |
| MiMo-V2.6-Flash | 32 | 19 | 19.00 | 11.49 | 1.65x |
| MiMo-V2.6-Flash | 64 | 19 | 19.00 | 12.22 | 1.56x |
| MiMo-V2.6-Flash | 256 | 19 | 19.00 | 12.53 | 1.52x |
| MiMo-V2.6-Flash | 1024 | 19 | 19.00 | 12.53 | 1.52x |
| MiMo-V2.6-Flash | 4096 | 19 | 19.00 | 12.53 | 1.52x |
| MiMo-V2.6-Flash | 1 | 20 | 6.73 | 4.42 | 1.52x |
| MiMo-V2.6-Flash | 2 | 20 | 11.08 | 5.85 | 1.90x |
| MiMo-V2.6-Flash | 4 | 20 | 15.82 | 7.46 | 2.12x |
| MiMo-V2.6-Flash | 8 | 20 | 18.95 | 9.12 | 2.08x |
| MiMo-V2.6-Flash | 16 | 20 | 19.89 | 10.66 | 1.87x |
| MiMo-V2.6-Flash | 32 | 20 | 20.00 | 11.89 | 1.68x |
| MiMo-V2.6-Flash | 64 | 20 | 20.00 | 12.66 | 1.58x |
| MiMo-V2.6-Flash | 256 | 20 | 20.00 | 13.00 | 1.54x |
| MiMo-V2.6-Flash | 1024 | 20 | 20.00 | 13.00 | 1.54x |
| MiMo-V2.6-Flash | 4096 | 20 | 20.00 | 13.00 | 1.54x |
| MiMo-V2.6-Flash | 1 | 21 | 6.79 | 4.48 | 1.51x |
| MiMo-V2.6-Flash | 2 | 21 | 11.26 | 5.95 | 1.89x |
| MiMo-V2.6-Flash | 4 | 21 | 16.27 | 7.62 | 2.13x |
| MiMo-V2.6-Flash | 8 | 21 | 19.72 | 9.36 | 2.11x |
| MiMo-V2.6-Flash | 16 | 21 | 20.85 | 10.98 | 1.90x |
| MiMo-V2.6-Flash | 32 | 21 | 20.99 | 12.28 | 1.71x |
| MiMo-V2.6-Flash | 64 | 21 | 21.00 | 13.10 | 1.60x |
| MiMo-V2.6-Flash | 256 | 21 | 21.00 | 13.46 | 1.56x |
| MiMo-V2.6-Flash | 1024 | 21 | 21.00 | 13.46 | 1.56x |
| MiMo-V2.6-Flash | 4096 | 21 | 21.00 | 13.46 | 1.56x |
| MiMo-V2.6-Flash | 1 | 22 | 6.84 | 4.54 | 1.51x |
| MiMo-V2.6-Flash | 2 | 22 | 11.43 | 6.05 | 1.89x |
| MiMo-V2.6-Flash | 4 | 22 | 16.68 | 7.78 | 2.14x |
| MiMo-V2.6-Flash | 8 | 22 | 20.48 | 9.60 | 2.13x |
| MiMo-V2.6-Flash | 16 | 22 | 21.81 | 11.29 | 1.93x |
| MiMo-V2.6-Flash | 32 | 22 | 21.99 | 12.66 | 1.74x |
| MiMo-V2.6-Flash | 64 | 22 | 22.00 | 13.53 | 1.63x |
| MiMo-V2.6-Flash | 256 | 22 | 22.00 | 13.91 | 1.58x |
| MiMo-V2.6-Flash | 1024 | 22 | 22.00 | 13.91 | 1.58x |
| MiMo-V2.6-Flash | 4096 | 22 | 22.00 | 13.91 | 1.58x |
| MiMo-V2.6-Flash | 1 | 30 | 7.13 | 4.94 | 1.44x |
| MiMo-V2.6-Flash | 2 | 30 | 12.41 | 6.70 | 1.85x |
| MiMo-V2.6-Flash | 4 | 30 | 19.34 | 8.86 | 2.18x |
| MiMo-V2.6-Flash | 8 | 30 | 25.72 | 11.22 | 2.29x |
| MiMo-V2.6-Flash | 16 | 30 | 29.05 | 13.51 | 2.15x |
| MiMo-V2.6-Flash | 32 | 30 | 29.88 | 15.42 | 1.94x |
| MiMo-V2.6-Flash | 64 | 30 | 29.98 | 16.66 | 1.80x |
| MiMo-V2.6-Flash | 256 | 30 | 29.99 | 17.21 | 1.74x |
| MiMo-V2.6-Flash | 1024 | 30 | 29.99 | 17.21 | 1.74x |
| MiMo-V2.6-Flash | 4096 | 30 | 29.99 | 17.21 | 1.74x |
| MiMo-V2.6-Flash | 1 | 37 | 7.28 | 5.22 | 1.40x |
| MiMo-V2.6-Flash | 2 | 37 | 12.97 | 7.13 | 1.82x |
| MiMo-V2.6-Flash | 4 | 37 | 20.97 | 9.62 | 2.18x |
| MiMo-V2.6-Flash | 8 | 37 | 29.33 | 12.38 | 2.37x |
| MiMo-V2.6-Flash | 16 | 37 | 34.74 | 15.13 | 2.30x |
| MiMo-V2.6-Flash | 32 | 37 | 36.58 | 17.49 | 2.09x |
| MiMo-V2.6-Flash | 64 | 37 | 36.92 | 19.04 | 1.94x |
| MiMo-V2.6-Flash | 256 | 37 | 36.97 | 19.74 | 1.87x |
| MiMo-V2.6-Flash | 1024 | 37 | 36.97 | 19.74 | 1.87x |
| MiMo-V2.6-Flash | 4096 | 37 | 36.97 | 19.74 | 1.87x |
| MiMo-V2.6-Flash | 1 | 40 | 7.33 | 5.32 | 1.38x |
| MiMo-V2.6-Flash | 2 | 40 | 13.15 | 7.29 | 1.80x |
| MiMo-V2.6-Flash | 4 | 40 | 21.53 | 9.90 | 2.17x |
| MiMo-V2.6-Flash | 8 | 40 | 30.65 | 12.82 | 2.39x |
| MiMo-V2.6-Flash | 16 | 40 | 36.97 | 15.76 | 2.35x |
| MiMo-V2.6-Flash | 32 | 40 | 39.36 | 18.30 | 2.15x |
| MiMo-V2.6-Flash | 64 | 40 | 39.86 | 19.98 | 1.99x |
| MiMo-V2.6-Flash | 256 | 40 | 39.94 | 20.74 | 1.93x |
| MiMo-V2.6-Flash | 1024 | 40 | 39.94 | 20.74 | 1.93x |
| MiMo-V2.6-Flash | 4096 | 40 | 39.94 | 20.74 | 1.93x |
| MiMo-V2.6-Flash | 1 | 41 | 7.35 | 5.35 | 1.37x |
| MiMo-V2.6-Flash | 2 | 41 | 13.21 | 7.34 | 1.80x |
| MiMo-V2.6-Flash | 4 | 41 | 21.71 | 9.99 | 2.17x |
| MiMo-V2.6-Flash | 8 | 41 | 31.07 | 12.96 | 2.40x |
| MiMo-V2.6-Flash | 16 | 41 | 37.69 | 15.97 | 2.36x |
| MiMo-V2.6-Flash | 32 | 41 | 40.27 | 18.56 | 2.17x |
| MiMo-V2.6-Flash | 64 | 41 | 40.83 | 20.29 | 2.01x |
| MiMo-V2.6-Flash | 256 | 41 | 40.93 | 21.06 | 1.94x |
| MiMo-V2.6-Flash | 1024 | 41 | 40.93 | 21.07 | 1.94x |
| MiMo-V2.6-Flash | 4096 | 41 | 40.93 | 21.07 | 1.94x |
| MiMo-V2.6-Flash | 1 | 42 | 7.36 | 5.38 | 1.37x |
| MiMo-V2.6-Flash | 2 | 42 | 13.26 | 7.39 | 1.80x |
| MiMo-V2.6-Flash | 4 | 42 | 21.88 | 10.08 | 2.17x |
| MiMo-V2.6-Flash | 8 | 42 | 31.47 | 13.10 | 2.40x |
| MiMo-V2.6-Flash | 16 | 42 | 38.40 | 16.17 | 2.38x |
| MiMo-V2.6-Flash | 32 | 42 | 41.18 | 18.82 | 2.19x |
| MiMo-V2.6-Flash | 64 | 42 | 41.80 | 20.59 | 2.03x |
| MiMo-V2.6-Flash | 256 | 42 | 41.91 | 21.38 | 1.96x |
| MiMo-V2.6-Flash | 1024 | 42 | 41.91 | 21.39 | 1.96x |
| MiMo-V2.6-Flash | 4096 | 42 | 41.91 | 21.39 | 1.96x |
| MiMo-V2.6-Flash | 1 | 44 | 7.39 | 5.44 | 1.36x |
| MiMo-V2.6-Flash | 2 | 44 | 13.37 | 7.48 | 1.79x |
| MiMo-V2.6-Flash | 4 | 44 | 22.19 | 10.26 | 2.16x |
| MiMo-V2.6-Flash | 8 | 44 | 32.25 | 13.37 | 2.41x |
| MiMo-V2.6-Flash | 16 | 44 | 39.78 | 16.55 | 2.40x |
| MiMo-V2.6-Flash | 32 | 44 | 42.97 | 19.32 | 2.22x |
| MiMo-V2.6-Flash | 64 | 44 | 43.74 | 21.17 | 2.07x |
| MiMo-V2.6-Flash | 256 | 44 | 43.88 | 22.01 | 1.99x |
| MiMo-V2.6-Flash | 1024 | 44 | 43.88 | 22.01 | 1.99x |
| MiMo-V2.6-Flash | 4096 | 44 | 43.88 | 22.01 | 1.99x |
| MiMo-V2.6-Flash | 1 | 46 | 7.42 | 5.50 | 1.35x |
| MiMo-V2.6-Flash | 2 | 46 | 13.46 | 7.57 | 1.78x |
| MiMo-V2.6-Flash | 4 | 46 | 22.49 | 10.42 | 2.16x |
| MiMo-V2.6-Flash | 8 | 46 | 32.98 | 13.63 | 2.42x |
| MiMo-V2.6-Flash | 16 | 46 | 41.11 | 16.93 | 2.43x |
| MiMo-V2.6-Flash | 32 | 46 | 44.73 | 19.81 | 2.26x |
| MiMo-V2.6-Flash | 64 | 46 | 45.65 | 21.74 | 2.10x |
| MiMo-V2.6-Flash | 256 | 46 | 45.83 | 22.62 | 2.03x |
| MiMo-V2.6-Flash | 1024 | 46 | 45.83 | 22.63 | 2.03x |
| MiMo-V2.6-Flash | 4096 | 46 | 45.83 | 22.63 | 2.03x |
| MiMo-V2.6-Flash | 1 | 48 | 7.44 | 5.56 | 1.34x |
| MiMo-V2.6-Flash | 2 | 48 | 13.55 | 7.66 | 1.77x |
| MiMo-V2.6-Flash | 4 | 48 | 22.76 | 10.58 | 2.15x |
| MiMo-V2.6-Flash | 8 | 48 | 33.67 | 13.88 | 2.43x |
| MiMo-V2.6-Flash | 16 | 48 | 42.39 | 17.29 | 2.45x |
| MiMo-V2.6-Flash | 32 | 48 | 46.46 | 20.29 | 2.29x |
| MiMo-V2.6-Flash | 64 | 48 | 47.56 | 22.30 | 2.13x |
| MiMo-V2.6-Flash | 256 | 48 | 47.78 | 23.22 | 2.06x |
| MiMo-V2.6-Flash | 1024 | 48 | 47.78 | 23.22 | 2.06x |
| MiMo-V2.6-Flash | 4096 | 48 | 47.78 | 23.22 | 2.06x |
| MiMo-V2.6-Flash | 1 | 51 | 7.47 | 5.64 | 1.33x |
| MiMo-V2.6-Flash | 2 | 51 | 13.66 | 7.78 | 1.76x |
| MiMo-V2.6-Flash | 4 | 51 | 23.14 | 10.81 | 2.14x |
| MiMo-V2.6-Flash | 8 | 51 | 34.64 | 14.24 | 2.43x |
| MiMo-V2.6-Flash | 16 | 51 | 44.23 | 17.81 | 2.48x |
| MiMo-V2.6-Flash | 32 | 51 | 48.99 | 20.97 | 2.34x |
| MiMo-V2.6-Flash | 64 | 51 | 50.38 | 23.11 | 2.18x |
| MiMo-V2.6-Flash | 256 | 51 | 50.68 | 24.08 | 2.10x |
| MiMo-V2.6-Flash | 1024 | 51 | 50.68 | 24.09 | 2.10x |
| MiMo-V2.6-Flash | 4096 | 51 | 50.68 | 24.09 | 2.10x |
| MiMo-V2.6-Flash | 1 | 53 | 7.49 | 5.69 | 1.32x |
| MiMo-V2.6-Flash | 2 | 53 | 13.74 | 7.86 | 1.75x |
| MiMo-V2.6-Flash | 4 | 53 | 23.37 | 10.96 | 2.13x |
| MiMo-V2.6-Flash | 8 | 53 | 35.25 | 14.47 | 2.44x |
| MiMo-V2.6-Flash | 16 | 53 | 45.40 | 18.15 | 2.50x |
| MiMo-V2.6-Flash | 32 | 53 | 50.64 | 21.42 | 2.36x |
| MiMo-V2.6-Flash | 64 | 53 | 52.23 | 23.63 | 2.21x |
| MiMo-V2.6-Flash | 256 | 53 | 52.60 | 24.64 | 2.13x |
| MiMo-V2.6-Flash | 1024 | 53 | 52.60 | 24.65 | 2.13x |
| MiMo-V2.6-Flash | 4096 | 53 | 52.60 | 24.65 | 2.13x |
| MiMo-V2.6-Flash | 1 | 56 | 7.52 | 5.76 | 1.31x |
| MiMo-V2.6-Flash | 2 | 56 | 13.84 | 7.98 | 1.73x |
| MiMo-V2.6-Flash | 4 | 56 | 23.69 | 11.17 | 2.12x |
| MiMo-V2.6-Flash | 8 | 56 | 36.10 | 14.80 | 2.44x |
| MiMo-V2.6-Flash | 16 | 56 | 47.08 | 18.63 | 2.53x |
| MiMo-V2.6-Flash | 32 | 56 | 53.05 | 22.06 | 2.40x |
| MiMo-V2.6-Flash | 64 | 56 | 54.98 | 24.39 | 2.25x |
| MiMo-V2.6-Flash | 256 | 56 | 55.44 | 25.46 | 2.18x |
| MiMo-V2.6-Flash | 1024 | 56 | 55.44 | 25.46 | 2.18x |
| MiMo-V2.6-Flash | 4096 | 56 | 55.44 | 25.46 | 2.18x |
| MiMo-V2.6-Flash | 1 | 58 | 7.53 | 5.80 | 1.30x |
| MiMo-V2.6-Flash | 2 | 58 | 13.90 | 8.05 | 1.73x |
| MiMo-V2.6-Flash | 4 | 58 | 23.89 | 11.30 | 2.11x |
| MiMo-V2.6-Flash | 8 | 58 | 36.63 | 15.01 | 2.44x |
| MiMo-V2.6-Flash | 16 | 58 | 48.15 | 18.95 | 2.54x |
| MiMo-V2.6-Flash | 32 | 58 | 54.61 | 22.48 | 2.43x |
| MiMo-V2.6-Flash | 64 | 58 | 56.79 | 24.88 | 2.28x |
| MiMo-V2.6-Flash | 256 | 58 | 57.32 | 25.99 | 2.21x |
| MiMo-V2.6-Flash | 1024 | 58 | 57.32 | 25.99 | 2.21x |
| MiMo-V2.6-Flash | 4096 | 58 | 57.32 | 25.99 | 2.21x |
| MiMo-V2.6-Flash | 1 | 62 | 7.56 | 5.88 | 1.29x |
| MiMo-V2.6-Flash | 2 | 62 | 14.01 | 8.19 | 1.71x |
| MiMo-V2.6-Flash | 4 | 62 | 24.26 | 11.56 | 2.10x |
| MiMo-V2.6-Flash | 8 | 62 | 37.63 | 15.42 | 2.44x |
| MiMo-V2.6-Flash | 16 | 62 | 50.19 | 19.55 | 2.57x |
| MiMo-V2.6-Flash | 32 | 62 | 57.64 | 23.28 | 2.48x |
| MiMo-V2.6-Flash | 64 | 62 | 60.33 | 25.83 | 2.34x |
| MiMo-V2.6-Flash | 256 | 62 | 61.03 | 27.01 | 2.26x |
| MiMo-V2.6-Flash | 1024 | 62 | 61.03 | 27.01 | 2.26x |
| MiMo-V2.6-Flash | 4096 | 62 | 61.03 | 27.01 | 2.26x |
| MiMo-V2.6-Flash | 1 | 66 | 7.59 | 5.96 | 1.27x |
| MiMo-V2.6-Flash | 2 | 66 | 14.11 | 8.32 | 1.70x |
| MiMo-V2.6-Flash | 4 | 66 | 24.59 | 11.79 | 2.09x |
| MiMo-V2.6-Flash | 8 | 66 | 38.53 | 15.80 | 2.44x |
| MiMo-V2.6-Flash | 16 | 66 | 52.09 | 20.12 | 2.59x |
| MiMo-V2.6-Flash | 32 | 66 | 60.55 | 24.04 | 2.52x |
| MiMo-V2.6-Flash | 64 | 66 | 63.79 | 26.74 | 2.39x |
| MiMo-V2.6-Flash | 256 | 66 | 64.67 | 27.99 | 2.31x |
| MiMo-V2.6-Flash | 1024 | 66 | 64.68 | 28.00 | 2.31x |
| MiMo-V2.6-Flash | 4096 | 66 | 64.68 | 28.00 | 2.31x |
| MiMo-V2.6-Flash | 1 | 67 | 7.59 | 5.98 | 1.27x |
| MiMo-V2.6-Flash | 2 | 67 | 14.13 | 8.35 | 1.69x |
| MiMo-V2.6-Flash | 4 | 67 | 24.67 | 11.85 | 2.08x |
| MiMo-V2.6-Flash | 8 | 67 | 38.75 | 15.89 | 2.44x |
| MiMo-V2.6-Flash | 16 | 67 | 52.54 | 20.26 | 2.59x |
| MiMo-V2.6-Flash | 32 | 67 | 61.25 | 24.23 | 2.53x |
| MiMo-V2.6-Flash | 64 | 67 | 64.64 | 26.96 | 2.40x |
| MiMo-V2.6-Flash | 256 | 67 | 65.57 | 28.23 | 2.32x |
| MiMo-V2.6-Flash | 1024 | 67 | 65.57 | 28.23 | 2.32x |
| MiMo-V2.6-Flash | 4096 | 67 | 65.57 | 28.23 | 2.32x |
| MiMo-V2.6-Flash | 1 | 71 | 7.62 | 6.05 | 1.26x |
| MiMo-V2.6-Flash | 2 | 71 | 14.22 | 8.48 | 1.68x |
| MiMo-V2.6-Flash | 4 | 71 | 24.96 | 12.07 | 2.07x |
| MiMo-V2.6-Flash | 8 | 71 | 39.56 | 16.24 | 2.44x |
| MiMo-V2.6-Flash | 16 | 71 | 54.28 | 20.79 | 2.61x |
| MiMo-V2.6-Flash | 32 | 71 | 64.00 | 24.95 | 2.57x |
| MiMo-V2.6-Flash | 64 | 71 | 67.97 | 27.83 | 2.44x |
| MiMo-V2.6-Flash | 256 | 71 | 69.12 | 29.17 | 2.37x |
| MiMo-V2.6-Flash | 1024 | 71 | 69.12 | 29.17 | 2.37x |
| MiMo-V2.6-Flash | 4096 | 71 | 69.12 | 29.17 | 2.37x |
| MiMo-V2.6-Flash | 1 | 77 | 7.65 | 6.15 | 1.24x |
| MiMo-V2.6-Flash | 2 | 77 | 14.33 | 8.65 | 1.66x |
| MiMo-V2.6-Flash | 4 | 77 | 25.34 | 12.37 | 2.05x |
| MiMo-V2.6-Flash | 8 | 77 | 40.65 | 16.73 | 2.43x |
| MiMo-V2.6-Flash | 16 | 77 | 56.69 | 21.55 | 2.63x |
| MiMo-V2.6-Flash | 32 | 77 | 67.89 | 25.98 | 2.61x |
| MiMo-V2.6-Flash | 64 | 77 | 72.80 | 29.07 | 2.50x |
| MiMo-V2.6-Flash | 256 | 77 | 74.29 | 30.50 | 2.44x |
| MiMo-V2.6-Flash | 1024 | 77 | 74.29 | 30.51 | 2.44x |
| MiMo-V2.6-Flash | 4096 | 77 | 74.29 | 30.51 | 2.44x |
| MiMo-V2.6-Flash | 1 | 107 | 7.74 | 6.52 | 1.19x |
| MiMo-V2.6-Flash | 2 | 107 | 14.71 | 9.40 | 1.56x |
| MiMo-V2.6-Flash | 4 | 107 | 26.67 | 13.51 | 1.97x |
| MiMo-V2.6-Flash | 8 | 107 | 44.59 | 18.77 | 2.38x |
| MiMo-V2.6-Flash | 16 | 107 | 65.92 | 24.72 | 2.67x |
| MiMo-V2.6-Flash | 32 | 107 | 83.91 | 30.35 | 2.77x |
| MiMo-V2.6-Flash | 64 | 107 | 93.75 | 34.37 | 2.73x |
| MiMo-V2.6-Flash | 256 | 107 | 97.32 | 36.27 | 2.68x |
| MiMo-V2.6-Flash | 1024 | 107 | 97.33 | 36.27 | 2.68x |
| MiMo-V2.6-Flash | 4096 | 107 | 97.33 | 36.27 | 2.68x |
| MiMo-V2.6-Flash | 1 | 111 | 7.75 | 6.56 | 1.18x |
| MiMo-V2.6-Flash | 2 | 111 | 14.75 | 9.49 | 1.55x |
| MiMo-V2.6-Flash | 4 | 111 | 26.80 | 13.64 | 1.97x |
| MiMo-V2.6-Flash | 8 | 111 | 44.99 | 19.00 | 2.37x |
| MiMo-V2.6-Flash | 16 | 111 | 66.89 | 25.09 | 2.67x |
| MiMo-V2.6-Flash | 32 | 111 | 85.68 | 30.85 | 2.78x |
| MiMo-V2.6-Flash | 64 | 111 | 96.17 | 34.99 | 2.75x |
| MiMo-V2.6-Flash | 256 | 111 | 100.05 | 36.94 | 2.71x |
| MiMo-V2.6-Flash | 1024 | 111 | 100.06 | 36.95 | 2.71x |
| MiMo-V2.6-Flash | 4096 | 111 | 100.06 | 36.95 | 2.71x |
| MiMo-V2.6-Flash | 1 | 112 | 7.75 | 6.57 | 1.18x |
| MiMo-V2.6-Flash | 2 | 112 | 14.75 | 9.51 | 1.55x |
| MiMo-V2.6-Flash | 4 | 112 | 26.83 | 13.67 | 1.96x |
| MiMo-V2.6-Flash | 8 | 112 | 45.08 | 19.06 | 2.37x |
| MiMo-V2.6-Flash | 16 | 112 | 67.12 | 25.18 | 2.67x |
| MiMo-V2.6-Flash | 32 | 112 | 86.11 | 30.98 | 2.78x |
| MiMo-V2.6-Flash | 64 | 112 | 96.77 | 35.14 | 2.75x |
| MiMo-V2.6-Flash | 256 | 112 | 100.72 | 37.11 | 2.71x |
| MiMo-V2.6-Flash | 1024 | 112 | 100.73 | 37.11 | 2.71x |
| MiMo-V2.6-Flash | 4096 | 112 | 100.73 | 37.11 | 2.71x |
| MiMo-V2.6-Flash | 1 | 115 | 7.76 | 6.59 | 1.18x |
| MiMo-V2.6-Flash | 2 | 115 | 14.78 | 9.57 | 1.54x |
| MiMo-V2.6-Flash | 4 | 115 | 26.92 | 13.75 | 1.96x |
| MiMo-V2.6-Flash | 8 | 115 | 45.35 | 19.23 | 2.36x |
| MiMo-V2.6-Flash | 16 | 115 | 67.80 | 25.44 | 2.66x |
| MiMo-V2.6-Flash | 32 | 115 | 87.38 | 31.35 | 2.79x |
| MiMo-V2.6-Flash | 64 | 115 | 98.52 | 35.59 | 2.77x |
| MiMo-V2.6-Flash | 256 | 115 | 102.70 | 37.60 | 2.73x |
| MiMo-V2.6-Flash | 1024 | 115 | 102.71 | 37.61 | 2.73x |
| MiMo-V2.6-Flash | 4096 | 115 | 102.71 | 37.61 | 2.73x |
| MiMo-V2.6-Flash | 1 | 142 | 7.81 | 6.80 | 1.15x |
| MiMo-V2.6-Flash | 2 | 142 | 14.96 | 10.09 | 1.48x |
| MiMo-V2.6-Flash | 4 | 142 | 27.56 | 14.42 | 1.91x |
| MiMo-V2.6-Flash | 8 | 142 | 47.37 | 20.64 | 2.29x |
| MiMo-V2.6-Flash | 16 | 142 | 72.92 | 27.59 | 2.64x |
| MiMo-V2.6-Flash | 32 | 142 | 97.22 | 34.34 | 2.83x |
| MiMo-V2.6-Flash | 64 | 142 | 112.52 | 39.27 | 2.86x |
| MiMo-V2.6-Flash | 256 | 142 | 118.73 | 41.64 | 2.85x |
| MiMo-V2.6-Flash | 1024 | 142 | 118.74 | 41.65 | 2.85x |
| MiMo-V2.6-Flash | 4096 | 142 | 118.74 | 41.65 | 2.85x |
| MiMo-V2.6-Flash | 1 | 154 | 7.82 | 6.87 | 1.14x |
| MiMo-V2.6-Flash | 2 | 154 | 15.02 | 10.29 | 1.46x |
| MiMo-V2.6-Flash | 4 | 154 | 27.78 | 14.68 | 1.89x |
| MiMo-V2.6-Flash | 8 | 154 | 48.06 | 21.20 | 2.27x |
| MiMo-V2.6-Flash | 16 | 154 | 74.74 | 28.41 | 2.63x |
| MiMo-V2.6-Flash | 32 | 154 | 100.86 | 35.51 | 2.84x |
| MiMo-V2.6-Flash | 64 | 154 | 117.85 | 40.73 | 2.89x |
| MiMo-V2.6-Flash | 256 | 154 | 124.93 | 43.25 | 2.89x |
| MiMo-V2.6-Flash | 1024 | 154 | 124.94 | 43.25 | 2.89x |
| MiMo-V2.6-Flash | 4096 | 154 | 124.94 | 43.25 | 2.89x |
| MiMo-V2.6-Flash | 1 | 168 | 7.84 | 6.95 | 1.13x |
| MiMo-V2.6-Flash | 2 | 168 | 15.08 | 10.51 | 1.43x |
| MiMo-V2.6-Flash | 4 | 168 | 27.99 | 14.95 | 1.87x |
| MiMo-V2.6-Flash | 8 | 168 | 48.76 | 21.79 | 2.24x |
| MiMo-V2.6-Flash | 16 | 168 | 76.60 | 29.28 | 2.62x |
| MiMo-V2.6-Flash | 32 | 168 | 104.63 | 36.76 | 2.85x |
| MiMo-V2.6-Flash | 64 | 168 | 123.48 | 42.32 | 2.92x |
| MiMo-V2.6-Flash | 256 | 168 | 131.55 | 44.99 | 2.92x |
| MiMo-V2.6-Flash | 1024 | 168 | 131.56 | 45.00 | 2.92x |
| MiMo-V2.6-Flash | 4096 | 168 | 131.56 | 45.00 | 2.92x |
| MiMo-V2.6-Flash | 1 | 224 | 7.88 | 7.17 | 1.10x |
| MiMo-V2.6-Flash | 2 | 224 | 15.24 | 11.23 | 1.36x |
| MiMo-V2.6-Flash | 4 | 224 | 28.60 | 15.89 | 1.80x |
| MiMo-V2.6-Flash | 8 | 224 | 50.75 | 23.72 | 2.14x |
| MiMo-V2.6-Flash | 16 | 224 | 82.06 | 32.12 | 2.55x |
| MiMo-V2.6-Flash | 32 | 224 | 116.13 | 41.10 | 2.83x |
| MiMo-V2.6-Flash | 64 | 224 | 141.20 | 47.76 | 2.96x |
| MiMo-V2.6-Flash | 256 | 224 | 152.72 | 50.99 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 224 | 152.75 | 51.00 | 3.00x |
| MiMo-V2.6-Flash | 4096 | 224 | 152.75 | 51.00 | 3.00x |
| MiMo-V2.6-Flash | 1 | 335 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Flash | 2 | 335 | 15.41 | 12.20 | 1.26x |
| MiMo-V2.6-Flash | 4 | 335 | 29.22 | 17.38 | 1.68x |
| MiMo-V2.6-Flash | 8 | 335 | 52.84 | 26.01 | 2.03x |
| MiMo-V2.6-Flash | 16 | 335 | 88.02 | 36.44 | 2.42x |
| MiMo-V2.6-Flash | 32 | 335 | 129.41 | 47.38 | 2.73x |
| MiMo-V2.6-Flash | 64 | 335 | 162.72 | 55.62 | 2.93x |
| MiMo-V2.6-Flash | 256 | 335 | 179.13 | 59.69 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 335 | 179.16 | 59.70 | 3.00x |
| MiMo-V2.6-Flash | 4096 | 335 | 179.16 | 59.70 | 3.00x |
| MiMo-V2.6-Flash | 1 | 336 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Flash | 2 | 336 | 15.41 | 12.20 | 1.26x |
| MiMo-V2.6-Flash | 4 | 336 | 29.23 | 17.40 | 1.68x |
| MiMo-V2.6-Flash | 8 | 336 | 52.85 | 26.03 | 2.03x |
| MiMo-V2.6-Flash | 16 | 336 | 88.06 | 36.47 | 2.41x |
| MiMo-V2.6-Flash | 32 | 336 | 129.49 | 47.43 | 2.73x |
| MiMo-V2.6-Flash | 64 | 336 | 162.86 | 55.68 | 2.93x |
| MiMo-V2.6-Flash | 256 | 336 | 179.31 | 59.75 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 336 | 179.34 | 59.76 | 3.00x |
| MiMo-V2.6-Flash | 4096 | 336 | 179.34 | 59.76 | 3.00x |
| MiMo-V2.6-Flash | 1 | 448 | 7.94 | 7.55 | 1.05x |
| MiMo-V2.6-Flash | 2 | 448 | 15.49 | 12.84 | 1.21x |
| MiMo-V2.6-Flash | 4 | 448 | 29.55 | 18.62 | 1.59x |
| MiMo-V2.6-Flash | 8 | 448 | 53.95 | 27.39 | 1.97x |
| MiMo-V2.6-Flash | 16 | 448 | 91.28 | 39.89 | 2.29x |
| MiMo-V2.6-Flash | 32 | 448 | 136.98 | 51.59 | 2.66x |
| MiMo-V2.6-Flash | 64 | 448 | 175.48 | 61.76 | 2.84x |
| MiMo-V2.6-Flash | 256 | 448 | 195.13 | 66.41 | 2.94x |
| MiMo-V2.6-Flash | 1024 | 448 | 195.17 | 66.42 | 2.94x |
| MiMo-V2.6-Flash | 4096 | 448 | 195.17 | 66.42 | 2.94x |
| MiMo-V2.6-Flash | 1 | 672 | 7.96 | 7.69 | 1.03x |
| MiMo-V2.6-Flash | 2 | 672 | 15.58 | 13.60 | 1.15x |
| MiMo-V2.6-Flash | 4 | 672 | 29.87 | 20.51 | 1.46x |
| MiMo-V2.6-Flash | 8 | 672 | 55.08 | 29.30 | 1.88x |
| MiMo-V2.6-Flash | 16 | 672 | 94.67 | 44.33 | 2.14x |
| MiMo-V2.6-Flash | 32 | 672 | 145.08 | 58.07 | 2.50x |
| MiMo-V2.6-Flash | 64 | 672 | 189.49 | 69.57 | 2.72x |
| MiMo-V2.6-Flash | 256 | 672 | 212.96 | 75.92 | 2.81x |
| MiMo-V2.6-Flash | 1024 | 672 | 213.01 | 75.93 | 2.81x |
| MiMo-V2.6-Flash | 4096 | 672 | 213.01 | 75.93 | 2.81x |

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
| gpu | MiMo-V2.6-Flash | 1 | 937.30 | 35.3% |
| rom | MiMo-V2.6-Flash | 1 | 104.88 | 71.8% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| MiMo-V2.6-Flash | sram | interleaved | 128 B | 1.00x |
| MiMo-V2.6-Flash | hbm | interleaved | 32 B | 1.00x |

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
| MiMo-V2.6-Flash | 1 | 19 | 16.60% | 29.29 | 9.28 |
| MiMo-V2.6-Flash | 2 | 19 | 16.60% | 29.29 | 9.28 |
| MiMo-V2.6-Flash | 4 | 19 | 16.60% | 29.29 | 9.28 |
| MiMo-V2.6-Flash | 8 | 1 | 0.35% | 1.87 | 9.28 |
| MiMo-V2.6-Flash | 16 | 1 | 0.35% | 1.87 | 9.28 |
| MiMo-V2.6-Flash | 32 | 1 | 0.35% | 1.87 | 9.28 |
| MiMo-V2.6-Flash | 64 | 1 | 0.40% | 2.10 | 9.28 |
| MiMo-V2.6-Flash | 256 | 1 | 1.59% | 8.42 | 9.28 |

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
| MiMo-V2.6-Flash | 1 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 659.2 | 27,028.4 |
| MiMo-V2.6-Flash | 2 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 659.2 | 27,028.4 |
| MiMo-V2.6-Flash | 4 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 659.2 | 27,028.4 |
| MiMo-V2.6-Flash | 8 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 659.2 | 27,028.4 |
| MiMo-V2.6-Flash | 16 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 659.2 | 27,028.4 |
| MiMo-V2.6-Flash | 32 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 659.2 | 27,028.4 |
| MiMo-V2.6-Flash | 64 | 4.84% | 15.4 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 431.0 | 27,583.1 |
| MiMo-V2.6-Flash | 256 | 17.98% | 36.6 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 110.8 | 28,362.4 |
| MiMo-V2.6-Flash | 1024 | 54.75% | 95.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 27.9 | 28,559.3 |
| MiMo-V2.6-Flash | 4096 | 95.81% | 161.8 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 7.0 | 28,582.8 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 19 |
| gpu | layer_fixed_latency | 106 |
| gpu | link_latency | 605 |
| gpu | weight_read | 630 |
| rom | compute | 606 |
| rom | infeasible | 2324 |
| rom | kv_read | 280 |
| rom | layer_fixed_latency | 808 |
| rom | link_latency | 893 |
| rom | weight_read | 609 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2324 |

## Mechanical consistency audit

**FAIL** over 144,867 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x38', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x42', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x43', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x45', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x54', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x72', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x108', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x144', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x38', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x42', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x43', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x45', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x54', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x72', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x108', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x144', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x38', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x42', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x43', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x45', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x54', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x72', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x108', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x144', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x38', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x42', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x43', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x45', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x54', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x72', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x108', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x144', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x170', 'MiMo-V2.6-Flash', 1)

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

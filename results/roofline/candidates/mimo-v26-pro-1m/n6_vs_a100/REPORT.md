# Area-constrained roofline: n6_vs_a100-mimo-v26-pro-1m

> CANDIDATE MODEL under n6_vs_a100: MiMo-V2.6-Pro at 1,000,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 2,189x (ROM-N6-native-HBMKV-wafer-pipeline-x339-perstream, 19,228 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 263 devices. On the GPU side the correction reaches 36x (a100_sxm_80gb-x18971-pipeline, 18,971 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 168 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Pro takes 170 x 815 mm2 (138,550 mm2, array, KV in SRAM) at 1,784 tok/s per user and 13 tok/s per 1,000 mm2, holding 1 session, against 168 copies of one unified HBM die at the same silicon: 8.2x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Pro on 277,100 mm2 of ROM silicon at 2,389 tok/s per user against 276,710 mm2 of a100_sxm_80gb-x335-hybrid at 190 tok/s: **12.5x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 459. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 15,670,275 mm2 on MiMo-V2.6-Pro at batch 1, the iso-area GPU cluster is 18,971 devices. Cut as one serial pipeline that is 297 stages and 3,636 us of link latency per token; but the model has 70 layers, so at most 70 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 3,064 us. The iso-area per-user ratio at that point falls from 3.8x to 3.4x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 12.66x to it.** At 260,800 mm2 on MiMo-V2.6-Pro the pipeline-only GPU delivers 17.73 tok/s and the same silicon running tensor delivers 224 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.06x (MiMo-V2.6-Pro, ROM binding on `kv_read`) to 0.28x (MiMo-V2.6-Pro, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Pro engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 5 to 20,003 tok/s, and its rate with every slot occupied from 20,003 to 20,003. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 19,228 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 2,627 us over NVLink, capping per-user decode at 381 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 824.8 us and cap it at 1,212 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 9 of 10 operating points and an array 1; on tokens per second per square millimetre the same points go 1 to the array and 9 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 379 of 1319 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 3.6x of aggregate throughput (MiMo-V2.6-Pro). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 3.56x, on MiMo-V2.6-Pro at batch 4096, where the busiest region carries 3.17x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 11 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### MiMo-V2.6-Pro at 1,000,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x170`** -- 170 x 815 mm2 reticle dies, 138,550 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **1,784.5 tok/s per user** (0.56 ms/token), binding on `link_latency`
- **12.9 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 1,784 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 8,843 W at 0.064 W/mm2, 4,955.8 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 168 copies of one unified HBM die -- `a100_sxm_80gb-x168-tensor`, 138,768 mm2, area ratio 0.9984 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 138,550 | 138,768 | 0.9984 |
| user tok/s | 1,784.5 | 217.3 | 8.21x |
| aggregate tok/s | 1,784 | 217 | 0.60x |
| resident sessions | 1 | 225 | -- |
| J/token | 4.9558 | 121.4235 | 24.5x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 225 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x316-tensor` at 261,016 mm2 and 224.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-array-hw-hybrid-x263` | 214,345 | 2,310.2 | 10.8 | 1 | 10.38x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 260,800 | 2,401.1 | 9.2 | 1 | 10.70x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x170` | 138,550 | 1,784.5 | 12.9 | 1 | 8.21x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x170` | 138,550 | 1,784.5 | 12.9 | 1 | 8.21x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x170` | 138,550 | 1,784.5 | 12.9 | -- | 12.9 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x173` | 140,995 | 1,793.8 | 12.7 | 3.8 | 12.9 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x178` | 145,070 | 1,806.2 | 12.5 | 3.3 | 12.9 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x213` | 173,595 | 2,156.1 | 12.4 | 10.6 | 12.9 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x227` | 185,005 | 2,250.0 | 12.2 | 10.0 | 12.9 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x232-romfill` | 189,080 | 2,278.0 | 12.0 | 9.8 | 12.9 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x263` | 214,345 | 2,310.2 | 10.8 | 6.9 | 12.9 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x284` | 231,460 | 2,366.0 | 10.2 | 6.3 | 12.9 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x319` | 259,985 | 2,400.3 | 9.2 | 5.1 | 12.9 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 260,800 | 2,401.1 | 9.2 | 5.0 | 12.9 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x170` **<-- recommended** | 138,550 | 170 | 1,784.5 | 1,784 | 12.9 | 1 | `link_latency` | 8,843 | 4,955.8 | `a100_sxm_80gb-x168-tensor` | 8.21x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x173` | 140,995 | 173 | 1,793.8 | 1,794 | 12.7 | 1 | `link_latency` | 8,995 | 5,014.5 | `a100_sxm_80gb-x171-tensor` | 8.25x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x178` | 145,070 | 178 | 1,806.2 | 1,806 | 12.5 | 1 | `link_latency` | 9,475 | 5,245.7 | `a100_sxm_80gb-x176-tensor` | 8.29x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x213` | 173,595 | 213 | 2,156.1 | 2,156 | 12.4 | 1 | `layer_fixed_latency` | 13,678 | 6,343.9 | `a100_sxm_80gb-x210-tensor` | 9.79x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x227` | 185,005 | 227 | 2,250.0 | 2,250 | 12.2 | 1 | `layer_fixed_latency` | 15,351 | 6,822.4 | `a100_sxm_80gb-x224-tensor` | 10.18x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x232-romfill` | 189,080 | 232 | 2,278.0 | 2,278 | 12.0 | 1 | `layer_fixed_latency` | 15,947 | 7,000.3 | `a100_sxm_80gb-x229-tensor` | 10.29x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x263` | 214,345 | 263 | 2,310.2 | 2,310 | 10.8 | 1 | `layer_fixed_latency` | 19,617 | 8,491.3 | `a100_sxm_80gb-x259-tensor` | 10.38x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x284` | 231,460 | 284 | 2,366.0 | 2,366 | 10.2 | 1 | `layer_fixed_latency` | 22,109 | 9,344.3 | `a100_sxm_80gb-x280-tensor` | 10.59x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x319` | 259,985 | 319 | 2,400.3 | 2,400 | 9.2 | 1 | `layer_fixed_latency` | 26,252 | 10,936.9 | `a100_sxm_80gb-x315-tensor` | 10.70x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 260,800 | 320 | 2,401.1 | 2,401 | 9.2 | 1 | `layer_fixed_latency` | 26,370 | 10,982.6 | `a100_sxm_80gb-x316-tensor` | 10.70x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 132 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x170` | 138,550 | 1,784.5 | 12.9 | 1 |
| array | 132 | fastest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 260,800 | 2,401.1 | 9.2 | 1 |
| array | 132 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x170` | 138,550 | 1,784.5 | 12.9 | 1 |
| wafer | 42 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 1,339.4 | 9.7 | 1 |
| wafer | 42 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 1,874.2 | 6.8 | 1 |
| wafer | 42 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 1,339.4 | 9.7 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-hybrid-x320` | 260,800 | 2,401.1 | 2,401 | 1 | 26,370 | 10,982.6 | `layer_fixed_latency` | `a100_sxm_80gb-x316-tensor` | 224.4 | 432 | 213,075.2 | 0.999 | 10.70x | 19.4x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 1,874.2 | 1,874 | 1 | 28,668 | 15,296.5 | `link_latency` | `a100_sxm_80gb-x336-hybrid` | 190.6 | 461 | 264,387.2 | 0.999 | 9.84x | 17.3x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-hybrid-x340` | 277,100 | 2,389.3 | 2,389 | 1 | 28,731 | 12,025.1 | `layer_fixed_latency` | `a100_sxm_80gb-x335-hybrid` | 190.4 | 459 | 263,770.9 | 1.001 | 12.55x | 21.9x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 1,874.2 | -- | 1 | -- | 15,296.5 | -- | -- | -- | -- | -- | 0.999 | 0.78x wafer/array | -- |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 15,670,275 | 624.3 | 1,249 | 4,096 | 2,310,042 | 1,850,234.3 | `link_latency` | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 26,646 | 7,252,734.0 | 1.000 | 3.30x | 3.9x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 15,670,275 | 590.7 | 2,363 | 4,096 | 2,316,085 | 980,293.1 | `link_latency` | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 26,646 | 3,631,264.7 | 1.000 | 3.12x | 3.7x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 15,670,275 | 582.6 | 49,525 | 4,096 | 2,572,346 | 499,570.1 | `kv_read` | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 26,646 | 1,820,530.0 | 1.000 | 3.08x | 3.6x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 15,670,275 | 582.6 | 49,525 | 4,096 | 2,572,346 | 252,501.7 | `kv_read` | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 26,646 | 915,162.7 | 1.000 | 3.08x | 3.6x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 15,670,275 | 582.6 | 49,525 | 4,096 | 2,572,346 | 128,967.5 | `kv_read` | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 26,646 | 462,479.0 | 1.000 | 3.08x | 3.6x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 15,670,275 | 582.6 | 49,525 | 4,096 | 2,572,346 | 67,200.4 | `kv_read` | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 26,646 | 236,137.2 | 1.000 | 3.08x | 3.5x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 15,670,275 | 284.4 | 72,817 | 4,096 | 2,698,681 | 37,060.9 | `kv_read` | `a100_sxm_80gb-x18971-hybrid` | 189.1 | 26,646 | 66,380.8 | 1.000 | 1.50x | 1.8x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 15,670,275 | 88.4 | 90,544 | 4,096 | 2,794,883 | 30,867.6 | `kv_read` | `a100_sxm_80gb-x18971-hybrid` | 139.5 | 26,646 | 27,715.2 | 1.000 | 0.63x | 0.9x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 15,670,275 | 22.8 | 93,421 | 4,096 | 2,810,501 | 30,084.4 | `kv_read` | `a100_sxm_80gb-x18971-hybrid` | 77.4 | 26,646 | 17,180.4 | 1.000 | 0.29x | 0.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x170` | 138,550 | array | SRAM | 1 |
| 2-4 | `ROM-N6-native-HBMKV-wafer-tensor-x339` | 15,670,275 | wafer | HBM | 4,096 |
| 8-4096 | `ROM-N6-native-HBMKV-wafer-hybrid-x339` | 15,670,275 | wafer | HBM | 4,096 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Pro | SRAM | rom | 170, 173, 178, 185, 213, 227, 232, 278, 280, 284, 340 |
| MiMo-V2.6-Pro | SRAM | sram | 170, 173, 178, 185, 213, 227, 263, 284, 319, 320, 340 |

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
| MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-array-hw-tensor-x170` | 1 | 170 | 3.00 | hierarchical | 234.95 | 294.79 | 76.25 | 207.17 | 1,784.5 |
| MiMo-V2.6-Pro | `a100_sxm_80gb-x168-tensor` | 1 | 168 | 3.00 | hierarchical | 1,366.30 | 2,909.23 | 326.45 | 1,495.86 | 217.3 |
| MiMo-V2.6-Pro | `a100_sxm_80gb-x168-tensor` | 64 | 168 | 3.00 | hierarchical | 1,366.30 | 22,227.03 | 13,338.00 | 14,830.49 | 27.1 |

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

- **0 of 1,319 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 863 | 0 | 49.0% | 79.9% | 0.387 | 74% |
| rom | wafer (>=40,000 mm2) | 456 | 0 | 15.1% | 35.9% | 0.179 | 98% |

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
| MiMo-V2.6-Pro | 1 | 214,345 | `MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x263` | 8.491338 | 19,616.6 | layer_fixed_latency | `MiMo-V2.6-Pro/a100_sxm_80gb-x259-tensor` | 177.780541 | 39,576.0 | link_latency | 20.94x |
| MiMo-V2.6-Pro | 2 | 15,670,275 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-tensor-x339` | 1,850.234331 | 2,310,042.1 | link_latency | `MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid` | 7,252.734023 | 3,289,210.0 | link_latency | 3.92x |
| MiMo-V2.6-Pro | 4 | 15,670,275 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-tensor-x339` | 980.293093 | 2,316,085.2 | link_latency | `MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid` | 3,631.264685 | 3,289,210.0 | link_latency | 3.70x |
| MiMo-V2.6-Pro | 8 | 15,670,275 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339` | 499.570126 | 2,572,346.3 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid` | 1,820.530016 | 3,289,210.0 | link_latency | 3.64x |
| MiMo-V2.6-Pro | 16 | 15,670,275 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339` | 252.501687 | 2,572,346.3 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid` | 915.162682 | 3,289,210.0 | link_latency | 3.62x |
| MiMo-V2.6-Pro | 32 | 15,670,275 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339` | 128.967467 | 2,572,346.3 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid` | 462.479014 | 3,289,210.0 | link_latency | 3.59x |
| MiMo-V2.6-Pro | 64 | 15,670,275 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339` | 67.200357 | 2,572,346.3 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid` | 236.137181 | 3,289,210.0 | link_latency | 3.51x |
| MiMo-V2.6-Pro | 256 | 15,670,275 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339` | 37.060946 | 2,698,680.7 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid` | 66.380806 | 3,289,210.0 | link_latency | 1.79x |
| MiMo-V2.6-Pro | 1024 | 15,670,275 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339` | 30.867637 | 2,794,882.6 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid` | 27.715176 | 3,958,155.6 | link_latency | 0.90x |
| MiMo-V2.6-Pro | 4096 | 15,670,275 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339` | 30.084393 | 2,810,500.6 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid` | 17.180442 | 5,443,737.1 | kv_read | 0.57x |

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
| MiMo-V2.6-Pro | 1,000,000 | 1,020 B | 566.0 GB | 4.44 | 51.239 GB | 51.239 GB | 0.8 |

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
| MiMo-V2.6-Pro | 3 | 138,675 | 2,010.4 | wafer-pipeline | 1,339.4 | wafer-hybrid | 1.50x | 534.8 | pipeline | 217.3 | tensor | 2.46x | 3.76x | 6.16x | 1.64x |
| MiMo-V2.6-Pro | 4 | 184,900 | 3,955.5 | wafer-pipeline | 1,626.1 | wafer-hybrid | 2.43x | 559.2 | pipeline | 221.1 | tensor | 2.53x | 7.07x | 7.36x | 1.04x |
| MiMo-V2.6-Pro | 6 | 277,350 | 4,030.4 | wafer-pipeline | 1,874.2 | wafer-hybrid | 2.15x | 585.9 | pipeline | 190.6 | hybrid | 3.07x | 6.88x | 9.84x | 1.43x |
| MiMo-V2.6-Pro | 8 | 369,800 | 4,033.6 | wafer-pipeline | 1,761.6 | wafer-hybrid | 2.29x | 600.3 | pipeline | 195.0 | hybrid | 3.08x | 6.72x | 9.03x | 1.34x |
| MiMo-V2.6-Pro | 12 | 554,700 | 4,757.6 | wafer-pipeline | 1,564.2 | wafer-hybrid | 3.04x | 615.3 | pipeline | 193.1 | hybrid | 3.19x | 7.73x | 8.10x | 1.05x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.04x to 1.64x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Pro | 1 | fastest | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x320 | 260,800 | 2,401.1 | 2,401.1 | layer_fixed_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x316-tensor | 261,016 | 1.00x | tensor | 2,915.55 | 224.4 | 224.4 | link_latency | 10.70x | 0.43x | 135.39x | 10.70x |
| MiMo-V2.6-Pro | 1 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x170 | 138,550 | 1,784.5 | 1,784.5 | link_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x168-tensor | 138,768 | 1.00x | tensor | 2,909.23 | 217.3 | 217.3 | link_latency | 8.21x | 0.60x | 100.62x | 8.21x |
| MiMo-V2.6-Pro | 2 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-tensor-x339 | 15,670,275 | 624.3 | 1,248.5 | link_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid | 15,670,046 | 1.00x | hybrid | 3,063.62 | 189.1 | 56,159.2 | link_latency | 3.30x | 0.00x | 35.20x | 3.66x |
| MiMo-V2.6-Pro | 4 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-tensor-x339 | 15,670,275 | 590.7 | 2,362.6 | link_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid | 15,670,046 | 1.00x | hybrid | 3,063.62 | 189.1 | 56,159.2 | link_latency | 3.12x | 0.01x | 33.31x | 3.46x |
| MiMo-V2.6-Pro | 8 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 582.6 | 49,525.1 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid | 15,670,046 | 1.00x | hybrid | 3,063.62 | 189.1 | 56,159.2 | link_latency | 3.08x | 0.15x | 32.85x | 3.41x |
| MiMo-V2.6-Pro | 16 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 582.6 | 49,525.1 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid | 15,670,046 | 1.00x | hybrid | 3,063.62 | 189.1 | 56,159.2 | link_latency | 3.08x | 0.15x | 32.85x | 3.41x |
| MiMo-V2.6-Pro | 32 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 582.6 | 49,525.1 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid | 15,670,046 | 1.00x | hybrid | 3,063.62 | 189.1 | 56,159.2 | link_latency | 3.08x | 0.15x | 32.85x | 3.41x |
| MiMo-V2.6-Pro | 64 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 582.6 | 49,525.1 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid | 15,670,046 | 1.00x | hybrid | 3,063.62 | 189.1 | 56,159.2 | link_latency | 3.08x | 0.15x | 32.85x | 3.41x |
| MiMo-V2.6-Pro | 256 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 284.4 | 72,817.4 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid | 15,670,046 | 1.00x | hybrid | 3,063.62 | 189.1 | 56,159.2 | link_latency | 1.50x | 0.22x | 16.04x | 1.67x |
| MiMo-V2.6-Pro | 1024 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 88.4 | 90,544.1 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid | 15,670,046 | 1.00x | hybrid | 3,235.09 | 139.5 | 142,815.5 | link_latency | 0.63x | 0.27x | 4.99x | 0.77x |
| MiMo-V2.6-Pro | 4096 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 22.8 | 93,420.6 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid | 15,670,046 | 1.00x | hybrid | 1,285.86 | 77.4 | 316,856.6 | kv_read | 0.29x | 0.28x | 1.29x | 0.45x |

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
| MiMo-V2.6-Pro | 56 | 46,256 | 17.7 | 191.3 | 161.8 | tensor | 2,882.61 | 55.1% | link_latency |
| MiMo-V2.6-Pro | 92 | 75,992 | 17.7 | 205.7 | 183.5 | tensor | 2,899.25 | 59.6% | link_latency |
| MiMo-V2.6-Pro | 110 | 90,860 | 17.7 | 209.8 | 190.3 | tensor | 2,902.58 | 60.9% | link_latency |
| MiMo-V2.6-Pro | 112 | 92,512 | 17.7 | 210.1 | 190.9 | tensor | 2,902.58 | 61.0% | link_latency |
| MiMo-V2.6-Pro | 118 | 97,468 | 17.7 | 211.2 | 192.8 | tensor | 2,903.91 | 61.3% | link_latency |
| MiMo-V2.6-Pro | 126 | 104,076 | 17.7 | 212.5 | 195.0 | tensor | 2,905.07 | 61.7% | link_latency |
| MiMo-V2.6-Pro | 168 | 138,768 | 17.7 | 217.3 | 190.8 | tensor | 2,909.23 | 63.2% | link_latency |
| MiMo-V2.6-Pro | 171 | 141,246 | 17.7 | 217.5 | 191.5 | tensor | 2,909.84 | 63.3% | link_latency |
| MiMo-V2.6-Pro | 176 | 145,376 | 17.7 | 218.0 | 192.5 | tensor | 2,909.84 | 63.4% | link_latency |
| MiMo-V2.6-Pro | 183 | 151,158 | 17.7 | 218.5 | 193.8 | tensor | 2,910.39 | 63.6% | link_latency |
| MiMo-V2.6-Pro | 187 | 154,462 | 17.7 | 218.8 | 194.5 | tensor | 2,910.90 | 63.7% | link_latency |
| MiMo-V2.6-Pro | 188 | 155,288 | 17.7 | 218.9 | 194.7 | tensor | 2,910.90 | 63.7% | link_latency |
| MiMo-V2.6-Pro | 210 | 173,460 | 17.7 | 220.3 | 188.4 | tensor | 2,912.19 | 64.2% | link_latency |
| MiMo-V2.6-Pro | 224 | 185,024 | 17.7 | 221.1 | 190.7 | tensor | 2,912.56 | 64.4% | link_latency |
| MiMo-V2.6-Pro | 229 | 189,154 | 17.7 | 221.3 | 191.5 | tensor | 2,912.90 | 64.5% | link_latency |
| MiMo-V2.6-Pro | 259 | 213,934 | 17.7 | 222.6 | 187.8 | tensor | 2,914.07 | 64.9% | link_latency |
| MiMo-V2.6-Pro | 274 | 226,324 | 17.7 | 223.2 | 189.9 | tensor | 2,914.56 | 65.0% | link_latency |
| MiMo-V2.6-Pro | 276 | 227,976 | 17.7 | 223.2 | 190.1 | tensor | 2,914.56 | 65.1% | link_latency |
| MiMo-V2.6-Pro | 280 | 231,280 | 17.7 | 223.4 | 190.6 | tensor | 2,914.56 | 65.1% | link_latency |
| MiMo-V2.6-Pro | 315 | 260,190 | 17.7 | 224.4 | 194.7 | tensor | 2,915.55 | 65.4% | link_latency |
| MiMo-V2.6-Pro | 316 | 261,016 | 17.7 | 224.4 | 194.8 | tensor | 2,915.55 | 65.4% | link_latency |
| MiMo-V2.6-Pro | 335 | 276,710 | 17.7 | 188.7 | 190.4 | hybrid | 2,902.24 | 55.3% | link_latency |
| MiMo-V2.6-Pro | 336 | 277,536 | 17.7 | 188.7 | 190.6 | hybrid | 2,902.24 | 55.3% | link_latency |
| MiMo-V2.6-Pro | 392 | 323,792 | 17.7 | 189.6 | 190.5 | hybrid | 2,904.76 | 55.3% | link_latency |
| MiMo-V2.6-Pro | 448 | 370,048 | 17.7 | 190.2 | 195.0 | hybrid | 2,904.76 | 56.6% | link_latency |
| MiMo-V2.6-Pro | 672 | 555,072 | 17.7 | 191.6 | 193.1 | hybrid | 2,914.85 | 56.3% | link_latency |
| MiMo-V2.6-Pro | 2923 | 2,414,398 | 17.7 | 193.8 | 191.1 | tensor | 3,774.38 | 73.2% | link_latency |
| MiMo-V2.6-Pro | 18971 | 15,670,046 | 17.7 | 166.8 | 189.1 | hybrid | 3,063.62 | 57.9% | link_latency |

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
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x320 | MiMo-V2.6-Pro | 320 | pipeline | rom_package_ucie | rom_board_serdes | 69 | 2.50 us | 40,067.4 tok/s | 400,673.6 tok/s | 52 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.68 us; 17 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.82 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x173 | MiMo-V2.6-Pro | 173 | tensor | rom_package_ucie | rom_board_serdes | 280 | 191.37 us | 522.5 tok/s | 5,225.5 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 140 x all_reduce span 44 on rom_board_serdes (traversals 13.2) = 187.60 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x185 | MiMo-V2.6-Pro | 185 | hybrid | rom_package_ucie | rom_board_serdes | 186 | 8.68 us | 11,518.5 tok/s | 115,184.7 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 46 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.91 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x319 | MiMo-V2.6-Pro | 319 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x6 | MiMo-V2.6-Pro | 6 | pipeline | on_wafer | rom_wafer_serdes | 69 | 8.60 us | 11,625.1 tok/s | 116,251.0 tok/s | 68 x point_to_point span 2 on on_wafer (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-tensor-x170 | MiMo-V2.6-Pro | 170 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.51 us | 67.5 tok/s | 675.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 765.45 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x4 | MiMo-V2.6-Pro | 4 | tensor | on_wafer | rom_wafer_serdes | 280 | 300.95 us | 332.3 tok/s | 3,322.9 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 140 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 31.45 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hybrid-x263 | MiMo-V2.6-Pro | 263 | hybrid | nvlink3 | infiniband_hdr | 172 | 795.74 us | 125.7 tok/s | 1,256.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 32 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 80.69 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x6 | MiMo-V2.6-Pro | 6 | hybrid | on_wafer | rom_wafer_serdes | 145 | 270.01 us | 370.4 tok/s | 3,703.6 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 5 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.51 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x339 | MiMo-V2.6-Pro | 339 | pipeline | on_wafer | rom_wafer_serdes | 69 | 8.60 us | 11,625.1 tok/s | 116,251.0 tok/s | 68 x point_to_point span 2 on on_wafer (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-tensor-x339 | MiMo-V2.6-Pro | 339 | tensor | on_wafer | rom_wafer_serdes | 280 | 824.76 us | 121.2 tok/s | 1,212.5 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 140 x all_reduce span 338 on rom_wafer_serdes (traversals 39.6) = 555.26 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | MiMo-V2.6-Pro | 339 | hybrid | on_wafer | rom_wafer_serdes | 209 | 276.54 us | 361.6 tok/s | 3,616.1 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 69 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 7.04 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-pipeline | MiMo-V2.6-Pro | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 139.64 us | 716.1 tok/s | 7,161.5 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.51 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.13 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-tensor | MiMo-V2.6-Pro | 56 | tensor | nvlink3 | infiniband_hdr | 280 | 1,460.40 us | 68.5 tok/s | 684.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 745.35 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-hybrid | MiMo-V2.6-Pro | 56 | hybrid | nvlink3 | infiniband_hdr | 146 | 730.18 us | 137.0 tok/s | 1,369.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.13 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-expert | MiMo-V2.6-Pro | 56 | expert | nvlink3 | infiniband_hdr | 280 | 996.18 us | 100.4 tok/s | 1,003.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 702.15 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 294.03 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x92-pipeline | MiMo-V2.6-Pro | 92 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x92-tensor | MiMo-V2.6-Pro | 92 | tensor | nvlink3 | infiniband_hdr | 280 | 1,472.69 us | 67.9 tok/s | 679.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 757.64 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x92-hybrid | MiMo-V2.6-Pro | 92 | hybrid | nvlink3 | infiniband_hdr | 151 | 742.79 us | 134.6 tok/s | 1,346.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 27.74 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x92-expert | MiMo-V2.6-Pro | 92 | expert | nvlink3 | infiniband_hdr | 280 | 991.55 us | 100.9 tok/s | 1,008.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.37 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 290.18 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x110-pipeline | MiMo-V2.6-Pro | 110 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x110-tensor | MiMo-V2.6-Pro | 110 | tensor | nvlink3 | infiniband_hdr | 280 | 1,475.15 us | 67.8 tok/s | 677.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 760.09 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x110-hybrid | MiMo-V2.6-Pro | 110 | hybrid | nvlink3 | infiniband_hdr | 153 | 747.83 us | 133.7 tok/s | 1,337.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 32.78 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x110-expert | MiMo-V2.6-Pro | 110 | expert | nvlink3 | infiniband_hdr | 280 | 990.36 us | 101.0 tok/s | 1,009.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.16 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 289.20 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-pipeline | MiMo-V2.6-Pro | 112 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-tensor | MiMo-V2.6-Pro | 112 | tensor | nvlink3 | infiniband_hdr | 280 | 1,475.15 us | 67.8 tok/s | 677.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 760.09 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-hybrid | MiMo-V2.6-Pro | 112 | hybrid | nvlink3 | infiniband_hdr | 153 | 747.83 us | 133.7 tok/s | 1,337.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 32.78 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-expert | MiMo-V2.6-Pro | 112 | expert | nvlink3 | infiniband_hdr | 280 | 990.19 us | 101.0 tok/s | 1,009.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.08 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 289.12 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x118-pipeline | MiMo-V2.6-Pro | 118 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x118-tensor | MiMo-V2.6-Pro | 118 | tensor | nvlink3 | infiniband_hdr | 280 | 1,476.13 us | 67.7 tok/s | 677.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 761.08 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x118-hybrid | MiMo-V2.6-Pro | 118 | hybrid | nvlink3 | infiniband_hdr | 154 | 750.35 us | 133.3 tok/s | 1,332.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.30 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x118-expert | MiMo-V2.6-Pro | 118 | expert | nvlink3 | infiniband_hdr | 280 | 989.94 us | 101.0 tok/s | 1,010.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.08 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.87 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x126-pipeline | MiMo-V2.6-Pro | 126 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x126-tensor | MiMo-V2.6-Pro | 126 | tensor | nvlink3 | infiniband_hdr | 280 | 1,476.99 us | 67.7 tok/s | 677.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 761.94 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x126-hybrid | MiMo-V2.6-Pro | 126 | hybrid | nvlink3 | infiniband_hdr | 155 | 752.88 us | 132.8 tok/s | 1,328.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 37.82 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x126-expert | MiMo-V2.6-Pro | 126 | expert | nvlink3 | infiniband_hdr | 280 | 989.57 us | 101.1 tok/s | 1,010.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.00 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.57 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-pipeline | MiMo-V2.6-Pro | 168 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-tensor | MiMo-V2.6-Pro | 168 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.06 us | 67.6 tok/s | 675.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 765.01 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-hybrid | MiMo-V2.6-Pro | 168 | hybrid | nvlink3 | infiniband_hdr | 160 | 765.48 us | 130.6 tok/s | 1,306.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 50.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-expert | MiMo-V2.6-Pro | 168 | expert | nvlink3 | infiniband_hdr | 280 | 988.19 us | 101.2 tok/s | 1,011.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.72 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.48 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x171-pipeline | MiMo-V2.6-Pro | 171 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x171-tensor | MiMo-V2.6-Pro | 171 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.51 us | 67.5 tok/s | 675.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 765.45 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x171-hybrid | MiMo-V2.6-Pro | 171 | hybrid | nvlink3 | infiniband_hdr | 161 | 768.00 us | 130.2 tok/s | 1,302.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.95 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x171-expert | MiMo-V2.6-Pro | 171 | expert | nvlink3 | infiniband_hdr | 280 | 988.14 us | 101.2 tok/s | 1,012.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.72 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.42 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x176-pipeline | MiMo-V2.6-Pro | 176 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x176-tensor | MiMo-V2.6-Pro | 176 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.51 us | 67.5 tok/s | 675.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 765.45 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x176-hybrid | MiMo-V2.6-Pro | 176 | hybrid | nvlink3 | infiniband_hdr | 161 | 768.00 us | 130.2 tok/s | 1,302.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.95 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x176-expert | MiMo-V2.6-Pro | 176 | expert | nvlink3 | infiniband_hdr | 280 | 988.01 us | 101.2 tok/s | 1,012.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.68 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.33 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x183-pipeline | MiMo-V2.6-Pro | 183 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x183-tensor | MiMo-V2.6-Pro | 183 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.92 us | 67.5 tok/s | 675.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 23 on infiniband_hdr (traversals 2.0) = 765.86 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x183-hybrid | MiMo-V2.6-Pro | 183 | hybrid | nvlink3 | infiniband_hdr | 162 | 770.53 us | 129.8 tok/s | 1,297.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.47 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x183-expert | MiMo-V2.6-Pro | 183 | expert | nvlink3 | infiniband_hdr | 280 | 987.89 us | 101.2 tok/s | 1,012.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.68 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.21 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x187-pipeline | MiMo-V2.6-Pro | 187 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x187-tensor | MiMo-V2.6-Pro | 187 | tensor | nvlink3 | infiniband_hdr | 280 | 1,481.29 us | 67.5 tok/s | 675.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 766.24 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x187-hybrid | MiMo-V2.6-Pro | 187 | hybrid | nvlink3 | infiniband_hdr | 163 | 773.05 us | 129.4 tok/s | 1,293.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 57.99 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x187-expert | MiMo-V2.6-Pro | 187 | expert | nvlink3 | infiniband_hdr | 280 | 987.80 us | 101.2 tok/s | 1,012.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.65 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.14 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x188-pipeline | MiMo-V2.6-Pro | 188 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x188-tensor | MiMo-V2.6-Pro | 188 | tensor | nvlink3 | infiniband_hdr | 280 | 1,481.29 us | 67.5 tok/s | 675.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 766.24 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x188-hybrid | MiMo-V2.6-Pro | 188 | hybrid | nvlink3 | infiniband_hdr | 163 | 773.05 us | 129.4 tok/s | 1,293.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 57.99 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x188-expert | MiMo-V2.6-Pro | 188 | expert | nvlink3 | infiniband_hdr | 280 | 987.78 us | 101.2 tok/s | 1,012.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.65 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.13 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x210-pipeline | MiMo-V2.6-Pro | 210 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x210-tensor | MiMo-V2.6-Pro | 210 | tensor | nvlink3 | infiniband_hdr | 280 | 1,482.25 us | 67.5 tok/s | 674.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 767.19 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x210-hybrid | MiMo-V2.6-Pro | 210 | hybrid | nvlink3 | infiniband_hdr | 166 | 780.61 us | 128.1 tok/s | 1,281.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 26 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.56 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x210-expert | MiMo-V2.6-Pro | 210 | expert | nvlink3 | infiniband_hdr | 280 | 987.40 us | 101.3 tok/s | 1,012.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.58 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.82 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-pipeline | MiMo-V2.6-Pro | 224 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-tensor | MiMo-V2.6-Pro | 224 | tensor | nvlink3 | infiniband_hdr | 280 | 1,482.52 us | 67.5 tok/s | 674.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 767.47 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-hybrid | MiMo-V2.6-Pro | 224 | hybrid | nvlink3 | infiniband_hdr | 167 | 783.13 us | 127.7 tok/s | 1,276.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 68.08 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-expert | MiMo-V2.6-Pro | 224 | expert | nvlink3 | infiniband_hdr | 280 | 987.20 us | 101.3 tok/s | 1,013.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.54 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.66 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x229-pipeline | MiMo-V2.6-Pro | 229 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x229-tensor | MiMo-V2.6-Pro | 229 | tensor | nvlink3 | infiniband_hdr | 280 | 1,482.77 us | 67.4 tok/s | 674.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 767.72 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x229-hybrid | MiMo-V2.6-Pro | 229 | hybrid | nvlink3 | infiniband_hdr | 168 | 785.66 us | 127.3 tok/s | 1,272.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.60 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x229-expert | MiMo-V2.6-Pro | 229 | expert | nvlink3 | infiniband_hdr | 280 | 987.14 us | 101.3 tok/s | 1,013.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.54 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.60 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x259-pipeline | MiMo-V2.6-Pro | 259 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x259-tensor | MiMo-V2.6-Pro | 259 | tensor | nvlink3 | infiniband_hdr | 280 | 1,483.64 us | 67.4 tok/s | 674.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 33 on infiniband_hdr (traversals 2.0) = 768.58 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x259-hybrid | MiMo-V2.6-Pro | 259 | hybrid | nvlink3 | infiniband_hdr | 172 | 795.74 us | 125.7 tok/s | 1,256.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 32 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 80.69 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x259-expert | MiMo-V2.6-Pro | 259 | expert | nvlink3 | infiniband_hdr | 280 | 986.80 us | 101.3 tok/s | 1,013.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.47 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.33 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x274-pipeline | MiMo-V2.6-Pro | 274 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x274-tensor | MiMo-V2.6-Pro | 274 | tensor | nvlink3 | infiniband_hdr | 280 | 1,483.99 us | 67.4 tok/s | 673.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 768.94 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x274-hybrid | MiMo-V2.6-Pro | 274 | hybrid | nvlink3 | infiniband_hdr | 174 | 800.78 us | 124.9 tok/s | 1,248.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 85.73 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x274-expert | MiMo-V2.6-Pro | 274 | expert | nvlink3 | infiniband_hdr | 280 | 986.65 us | 101.4 tok/s | 1,013.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.44 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.21 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x276-pipeline | MiMo-V2.6-Pro | 276 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x276-tensor | MiMo-V2.6-Pro | 276 | tensor | nvlink3 | infiniband_hdr | 280 | 1,483.99 us | 67.4 tok/s | 673.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 768.94 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x276-hybrid | MiMo-V2.6-Pro | 276 | hybrid | nvlink3 | infiniband_hdr | 174 | 800.78 us | 124.9 tok/s | 1,248.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 85.73 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x276-expert | MiMo-V2.6-Pro | 276 | expert | nvlink3 | infiniband_hdr | 280 | 986.64 us | 101.4 tok/s | 1,013.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.44 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.19 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x280-pipeline | MiMo-V2.6-Pro | 280 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x280-tensor | MiMo-V2.6-Pro | 280 | tensor | nvlink3 | infiniband_hdr | 280 | 1,483.99 us | 67.4 tok/s | 673.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 768.94 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x280-hybrid | MiMo-V2.6-Pro | 280 | hybrid | nvlink3 | infiniband_hdr | 174 | 800.78 us | 124.9 tok/s | 1,248.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 85.73 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x280-expert | MiMo-V2.6-Pro | 280 | expert | nvlink3 | infiniband_hdr | 280 | 986.60 us | 101.4 tok/s | 1,013.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.43 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x315-pipeline | MiMo-V2.6-Pro | 315 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x315-tensor | MiMo-V2.6-Pro | 315 | tensor | nvlink3 | infiniband_hdr | 280 | 1,484.73 us | 67.4 tok/s | 673.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 40 on infiniband_hdr (traversals 2.0) = 769.68 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x315-hybrid | MiMo-V2.6-Pro | 315 | hybrid | nvlink3 | infiniband_hdr | 179 | 813.39 us | 122.9 tok/s | 1,229.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 98.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x315-expert | MiMo-V2.6-Pro | 315 | expert | nvlink3 | infiniband_hdr | 280 | 986.33 us | 101.4 tok/s | 1,013.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.39 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.95 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x316-pipeline | MiMo-V2.6-Pro | 316 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x316-tensor | MiMo-V2.6-Pro | 316 | tensor | nvlink3 | infiniband_hdr | 280 | 1,484.73 us | 67.4 tok/s | 673.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 40 on infiniband_hdr (traversals 2.0) = 769.68 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x316-hybrid | MiMo-V2.6-Pro | 316 | hybrid | nvlink3 | infiniband_hdr | 179 | 813.39 us | 122.9 tok/s | 1,229.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 98.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x316-expert | MiMo-V2.6-Pro | 316 | expert | nvlink3 | infiniband_hdr | 280 | 986.33 us | 101.4 tok/s | 1,013.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.39 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.94 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-pipeline | MiMo-V2.6-Pro | 335 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-tensor | MiMo-V2.6-Pro | 335 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.38 us | 48.7 tok/s | 487.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,338.32 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-hybrid | MiMo-V2.6-Pro | 335 | hybrid | nvlink3 | infiniband_hdr | 181 | 818.44 us | 122.2 tok/s | 1,221.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 103.38 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-expert | MiMo-V2.6-Pro | 335 | expert | nvlink3 | infiniband_hdr | 280 | 986.21 us | 101.4 tok/s | 1,014.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.37 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.84 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-pipeline | MiMo-V2.6-Pro | 336 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-tensor | MiMo-V2.6-Pro | 336 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.38 us | 48.7 tok/s | 487.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,338.32 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-hybrid | MiMo-V2.6-Pro | 336 | hybrid | nvlink3 | infiniband_hdr | 181 | 818.44 us | 122.2 tok/s | 1,221.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 103.38 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-expert | MiMo-V2.6-Pro | 336 | expert | nvlink3 | infiniband_hdr | 280 | 986.20 us | 101.4 tok/s | 1,014.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.36 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.84 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x392-pipeline | MiMo-V2.6-Pro | 392 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x392-tensor | MiMo-V2.6-Pro | 392 | tensor | nvlink3 | infiniband_hdr | 280 | 2,054.08 us | 48.7 tok/s | 486.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,339.03 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x392-hybrid | MiMo-V2.6-Pro | 392 | hybrid | nvlink3 | infiniband_hdr | 188 | 836.09 us | 119.6 tok/s | 1,196.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 121.03 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x392-expert | MiMo-V2.6-Pro | 392 | expert | nvlink3 | infiniband_hdr | 280 | 985.91 us | 101.4 tok/s | 1,014.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.31 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.60 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-pipeline | MiMo-V2.6-Pro | 448 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-tensor | MiMo-V2.6-Pro | 448 | tensor | nvlink3 | infiniband_hdr | 280 | 2,054.60 us | 48.7 tok/s | 486.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,339.55 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-hybrid | MiMo-V2.6-Pro | 448 | hybrid | nvlink3 | infiniband_hdr | 195 | 853.74 us | 117.1 tok/s | 1,171.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 138.68 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-expert | MiMo-V2.6-Pro | 448 | expert | nvlink3 | infiniband_hdr | 280 | 985.70 us | 101.5 tok/s | 1,014.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.27 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-pipeline | MiMo-V2.6-Pro | 672 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-tensor | MiMo-V2.6-Pro | 672 | tensor | nvlink3 | infiniband_hdr | 280 | 2,055.83 us | 48.6 tok/s | 486.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,340.78 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-hybrid | MiMo-V2.6-Pro | 672 | hybrid | nvlink3 | infiniband_hdr | 209 | 889.04 us | 112.5 tok/s | 1,124.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 69 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 173.98 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-expert | MiMo-V2.6-Pro | 672 | expert | nvlink3 | infiniband_hdr | 280 | 985.20 us | 101.5 tok/s | 1,015.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.18 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.02 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x2923-pipeline | MiMo-V2.6-Pro | 2923 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x2923-tensor | MiMo-V2.6-Pro | 2923 | tensor | nvlink3 | infiniband_hdr | 280 | 2,057.73 us | 48.6 tok/s | 486.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 366 on infiniband_hdr (traversals 4.0) = 1,342.67 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x2923-hybrid | MiMo-V2.6-Pro | 2923 | hybrid | nvlink3 | infiniband_hdr | 209 | 889.04 us | 112.5 tok/s | 1,124.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 69 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 173.98 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x2923-expert | MiMo-V2.6-Pro | 2923 | expert | nvlink3 | infiniband_hdr | 280 | 984.43 us | 101.6 tok/s | 1,015.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.04 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 284.39 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x18971-pipeline | MiMo-V2.6-Pro | 18971 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x18971-tensor | MiMo-V2.6-Pro | 18971 | tensor | nvlink3 | infiniband_hdr | 280 | 2,626.60 us | 38.1 tok/s | 380.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 2372 on infiniband_hdr (traversals 6.0) = 1,911.55 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x18971-hybrid | MiMo-V2.6-Pro | 18971 | hybrid | nvlink3 | infiniband_hdr | 209 | 889.04 us | 112.5 tok/s | 1,124.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 69 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 173.98 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x18971-expert | MiMo-V2.6-Pro | 18971 | expert | nvlink3 | infiniband_hdr | 280 | 984.24 us | 101.6 tok/s | 1,016.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.01 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 284.23 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Pro | 1 | array | array | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x263 | 214,345 | 2,310.2 | 0.011 | 2,310.2 (214,345) | 1,874.2 (277,350) | 0.81x | layer_fixed_latency |
| MiMo-V2.6-Pro | 2 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-tensor-x339 | 15,670,275 | 624.3 | 0.000 | — (—) | 624.3 (15,670,275) | — | link_latency |
| MiMo-V2.6-Pro | 4 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-tensor-x339 | 15,670,275 | 590.7 | 0.000 | — (—) | 590.7 (15,670,275) | — | link_latency |
| MiMo-V2.6-Pro | 8 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 582.6 | 0.000 | — (—) | 582.6 (15,670,275) | — | kv_read |
| MiMo-V2.6-Pro | 16 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 582.6 | 0.000 | — (—) | 582.6 (15,670,275) | — | kv_read |
| MiMo-V2.6-Pro | 32 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 582.6 | 0.000 | — (—) | 582.6 (15,670,275) | — | kv_read |
| MiMo-V2.6-Pro | 64 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 582.6 | 0.000 | — (—) | 582.6 (15,670,275) | — | kv_read |
| MiMo-V2.6-Pro | 256 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 284.4 | 0.000 | — (—) | 284.4 (15,670,275) | — | kv_read |
| MiMo-V2.6-Pro | 1024 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 88.4 | 0.000 | — (—) | 88.4 (15,670,275) | — | kv_read |
| MiMo-V2.6-Pro | 4096 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 22.8 | 0.000 | — (—) | 22.8 (15,670,275) | — | kv_read |

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
| MiMo-V2.6-Pro | 384 | 1,383.7 MB | 303.5 mm2 | 54.63 mm2 (18.0%) | 116,538 mm2 | 20,977 mm2 | 124,143 mm2 = 152.3 reticles |

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
| MiMo-V2.6-Pro | 1 | sram | 49,525.1 | 20,911.3 | 20,911.3 | 2.37x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 2 | sram | 49,525.1 | 20,911.3 | 20,911.3 | 2.37x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 4 | sram | 49,525.1 | 20,911.3 | 20,911.3 | 2.37x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 8 | sram | 49,525.1 | 20,911.3 | 20,911.3 | 2.37x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 16 | sram | 49,525.1 | 20,911.3 | 20,911.3 | 2.37x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 32 | sram | 49,525.1 | 20,911.3 | 20,911.3 | 2.37x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 64 | sram | 49,525.1 | 20,911.3 | 20,911.3 | 2.37x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 256 | sram | 72,817.4 | 24,168.9 | 47,758.4 | 3.01x | 1.98x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 1024 | sram | 90,544.1 | 25,839.3 | 87,125.0 | 3.50x | 3.37x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Pro | 4096 | sram | 93,420.6 | 26,068.5 | 92,807.0 | 3.58x | 3.56x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Pro | 1 | rom | 49,046.1 | 49,246.6 | 49,246.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 2 | rom | 49,046.1 | 49,246.6 | 49,246.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 4 | rom | 49,046.1 | 49,246.6 | 49,246.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 8 | rom | 49,046.1 | 49,246.6 | 49,246.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 16 | rom | 49,046.1 | 49,246.6 | 49,246.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 32 | rom | 49,046.1 | 49,246.6 | 49,246.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 64 | rom | 49,046.1 | 49,246.6 | 49,246.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 256 | rom | 72,124.8 | 72,539.3 | 72,422.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 1024 | rom | 90,363.3 | 90,466.2 | 90,462.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 4096 | rom | 93,395.8 | 93,387.6 | 93,383.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| MiMo-V2.6-Pro | 1 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 1.00 | 1.00 | 49,525.1 | 0.003 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-romfill | 15,670,275 | 87.87 | 1.00 | 49,046.1 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 1 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 1 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 1 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 1 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 2 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 1.00 | 1.00 | 49,525.1 | 0.003 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 2 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-romfill | 15,670,275 | 87.87 | 1.00 | 49,046.1 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 2 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 2 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 2 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 2 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 4 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 1.00 | 1.00 | 49,525.1 | 0.003 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-romfill | 15,670,275 | 87.87 | 1.00 | 49,046.1 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 4 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 4 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 4 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 4 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 8 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 1.00 | 1.00 | 49,525.1 | 0.003 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 8 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-romfill | 15,670,275 | 87.87 | 1.00 | 49,046.1 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 8 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 8 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 8 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 8 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 16 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 1.00 | 1.00 | 49,525.1 | 0.003 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 16 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-romfill | 15,670,275 | 87.87 | 1.00 | 49,046.1 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 16 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 16 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 16 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 16 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 32 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 1.00 | 1.00 | 49,525.1 | 0.003 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 32 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-romfill | 15,670,275 | 87.87 | 1.00 | 49,046.1 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 32 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 32 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 32 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 32 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 64 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 1.00 | 1.00 | 49,525.1 | 0.003 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 64 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-romfill | 15,670,275 | 87.87 | 1.00 | 49,046.1 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 64 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 64 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 64 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion | 15,670,275 | 1.00 | 1.00 | 20,911.3 | 0.001 | weight_read | 0.42x |
| MiMo-V2.6-Pro | 64 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion-romfill | 15,670,275 | 318.45 | 1.00 | 49,246.6 | 0.003 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 256 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 1.00 | 1.00 | 72,817.4 | 0.005 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 256 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-romfill | 15,670,275 | 87.87 | 1.00 | 72,124.8 | 0.005 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 256 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream | 15,670,275 | 1.00 | 1.51 | 24,168.9 | 0.002 | weight_read | 0.33x |
| MiMo-V2.6-Pro | 256 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream-romfill | 15,670,275 | 318.45 | 1.51 | 72,539.3 | 0.005 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 256 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion | 15,670,275 | 1.00 | 1.40 | 47,758.4 | 0.003 | weight_read | 0.66x |
| MiMo-V2.6-Pro | 256 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion-romfill | 15,670,275 | 318.45 | 1.08 | 72,422.2 | 0.005 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 1024 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 1.00 | 1.00 | 90,544.1 | 0.006 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-romfill | 15,670,275 | 87.87 | 1.00 | 90,363.3 | 0.006 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream | 15,670,275 | 1.00 | 1.70 | 25,839.3 | 0.002 | weight_read | 0.29x |
| MiMo-V2.6-Pro | 1024 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream-romfill | 15,670,275 | 318.45 | 1.70 | 90,466.2 | 0.006 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion | 15,670,275 | 1.00 | 2.52 | 87,125.0 | 0.006 | kv_read | 0.96x |
| MiMo-V2.6-Pro | 1024 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion-romfill | 15,670,275 | 318.45 | 1.11 | 90,462.8 | 0.006 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339 | 15,670,275 | 1.00 | 1.00 | 93,420.6 | 0.006 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-romfill | 15,670,275 | 87.87 | 1.00 | 93,395.8 | 0.006 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream | 15,670,275 | 1.00 | 1.70 | 26,068.5 | 0.002 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 4096 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perstream-romfill | 15,670,275 | 318.45 | 1.70 | 93,387.6 | 0.006 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion | 15,670,275 | 1.00 | 2.53 | 92,807.0 | 0.006 | kv_read | 0.99x |
| MiMo-V2.6-Pro | 4096 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x339-perregion-romfill | 15,670,275 | 318.45 | 1.11 | 93,383.9 | 0.006 | kv_read | 1.00x |

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
| MiMo-V2.6-Pro | 1 | 93 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 2 | 19,228 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 4 | 19,228 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 8 | 19,228 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 16 | 19,228 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 32 | 19,228 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 64 | 19,228 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 256 | 19,228 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 1024 | 19,228 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 4096 | 19,228 | 1.00 | 1.000 | 1.000 | 1.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Pro | 1 | 56 | 7.52 | 5.76 | 1.31x |
| MiMo-V2.6-Pro | 2 | 56 | 13.90 | 8.00 | 1.74x |
| MiMo-V2.6-Pro | 4 | 56 | 23.97 | 11.25 | 2.13x |
| MiMo-V2.6-Pro | 8 | 56 | 36.84 | 15.03 | 2.45x |
| MiMo-V2.6-Pro | 16 | 56 | 48.26 | 19.16 | 2.52x |
| MiMo-V2.6-Pro | 32 | 56 | 54.12 | 23.13 | 2.34x |
| MiMo-V2.6-Pro | 64 | 56 | 55.67 | 26.26 | 2.12x |
| MiMo-V2.6-Pro | 1 | 92 | 7.70 | 6.35 | 1.21x |
| MiMo-V2.6-Pro | 2 | 92 | 14.62 | 9.07 | 1.61x |
| MiMo-V2.6-Pro | 4 | 92 | 26.45 | 13.12 | 2.02x |
| MiMo-V2.6-Pro | 8 | 92 | 44.00 | 18.13 | 2.43x |
| MiMo-V2.6-Pro | 16 | 92 | 64.30 | 24.00 | 2.68x |
| MiMo-V2.6-Pro | 32 | 92 | 80.24 | 29.93 | 2.68x |
| MiMo-V2.6-Pro | 64 | 92 | 87.88 | 34.82 | 2.52x |
| MiMo-V2.6-Pro | 1 | 110 | 7.75 | 6.55 | 1.18x |
| MiMo-V2.6-Pro | 2 | 110 | 14.81 | 9.49 | 1.56x |
| MiMo-V2.6-Pro | 4 | 110 | 27.13 | 13.73 | 1.98x |
| MiMo-V2.6-Pro | 8 | 110 | 46.13 | 19.28 | 2.39x |
| MiMo-V2.6-Pro | 16 | 110 | 69.65 | 25.84 | 2.70x |
| MiMo-V2.6-Pro | 32 | 110 | 90.28 | 32.59 | 2.77x |
| MiMo-V2.6-Pro | 64 | 110 | 101.79 | 38.26 | 2.66x |
| MiMo-V2.6-Pro | 1 | 112 | 7.75 | 6.57 | 1.18x |
| MiMo-V2.6-Pro | 2 | 112 | 14.83 | 9.53 | 1.56x |
| MiMo-V2.6-Pro | 4 | 112 | 27.20 | 13.79 | 1.97x |
| MiMo-V2.6-Pro | 8 | 112 | 46.33 | 19.40 | 2.39x |
| MiMo-V2.6-Pro | 16 | 112 | 70.17 | 26.03 | 2.70x |
| MiMo-V2.6-Pro | 32 | 112 | 91.30 | 32.86 | 2.78x |
| MiMo-V2.6-Pro | 64 | 112 | 103.24 | 38.61 | 2.67x |
| MiMo-V2.6-Pro | 1 | 118 | 7.77 | 6.62 | 1.17x |
| MiMo-V2.6-Pro | 2 | 118 | 14.88 | 9.66 | 1.54x |
| MiMo-V2.6-Pro | 4 | 118 | 27.37 | 13.97 | 1.96x |
| MiMo-V2.6-Pro | 8 | 118 | 46.90 | 19.74 | 2.38x |
| MiMo-V2.6-Pro | 16 | 118 | 71.66 | 26.58 | 2.70x |
| MiMo-V2.6-Pro | 32 | 118 | 94.22 | 33.66 | 2.80x |
| MiMo-V2.6-Pro | 64 | 118 | 107.49 | 39.65 | 2.71x |
| MiMo-V2.6-Pro | 1 | 126 | 7.78 | 6.68 | 1.16x |
| MiMo-V2.6-Pro | 2 | 126 | 14.93 | 9.82 | 1.52x |
| MiMo-V2.6-Pro | 4 | 126 | 27.59 | 14.18 | 1.95x |
| MiMo-V2.6-Pro | 8 | 126 | 47.59 | 20.18 | 2.36x |
| MiMo-V2.6-Pro | 16 | 126 | 73.48 | 27.29 | 2.69x |
| MiMo-V2.6-Pro | 32 | 126 | 97.88 | 34.67 | 2.82x |
| MiMo-V2.6-Pro | 64 | 126 | 112.91 | 40.98 | 2.76x |
| MiMo-V2.6-Pro | 1 | 168 | 7.84 | 6.95 | 1.13x |
| MiMo-V2.6-Pro | 2 | 168 | 15.15 | 10.53 | 1.44x |
| MiMo-V2.6-Pro | 4 | 168 | 28.40 | 15.10 | 1.88x |
| MiMo-V2.6-Pro | 8 | 168 | 50.25 | 22.20 | 2.26x |
| MiMo-V2.6-Pro | 16 | 168 | 80.79 | 30.42 | 2.66x |
| MiMo-V2.6-Pro | 32 | 168 | 113.39 | 39.29 | 2.89x |
| MiMo-V2.6-Pro | 64 | 168 | 137.21 | 47.05 | 2.92x |
| MiMo-V2.6-Pro | 1 | 171 | 7.84 | 6.96 | 1.13x |
| MiMo-V2.6-Pro | 2 | 171 | 15.16 | 10.58 | 1.43x |
| MiMo-V2.6-Pro | 4 | 171 | 28.44 | 15.15 | 1.88x |
| MiMo-V2.6-Pro | 8 | 171 | 50.39 | 22.32 | 2.26x |
| MiMo-V2.6-Pro | 16 | 171 | 81.20 | 30.61 | 2.65x |
| MiMo-V2.6-Pro | 32 | 171 | 114.31 | 39.58 | 2.89x |
| MiMo-V2.6-Pro | 64 | 171 | 138.71 | 47.44 | 2.92x |
| MiMo-V2.6-Pro | 1 | 176 | 7.84 | 6.98 | 1.12x |
| MiMo-V2.6-Pro | 2 | 176 | 15.18 | 10.65 | 1.43x |
| MiMo-V2.6-Pro | 4 | 176 | 28.51 | 15.24 | 1.87x |
| MiMo-V2.6-Pro | 8 | 176 | 50.62 | 22.53 | 2.25x |
| MiMo-V2.6-Pro | 16 | 176 | 81.86 | 30.92 | 2.65x |
| MiMo-V2.6-Pro | 32 | 176 | 115.78 | 40.05 | 2.89x |
| MiMo-V2.6-Pro | 64 | 176 | 141.15 | 48.07 | 2.94x |
| MiMo-V2.6-Pro | 1 | 183 | 7.85 | 7.02 | 1.12x |
| MiMo-V2.6-Pro | 2 | 183 | 15.21 | 10.75 | 1.41x |
| MiMo-V2.6-Pro | 4 | 183 | 28.60 | 15.37 | 1.86x |
| MiMo-V2.6-Pro | 8 | 183 | 50.93 | 22.81 | 2.23x |
| MiMo-V2.6-Pro | 16 | 183 | 82.74 | 31.34 | 2.64x |
| MiMo-V2.6-Pro | 32 | 183 | 117.76 | 40.69 | 2.89x |
| MiMo-V2.6-Pro | 64 | 183 | 144.44 | 48.92 | 2.95x |
| MiMo-V2.6-Pro | 1 | 187 | 7.85 | 7.03 | 1.12x |
| MiMo-V2.6-Pro | 2 | 187 | 15.22 | 10.81 | 1.41x |
| MiMo-V2.6-Pro | 4 | 187 | 28.65 | 15.44 | 1.86x |
| MiMo-V2.6-Pro | 8 | 187 | 51.10 | 22.96 | 2.23x |
| MiMo-V2.6-Pro | 16 | 187 | 83.22 | 31.57 | 2.64x |
| MiMo-V2.6-Pro | 32 | 187 | 118.84 | 41.04 | 2.90x |
| MiMo-V2.6-Pro | 64 | 187 | 146.26 | 49.40 | 2.96x |
| MiMo-V2.6-Pro | 1 | 188 | 7.85 | 7.04 | 1.12x |
| MiMo-V2.6-Pro | 2 | 188 | 15.22 | 10.82 | 1.41x |
| MiMo-V2.6-Pro | 4 | 188 | 28.66 | 15.46 | 1.85x |
| MiMo-V2.6-Pro | 8 | 188 | 51.14 | 23.00 | 2.22x |
| MiMo-V2.6-Pro | 16 | 188 | 83.34 | 31.63 | 2.64x |
| MiMo-V2.6-Pro | 32 | 188 | 119.11 | 41.13 | 2.90x |
| MiMo-V2.6-Pro | 64 | 188 | 146.71 | 49.52 | 2.96x |
| MiMo-V2.6-Pro | 1 | 210 | 7.87 | 7.12 | 1.11x |
| MiMo-V2.6-Pro | 2 | 210 | 15.29 | 11.10 | 1.38x |
| MiMo-V2.6-Pro | 4 | 210 | 28.90 | 15.82 | 1.83x |
| MiMo-V2.6-Pro | 8 | 210 | 51.94 | 23.77 | 2.18x |
| MiMo-V2.6-Pro | 16 | 210 | 85.67 | 32.79 | 2.61x |
| MiMo-V2.6-Pro | 32 | 210 | 124.49 | 42.94 | 2.90x |
| MiMo-V2.6-Pro | 64 | 210 | 155.91 | 51.99 | 3.00x |
| MiMo-V2.6-Pro | 256 | 210 | 176.13 | 59.12 | 2.98x |
| MiMo-V2.6-Pro | 1 | 224 | 7.88 | 7.17 | 1.10x |
| MiMo-V2.6-Pro | 2 | 224 | 15.32 | 11.26 | 1.36x |
| MiMo-V2.6-Pro | 4 | 224 | 29.02 | 16.04 | 1.81x |
| MiMo-V2.6-Pro | 8 | 224 | 52.37 | 24.21 | 2.16x |
| MiMo-V2.6-Pro | 16 | 224 | 86.96 | 33.46 | 2.60x |
| MiMo-V2.6-Pro | 32 | 224 | 127.51 | 44.02 | 2.90x |
| MiMo-V2.6-Pro | 64 | 224 | 161.19 | 53.46 | 3.02x |
| MiMo-V2.6-Pro | 256 | 224 | 183.50 | 60.94 | 3.01x |
| MiMo-V2.6-Pro | 1 | 229 | 7.88 | 7.18 | 1.10x |
| MiMo-V2.6-Pro | 2 | 229 | 15.33 | 11.32 | 1.35x |
| MiMo-V2.6-Pro | 4 | 229 | 29.06 | 16.11 | 1.80x |
| MiMo-V2.6-Pro | 8 | 229 | 52.52 | 24.36 | 2.16x |
| MiMo-V2.6-Pro | 16 | 229 | 87.38 | 33.69 | 2.59x |
| MiMo-V2.6-Pro | 32 | 229 | 128.52 | 44.39 | 2.90x |
| MiMo-V2.6-Pro | 64 | 229 | 162.98 | 53.97 | 3.02x |
| MiMo-V2.6-Pro | 256 | 229 | 186.01 | 61.56 | 3.02x |
| MiMo-V2.6-Pro | 1 | 259 | 7.89 | 7.26 | 1.09x |
| MiMo-V2.6-Pro | 2 | 259 | 15.39 | 11.62 | 1.32x |
| MiMo-V2.6-Pro | 4 | 259 | 29.28 | 16.55 | 1.77x |
| MiMo-V2.6-Pro | 8 | 259 | 53.27 | 25.16 | 2.12x |
| MiMo-V2.6-Pro | 16 | 259 | 89.65 | 34.99 | 2.56x |
| MiMo-V2.6-Pro | 32 | 259 | 133.96 | 46.52 | 2.88x |
| MiMo-V2.6-Pro | 64 | 259 | 172.73 | 56.87 | 3.04x |
| MiMo-V2.6-Pro | 256 | 259 | 199.97 | 65.10 | 3.07x |
| MiMo-V2.6-Pro | 1 | 274 | 7.90 | 7.30 | 1.08x |
| MiMo-V2.6-Pro | 2 | 274 | 15.41 | 11.76 | 1.31x |
| MiMo-V2.6-Pro | 4 | 274 | 29.37 | 16.75 | 1.75x |
| MiMo-V2.6-Pro | 8 | 274 | 53.59 | 25.51 | 2.10x |
| MiMo-V2.6-Pro | 16 | 274 | 90.61 | 35.59 | 2.55x |
| MiMo-V2.6-Pro | 32 | 274 | 136.33 | 47.52 | 2.87x |
| MiMo-V2.6-Pro | 64 | 274 | 177.07 | 58.21 | 3.04x |
| MiMo-V2.6-Pro | 256 | 274 | 206.27 | 66.73 | 3.09x |
| MiMo-V2.6-Pro | 1 | 276 | 7.90 | 7.30 | 1.08x |
| MiMo-V2.6-Pro | 2 | 276 | 15.41 | 11.78 | 1.31x |
| MiMo-V2.6-Pro | 4 | 276 | 29.39 | 16.78 | 1.75x |
| MiMo-V2.6-Pro | 8 | 276 | 53.63 | 25.55 | 2.10x |
| MiMo-V2.6-Pro | 16 | 276 | 90.74 | 35.67 | 2.54x |
| MiMo-V2.6-Pro | 32 | 276 | 136.63 | 47.65 | 2.87x |
| MiMo-V2.6-Pro | 64 | 276 | 177.62 | 58.39 | 3.04x |
| MiMo-V2.6-Pro | 256 | 276 | 207.08 | 66.94 | 3.09x |
| MiMo-V2.6-Pro | 1 | 280 | 7.90 | 7.31 | 1.08x |
| MiMo-V2.6-Pro | 2 | 280 | 15.42 | 11.81 | 1.31x |
| MiMo-V2.6-Pro | 4 | 280 | 29.41 | 16.83 | 1.75x |
| MiMo-V2.6-Pro | 8 | 280 | 53.71 | 25.64 | 2.09x |
| MiMo-V2.6-Pro | 16 | 280 | 90.98 | 35.83 | 2.54x |
| MiMo-V2.6-Pro | 32 | 280 | 137.22 | 47.90 | 2.86x |
| MiMo-V2.6-Pro | 64 | 280 | 178.71 | 58.73 | 3.04x |
| MiMo-V2.6-Pro | 256 | 280 | 208.68 | 67.35 | 3.10x |
| MiMo-V2.6-Pro | 1 | 315 | 7.91 | 7.38 | 1.07x |
| MiMo-V2.6-Pro | 2 | 315 | 15.47 | 12.09 | 1.28x |
| MiMo-V2.6-Pro | 4 | 315 | 29.58 | 17.29 | 1.71x |
| MiMo-V2.6-Pro | 8 | 315 | 54.32 | 26.32 | 2.06x |
| MiMo-V2.6-Pro | 16 | 315 | 92.84 | 37.16 | 2.50x |
| MiMo-V2.6-Pro | 32 | 315 | 141.87 | 50.04 | 2.84x |
| MiMo-V2.6-Pro | 64 | 315 | 187.40 | 61.53 | 3.05x |
| MiMo-V2.6-Pro | 256 | 315 | 221.58 | 70.82 | 3.13x |
| MiMo-V2.6-Pro | 1 | 316 | 7.91 | 7.38 | 1.07x |
| MiMo-V2.6-Pro | 2 | 316 | 15.47 | 12.10 | 1.28x |
| MiMo-V2.6-Pro | 4 | 316 | 29.59 | 17.30 | 1.71x |
| MiMo-V2.6-Pro | 8 | 316 | 54.33 | 26.34 | 2.06x |
| MiMo-V2.6-Pro | 16 | 316 | 92.89 | 37.19 | 2.50x |
| MiMo-V2.6-Pro | 32 | 316 | 141.99 | 50.10 | 2.83x |
| MiMo-V2.6-Pro | 64 | 316 | 187.62 | 61.61 | 3.05x |
| MiMo-V2.6-Pro | 256 | 316 | 221.92 | 70.91 | 3.13x |
| MiMo-V2.6-Pro | 1 | 335 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Pro | 2 | 335 | 15.49 | 12.24 | 1.27x |
| MiMo-V2.6-Pro | 4 | 335 | 29.66 | 17.53 | 1.69x |
| MiMo-V2.6-Pro | 8 | 335 | 54.61 | 26.66 | 2.05x |
| MiMo-V2.6-Pro | 16 | 335 | 93.75 | 37.88 | 2.48x |
| MiMo-V2.6-Pro | 32 | 335 | 144.17 | 51.16 | 2.82x |
| MiMo-V2.6-Pro | 64 | 335 | 191.76 | 62.99 | 3.04x |
| MiMo-V2.6-Pro | 256 | 335 | 228.15 | 72.67 | 3.14x |
| MiMo-V2.6-Pro | 1 | 336 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Pro | 2 | 336 | 15.49 | 12.24 | 1.26x |
| MiMo-V2.6-Pro | 4 | 336 | 29.67 | 17.54 | 1.69x |
| MiMo-V2.6-Pro | 8 | 336 | 54.62 | 26.67 | 2.05x |
| MiMo-V2.6-Pro | 16 | 336 | 93.80 | 37.91 | 2.47x |
| MiMo-V2.6-Pro | 32 | 336 | 144.27 | 51.21 | 2.82x |
| MiMo-V2.6-Pro | 64 | 336 | 191.97 | 63.06 | 3.04x |
| MiMo-V2.6-Pro | 256 | 336 | 228.47 | 72.76 | 3.14x |
| MiMo-V2.6-Pro | 1 | 392 | 7.93 | 7.49 | 1.06x |
| MiMo-V2.6-Pro | 2 | 392 | 15.54 | 12.59 | 1.23x |
| MiMo-V2.6-Pro | 4 | 392 | 29.86 | 18.19 | 1.64x |
| MiMo-V2.6-Pro | 8 | 392 | 55.29 | 27.47 | 2.01x |
| MiMo-V2.6-Pro | 16 | 392 | 95.88 | 39.80 | 2.41x |
| MiMo-V2.6-Pro | 32 | 392 | 149.63 | 53.94 | 2.77x |
| MiMo-V2.6-Pro | 64 | 392 | 202.32 | 66.72 | 3.03x |
| MiMo-V2.6-Pro | 256 | 392 | 244.34 | 77.55 | 3.15x |
| MiMo-V2.6-Pro | 1 | 448 | 7.94 | 7.55 | 1.05x |
| MiMo-V2.6-Pro | 2 | 448 | 15.57 | 12.88 | 1.21x |
| MiMo-V2.6-Pro | 4 | 448 | 30.00 | 18.77 | 1.60x |
| MiMo-V2.6-Pro | 8 | 448 | 55.80 | 28.11 | 1.99x |
| MiMo-V2.6-Pro | 16 | 448 | 97.49 | 41.50 | 2.35x |
| MiMo-V2.6-Pro | 32 | 448 | 153.83 | 56.17 | 2.74x |
| MiMo-V2.6-Pro | 64 | 448 | 210.61 | 70.02 | 3.01x |
| MiMo-V2.6-Pro | 256 | 448 | 257.32 | 81.76 | 3.15x |
| MiMo-V2.6-Pro | 1 | 672 | 7.96 | 7.69 | 1.03x |
| MiMo-V2.6-Pro | 2 | 672 | 15.66 | 13.65 | 1.15x |
| MiMo-V2.6-Pro | 4 | 672 | 30.33 | 20.68 | 1.47x |
| MiMo-V2.6-Pro | 8 | 672 | 57.00 | 30.02 | 1.90x |
| MiMo-V2.6-Pro | 16 | 672 | 101.38 | 46.51 | 2.18x |
| MiMo-V2.6-Pro | 32 | 672 | 164.27 | 62.86 | 2.61x |
| MiMo-V2.6-Pro | 64 | 672 | 231.89 | 80.75 | 2.87x |
| MiMo-V2.6-Pro | 256 | 672 | 291.68 | 94.44 | 3.09x |
| MiMo-V2.6-Pro | 1 | 2923 | 7.99 | 7.93 | 1.01x |
| MiMo-V2.6-Pro | 2 | 2923 | 15.79 | 15.23 | 1.04x |
| MiMo-V2.6-Pro | 4 | 2923 | 30.86 | 27.04 | 1.14x |
| MiMo-V2.6-Pro | 8 | 2923 | 58.93 | 41.09 | 1.43x |
| MiMo-V2.6-Pro | 16 | 2923 | 107.80 | 58.15 | 1.85x |
| MiMo-V2.6-Pro | 32 | 2923 | 182.33 | 89.05 | 2.05x |
| MiMo-V2.6-Pro | 64 | 2923 | 270.86 | 121.04 | 2.24x |
| MiMo-V2.6-Pro | 256 | 2923 | 358.37 | 143.86 | 2.49x |
| MiMo-V2.6-Pro | 1024 | 2923 | 359.90 | 144.22 | 2.50x |
| MiMo-V2.6-Pro | 1 | 18971 | 8.00 | 7.99 | 1.00x |
| MiMo-V2.6-Pro | 2 | 18971 | 15.83 | 15.74 | 1.01x |
| MiMo-V2.6-Pro | 4 | 18971 | 30.99 | 30.28 | 1.02x |
| MiMo-V2.6-Pro | 8 | 18971 | 59.43 | 54.73 | 1.09x |
| MiMo-V2.6-Pro | 16 | 18971 | 109.50 | 86.48 | 1.27x |
| MiMo-V2.6-Pro | 32 | 18971 | 187.31 | 117.23 | 1.60x |
| MiMo-V2.6-Pro | 64 | 18971 | 282.08 | 150.53 | 1.87x |
| MiMo-V2.6-Pro | 256 | 18971 | 378.43 | 190.89 | 1.98x |
| MiMo-V2.6-Pro | 1024 | 18971 | 380.15 | 191.65 | 1.98x |
| MiMo-V2.6-Pro | 4096 | 18971 | 380.15 | 191.65 | 1.98x |

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
| gpu | MiMo-V2.6-Pro | 1 | 1,366.30 | 30.7% |
| rom | MiMo-V2.6-Pro | 1 | 232.43 | 55.8% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| MiMo-V2.6-Pro | sram | interleaved | 128 B | 1.00x |
| MiMo-V2.6-Pro | hbm | interleaved | 32 B | 1.00x |

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
| MiMo-V2.6-Pro | 1 | 93 | 97.45% | 840.44 | 9.27 |

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
| MiMo-V2.6-Pro | 1 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 4.9 | 20,002.7 |
| MiMo-V2.6-Pro | 2 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 4.9 | 20,002.7 |
| MiMo-V2.6-Pro | 4 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 4.9 | 20,002.7 |
| MiMo-V2.6-Pro | 8 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 4.9 | 20,002.7 |
| MiMo-V2.6-Pro | 16 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 4.9 | 20,002.7 |
| MiMo-V2.6-Pro | 32 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 4.9 | 20,002.7 |
| MiMo-V2.6-Pro | 64 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 4.9 | 20,002.7 |
| MiMo-V2.6-Pro | 256 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 4.9 | 20,002.7 |
| MiMo-V2.6-Pro | 1024 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 4.9 | 20,002.7 |
| MiMo-V2.6-Pro | 4096 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 4.9 | 20,002.7 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 257 |
| gpu | kv_read | 294 |
| gpu | link_latency | 407 |
| gpu | weight_read | 162 |
| rom | compute | 41 |
| rom | infeasible | 2484 |
| rom | kv_read | 85 |
| rom | layer_fixed_latency | 117 |
| rom | link_latency | 163 |
| rom | weight_read | 50 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 257 |
| rom | CAPACITY | 2484 |

## Mechanical consistency audit

**FAIL** over 48,913 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x173', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x178', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x185', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x213', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x263', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x284', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x319', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x320', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x173', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x178', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x185', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x213', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x263', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x284', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x319', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x320', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x173', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x178', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x185', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x213', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x263', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x284', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x319', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x320', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x173', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x178', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x185', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x213', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x263', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x284', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x319', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x320', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-tensor-x170', 'MiMo-V2.6-Pro', 1)

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

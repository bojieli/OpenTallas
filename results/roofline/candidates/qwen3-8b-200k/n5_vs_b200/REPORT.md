# Area-constrained roofline: n5_vs_b200-qwen3-8b-200k

> CANDIDATE MODEL under n5_vs_b200: Qwen3-8B at 200,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 6,101x (ROM-N5-native-HBMKV-wafer-pipeline-x139-perstream, 7,884 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 19 devices. On the GPU side the correction reaches 127x (b200_sxm-x4016-pipeline, 4,016 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 58 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Qwen3-8B takes 16 x 815 mm2 (13,040 mm2, array, KV in SRAM) at 16,514 tok/s per user and 1,266 tok/s per 1,000 mm2, holding 1 session, against 8 copies of one unified HBM die at the same silicon: 17.2x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Qwen3-8B on 13,040 mm2 of ROM silicon at 16,514 tok/s per user against 12,800 mm2 of b200_sxm-x8-tensor at 959 tok/s: **17.2x**, ROM binding on `weight_read` and the GPU on `kv_read`. It holds 1 resident session against the GPU cluster's 43. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 6,425,275 mm2 on Qwen3-8B at batch 1, the iso-area GPU cluster is 4,016 devices. Cut as one serial pipeline that is 56 stages and 295 us of link latency per token; but the model has 36 layers, so at most 36 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 252 us. The iso-area per-user ratio at that point falls from 1.2x to 1.1x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 24.97x to it.** At 554,700 mm2 on Qwen3-8B the pipeline-only GPU delivers 138.33 tok/s and the same silicon running hybrid delivers 3,453 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (Qwen3-8B, ROM binding on `weight_read`) to 0.21x (Qwen3-8B, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 794 us over NVLink, capping per-user decode at 1,259 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 313.1 us and cap it at 3,194 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.5x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
9. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 9 of 10 operating points and an array 1; on tokens per second per square millimetre the same points go 1 to the array and 9 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
10. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 355 of 1022 feasible points.
11. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 6.3x of aggregate throughput (Qwen3-8B). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
12. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 1.00x, on Qwen3-8B at batch 1, where the busiest region carries 1.00x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 10 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
13. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
14. **The cooling limit binds, and not where a uniform correction said it would.** 202 of 1,022 feasible points (19.8%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `Qwen3-8B/b200_sxm-x8-pipeline` at batch 32 on 12,800 mm2, throttled 1.05x from 49 to 46 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 88% kv read against 11.3% weight read. The ROM sweep is not what melts it.


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

### Qwen3-8B at 200,000 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x16`** -- 16 x 815 mm2 reticle dies, 13,040 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **16,514.4 tok/s per user** (0.06 ms/token), binding on `weight_read`
- **1,266.4 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 16,514 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 2,338 W at 0.179 W/mm2, 141.6 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 8 copies of one unified HBM die -- `b200_sxm-x8-tensor`, 12,800 mm2, area ratio 1.0188 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 13,040 | 12,800 | 1.0188 |
| user tok/s | 16,514.4 | 959.5 | 17.21x |
| aggregate tok/s | 16,514 | 959 | 14.92x |
| resident sessions | 1 | 43 | -- |
| J/token | 0.1416 | 7.6178 | 53.8x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 43 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x347-nvl72-hybrid` at 555,200 mm2 and 3,453.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-tensor-x26-romfill` | 21,190 | 19,208.3 | 906.5 | 1 | 13.66x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-array-hw-tensor-x27-romfill` | 22,005 | 19,448.8 | 883.8 | 1 | 13.10x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x16` | 13,040 | 16,514.4 | 1,266.4 | 1 | 17.21x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x16` | 13,040 | 16,514.4 | 1,266.4 | 1 | 17.21x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x16` | 13,040 | 16,514.4 | 1,266.4 | -- | 1,266.4 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x23-romfill` | 18,745 | 18,224.9 | 972.3 | 299.8 | 1,266.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x26-romfill` | 21,190 | 19,208.3 | 906.5 | 330.5 | 1,266.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x27-romfill` | 22,005 | 19,448.8 | 883.8 | 327.3 | 1,266.4 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x16` **<-- recommended** | 13,040 | 16 | 16,514.4 | 16,514 | 1,266.4 | 1 | `weight_read` | 2,338 | 141.6 | `b200_sxm-x8-tensor` | 17.21x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x23-romfill` | 18,745 | 23 | 18,224.9 | 18,225 | 972.3 | 1 | `link_latency` | 2,883 | 158.2 | `b200_sxm-x12-nvl72-tensor` | 13.77x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x26-romfill` | 21,190 | 26 | 19,208.3 | 19,208 | 906.5 | 1 | `link_latency` | 3,183 | 165.7 | `b200_sxm-x13-nvl72-tensor` | 13.66x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x27-romfill` | 22,005 | 27 | 19,448.8 | 19,449 | 883.8 | 1 | `link_latency` | 3,275 | 168.4 | `b200_sxm-x14-nvl72-tensor` | 13.10x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 138 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x16` | 13,040 | 16,514.4 | 1,266.4 | 1 |
| array | 138 | fastest | `ROM-N5-native-SRAMKV-array-hw-tensor-x27-romfill` | 22,005 | 19,448.8 | 883.8 | 1 |
| array | 138 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x16` | 13,040 | 16,514.4 | 1,266.4 | 1 |
| wafer | 46 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |
| wafer | 46 | fastest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |
| wafer | 46 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-tensor-x27-romfill` | 22,005 | 19,448.8 | 19,449 | 1 | 3,275 | 168.4 | `link_latency` | `b200_sxm-x14-nvl72-tensor` | 1,485.1 | 76 | 7,999.6 | 0.982 | 13.10x | 47.5x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 6,464 | 1 | 4,134 | 639.6 | `link_latency` | `b200_sxm-x29-nvl72-tensor` | 2,386.6 | 158 | 8,954.1 | 0.996 | 2.71x | 14.0x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-tensor-x57-romfill` | 46,455 | 14,851.8 | 14,852 | 1 | 4,935 | 332.3 | `link_latency` | `b200_sxm-x29-nvl72-tensor` | 2,386.6 | 158 | 8,954.1 | 1.001 | 6.22x | 26.9x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | -- | 1 | -- | 639.6 | -- | -- | -- | -- | -- | 1.005 | 0.44x wafer/array | -- |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x139-romfill` | 6,425,275 | 3,008.2 | 6,016 | 4,104 | 588,578 | 97,829.8 | `link_latency` | `b200_sxm-x4016-nvl72-hybrid` | 2,821.9 | 22,059 | 254,064.9 | 1.000 | 1.07x | 2.6x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x139-romfill` | 6,425,275 | 2,896.9 | 11,588 | 4,104 | 605,876 | 52,286.5 | `link_latency` | `b200_sxm-x4016-nvl72-hybrid` | 2,821.9 | 22,059 | 129,380.4 | 1.000 | 1.03x | 2.5x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x139` | 6,425,275 | 2,697.4 | 21,579 | 4,104 | 1,015,192 | 47,045.8 | `link_latency` | `b200_sxm-x4016-nvl72-hybrid` | 2,821.9 | 22,059 | 67,038.1 | 1.000 | 0.96x | 1.4x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x139` | 6,425,275 | 2,370.7 | 37,932 | 4,104 | 1,065,964 | 28,102.1 | `link_latency` | `b200_sxm-x4016-nvl72-hybrid` | 2,821.9 | 22,059 | 35,867.0 | 1.000 | 0.84x | 1.3x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x139` | 6,425,275 | 1,908.5 | 61,073 | 4,104 | 1,137,813 | 18,630.2 | `link_latency` | `b200_sxm-x4016-nvl72-hybrid` | 2,821.9 | 22,059 | 20,281.4 | 1.000 | 0.68x | 1.1x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x139` | 6,425,275 | 1,373.1 | 87,881 | 4,104 | 1,221,043 | 13,894.3 | `kv_read` | `b200_sxm-x4016-nvl72-hybrid` | 2,743.2 | 22,059 | 12,513.2 | 1.000 | 0.50x | 0.9x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 6,425,275 | 585.3 | 149,844 | 4,104 | 1,035,508 | 6,910.6 | `kv_read` | `b200_sxm-x4016-nvl72-hybrid` | 1,643.6 | 22,059 | 6,797.7 | 1.000 | 0.36x | 1.0x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x139` | 6,425,275 | 156.6 | 160,326 | 4,104 | 1,446,068 | 9,019.6 | `kv_read` | `b200_sxm-x4016-nvl72-hybrid` | 631.3 | 22,059 | 5,368.9 | 1.000 | 0.25x | 0.6x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x139` | 6,425,275 | 39.8 | 163,179 | 4,104 | 1,454,851 | 8,915.7 | `kv_read` | `b200_sxm-x4016-hybrid` | 190.6 | 22,059 | 5,102.1 | 1.000 | 0.21x | 0.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x16` | 13,040 | array | SRAM | 1 |
| 2-4 | `ROM-N5-native-HBMKV-wafer-tensor-x139-romfill` | 6,425,275 | wafer | HBM | 4,104 |
| 8-64 | `ROM-N5-native-HBMKV-wafer-tensor-x139` | 6,425,275 | wafer | HBM | 4,104 |
| 256 | `ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 6,425,275 | wafer | HBM | 4,104 |
| 1024-4096 | `ROM-N5-native-HBMKV-wafer-hybrid-x139` | 6,425,275 | wafer | HBM | 4,104 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Qwen3-8B | SRAM | rom | 19, 23, 26, 27, 30, 45, 57, 60, 113, 170, 227, 340 |
| Qwen3-8B | SRAM | sram | 16, 19, 23, 30, 45, 57, 60, 113, 170, 227, 340 |

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
(5.563e+11 B/s/mm2).

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

**The thermal limit binds here, and this is the first version of this
study in which it could.**
Static power is charged per mm2 per second whether or not a byte moves,
so the coolable step time solves
`t >= E_dynamic / (cooling_limit - P_static)` rather than dividing the
total energy by the total limit. Under the old rule stretching a step
always reduced modelled power, so every design was coolable at some speed
and `thermal_scale` was exactly 1.0 at all 11,747 feasible points across
both studies.

- **202 of 1,022 feasible points (19.8%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 202.
- By area class: large array (5,000-40,000 mm2) 99, wafer (>=40,000 mm2) 103.
- By KV store: hbm 202.
- By batch: B=1 18, B=2 18, B=4 18, B=8 24, B=16 32, B=32 37, B=64 30, B=256 15, B=1024 7, B=4096 3.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 45% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 32.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 206 | 99 | 99.4% | 100.0% | 0.625 | 35% |
| gpu | wafer (>=40,000 mm2) | 398 | 103 | 87.6% | 100.0% | 0.625 | 40% |
| rom | large array (5,000-40,000 mm2) | 114 | 0 | 18.0% | 35.9% | 0.179 | 78% |
| rom | wafer (>=40,000 mm2) | 304 | 0 | 22.0% | 45.3% | 0.226 | 91% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `Qwen3-8B/b200_sxm-x8-pipeline` | Qwen3-8B | 32 | 12,800 | hbm | 1.049x | 8,000.0 / 8,000.0 W | 35% | 46.4 | 48.6 |
| `Qwen3-8B/b200_sxm-x12-pipeline` | Qwen3-8B | 64 | 19,200 | hbm | 1.049x | 12,000.0 / 12,000.0 W | 35% | 35.8 | 37.6 |
| `Qwen3-8B/b200_sxm-x13-pipeline` | Qwen3-8B | 64 | 20,800 | hbm | 1.049x | 13,000.0 / 13,000.0 W | 35% | 38.5 | 40.4 |
| `Qwen3-8B/b200_sxm-x9-pipeline` | Qwen3-8B | 32 | 14,400 | hbm | 1.049x | 9,000.0 / 9,000.0 W | 35% | 51.4 | 53.9 |
| `Qwen3-8B/b200_sxm-x14-pipeline` | Qwen3-8B | 64 | 22,400 | hbm | 1.049x | 14,000.0 / 14,000.0 W | 35% | 41.2 | 43.2 |
| `Qwen3-8B/b200_sxm-x15-pipeline` | Qwen3-8B | 64 | 24,000 | hbm | 1.049x | 15,000.0 / 15,000.0 W | 35% | 43.8 | 45.9 |
| `Qwen3-8B/b200_sxm-x10-pipeline` | Qwen3-8B | 32 | 16,000 | hbm | 1.049x | 10,000.0 / 10,000.0 W | 35% | 56.4 | 59.1 |
| `Qwen3-8B/b200_sxm-x8-pipeline` | Qwen3-8B | 16 | 12,800 | hbm | 1.049x | 8,000.0 / 8,000.0 W | 35% | 83.3 | 87.3 |
| `Qwen3-8B/b200_sxm-x12-pipeline` | Qwen3-8B | 32 | 19,200 | hbm | 1.048x | 12,000.0 / 12,000.0 W | 35% | 65.8 | 69.0 |
| `Qwen3-8B/b200_sxm-x13-pipeline` | Qwen3-8B | 32 | 20,800 | hbm | 1.048x | 13,000.0 / 13,000.0 W | 35% | 70.3 | 73.7 |
| `Qwen3-8B/b200_sxm-x9-pipeline` | Qwen3-8B | 16 | 14,400 | hbm | 1.048x | 9,000.0 / 9,000.0 W | 35% | 91.3 | 95.7 |
| `Qwen3-8B/b200_sxm-x14-pipeline` | Qwen3-8B | 32 | 22,400 | hbm | 1.048x | 14,000.0 / 14,000.0 W | 35% | 74.8 | 78.4 |

The worst point's dynamic energy is kv read 88.3%, weight read 11.3%, operand delivery 0.2%, arithmetic 0.1%. **The ROM sweep is not what melts it.** A mask-ROM array
reads its weights for almost nothing; what it still pays for, at
the same rate a GPU does, is KV traffic to DRAM. That is an
argument for keeping KV on die, and it is visible here only
because the power model now distinguishes the two.

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
| Qwen3-8B | 1 | 21,190 | `Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x26-romfill` | 0.165713 | 3,183.1 | link_latency | `Qwen3-8B/b200_sxm-x13-nvl72-tensor` | 7.935924 | 11,158.4 | kv_read | 47.89x |
| Qwen3-8B | 2 | 6,425,275 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139-romfill` | 97.829815 | 588,578.2 | link_latency | `Qwen3-8B/b200_sxm-x4016-nvl72-hybrid` | 254.064902 | 2,149,425.5 | link_latency | 2.60x |
| Qwen3-8B | 4 | 6,425,275 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139-romfill` | 52.286503 | 605,875.5 | link_latency | `Qwen3-8B/b200_sxm-x4016-nvl72-hybrid` | 129.380382 | 2,149,425.5 | link_latency | 2.47x |
| Qwen3-8B | 8 | 6,425,275 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139` | 47.045779 | 1,015,192.4 | link_latency | `Qwen3-8B/b200_sxm-x4016-nvl72-hybrid` | 67.038121 | 2,149,425.5 | link_latency | 1.42x |
| Qwen3-8B | 16 | 6,425,275 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139` | 28.102082 | 1,065,964.3 | link_latency | `Qwen3-8B/b200_sxm-x4016-nvl72-hybrid` | 35.866991 | 2,149,425.5 | link_latency | 1.28x |
| Qwen3-8B | 32 | 6,425,275 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139` | 18.630233 | 1,137,812.9 | link_latency | `Qwen3-8B/b200_sxm-x4016-nvl72-hybrid` | 20.281426 | 2,149,425.5 | link_latency | 1.09x |
| Qwen3-8B | 64 | 6,425,275 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139` | 13.894309 | 1,221,042.6 | kv_read | `Qwen3-8B/b200_sxm-x4016-nvl72-hybrid` | 12.513232 | 2,196,876.4 | link_latency | 0.90x |
| Qwen3-8B | 256 | 6,425,275 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill` | 6.910552 | 1,035,507.8 | kv_read | `Qwen3-8B/b200_sxm-x4016-nvl72-hybrid` | 6.797735 | 2,860,176.6 | link_latency | 0.98x |
| Qwen3-8B | 1024 | 6,425,275 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139` | 9.019560 | 1,446,067.6 | kv_read | `Qwen3-8B/b200_sxm-x4016-nvl72-hybrid` | 5.368860 | 3,470,779.6 | kv_read | 0.60x |
| Qwen3-8B | 4096 | 6,425,275 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139` | 8.915663 | 1,454,851.1 | kv_read | `Qwen3-8B/b200_sxm-x4016-hybrid` | 5.102079 | 3,984,176.1 | kv_read | 0.56x |

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


## Derived technology at N5

These are outputs of the graded primitives, not inputs.

| Quantity | Value | Grade |
|---|---:|---|
| SRAM capacity density | 3.869 MB/mm2 | assumed |
| ROM capacity density | 9.380 MB/mm2 | derived |
| ROM read bandwidth density | 362.9 GB/s/mm2 | derived |
| SRAM read bandwidth density | 556.3 GB/s/mm2 | derived |
| Compute density, bf16 | 0.680 Tops/s/mm2 | derived |
| Compute density, fp8 | 1.360 Tops/s/mm2 | derived |
| Compute density, w4a8 | 1.923 Tops/s/mm2 | derived |
| Compute density, fp4 | 2.720 Tops/s/mm2 | derived |
| Compute density, fp32 | 0.042 Tops/s/mm2 | derived |
| ROM full-array sweep time | 34.5 us | derived |
| ROM per-token ceiling from that sweep | 29,015 tok/s | derived |
| ROM per-token ceiling before the read derate | 38,686 tok/s | derived |

The ROM full-array sweep time is rom_capacity_density divided by rom_read_bandwidth_density. Both scale with the same published bitcell-area ratio under this derivation, so the sweep time -- and hence the ROM path's hard per-token ceiling -- is the SAME at every node. Process scaling buys a ROM design capacity, not per-token speed. No clock-frequency bonus is credited, which makes this the conservative reading.

## Models and their work

| Model | Context | Params | Checkpoint | Native bits/param | KV read/token | KV/user | W:KV at B=1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 200,000 | 8 B | 16.4 GB | 16.00 | 29.491 GB | 29.491 GB | 0.5 |

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
| Qwen3-8B | 1 | 46,225 | 48,858.2 | wafer-pipeline | 6,464.4 | wafer-tensor | 7.56x | 3,410.4 | pipeline | 2,386.6 | tensor | 1.43x | 14.33x | 2.71x | 0.19x |
| Qwen3-8B | 2 | 92,450 | 46,516.4 | wafer-pipeline | 6,019.4 | wafer-hybrid | 7.73x | 5,587.3 | pipeline | 3,330.1 | tensor | 1.68x | 8.33x | 1.81x | 0.22x |
| Qwen3-8B | 3 | 138,675 | 46,516.4 | wafer-pipeline | 5,822.1 | wafer-tensor | 7.99x | 7,259.7 | pipeline | 2,923.3 | hybrid | 2.48x | 6.41x | 1.99x | 0.31x |
| Qwen3-8B | 4 | 184,900 | 46,516.4 | wafer-pipeline | 5,821.3 | wafer-tensor | 7.99x | 8,537.3 | pipeline | 3,305.9 | hybrid | 2.58x | 5.45x | 1.76x | 0.32x |
| Qwen3-8B | 6 | 277,350 | 46,516.4 | wafer-pipeline | 5,329.1 | wafer-tensor | 8.73x | 10,335.3 | pipeline | 3,274.7 | hybrid | 3.16x | 4.50x | 1.63x | 0.36x |
| Qwen3-8B | 8 | 369,800 | 46,516.4 | wafer-pipeline | 5,328.8 | wafer-tensor | 8.73x | 11,581.6 | pipeline | 3,253.1 | hybrid | 3.56x | 4.02x | 1.64x | 0.41x |
| Qwen3-8B | 12 | 554,700 | 46,516.4 | wafer-pipeline | 4,913.7 | wafer-tensor | 9.47x | 13,164.5 | pipeline | 3,453.4 | hybrid | 3.81x | 3.53x | 1.42x | 0.40x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.19x to 0.41x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x27-romfill | 22,005 | 19,448.8 | 19,448.8 | link_latency | Qwen3-8B/b200_sxm-x14-nvl72-tensor | 22,400 | 0.98x | tensor | 174.63 | 1,485.1 | 1,485.1 | kv_read | 13.10x | 10.04x | 140.60x | 13.10x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x16 | 13,040 | 16,514.4 | 16,514.4 | weight_read | Qwen3-8B/b200_sxm-x8-tensor | 12,800 | 1.02x | tensor | 174.52 | 959.5 | 959.5 | kv_read | 17.21x | 14.92x | 119.39x | 17.21x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139-romfill | 6,425,275 | 3,008.2 | 6,016.3 | link_latency | Qwen3-8B/b200_sxm-x4016-nvl72-hybrid | 6,425,600 | 1.00x | hybrid | 251.52 | 2,821.9 | 158,023.9 | link_latency | 1.07x | 0.01x | 21.75x | 1.20x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139-romfill | 6,425,275 | 2,896.9 | 11,587.6 | link_latency | Qwen3-8B/b200_sxm-x4016-nvl72-hybrid | 6,425,600 | 1.00x | hybrid | 251.52 | 2,821.9 | 158,023.9 | link_latency | 1.03x | 0.02x | 20.94x | 1.15x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | 6,425,275 | 2,697.4 | 21,578.8 | link_latency | Qwen3-8B/b200_sxm-x4016-nvl72-hybrid | 6,425,600 | 1.00x | hybrid | 251.52 | 2,821.9 | 158,023.9 | link_latency | 0.96x | 0.04x | 19.50x | 1.07x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | 6,425,275 | 2,370.7 | 37,931.9 | link_latency | Qwen3-8B/b200_sxm-x4016-nvl72-hybrid | 6,425,600 | 1.00x | hybrid | 251.52 | 2,821.9 | 158,023.9 | link_latency | 0.84x | 0.07x | 17.14x | 0.94x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | 6,425,275 | 1,908.5 | 61,073.5 | link_latency | Qwen3-8B/b200_sxm-x4016-nvl72-hybrid | 6,425,600 | 1.00x | hybrid | 251.52 | 2,821.9 | 158,023.9 | link_latency | 0.68x | 0.11x | 13.80x | 0.76x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | 6,425,275 | 1,373.1 | 87,880.8 | kv_read | Qwen3-8B/b200_sxm-x4016-nvl72-hybrid | 6,425,600 | 1.00x | hybrid | 252.62 | 2,743.2 | 175,564.3 | link_latency | 0.50x | 0.16x | 9.93x | 0.56x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill | 6,425,275 | 585.3 | 149,844.4 | kv_read | Qwen3-8B/b200_sxm-x4016-nvl72-hybrid | 6,425,600 | 1.00x | hybrid | 278.93 | 1,643.6 | 420,754.4 | link_latency | 0.36x | 0.27x | 4.23x | 0.39x |
| Qwen3-8B | 1024 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139 | 6,425,275 | 156.6 | 160,325.7 | kv_read | Qwen3-8B/b200_sxm-x4016-nvl72-hybrid | 6,425,600 | 1.00x | hybrid | 384.16 | 631.3 | 646,464.9 | kv_read | 0.25x | 0.25x | 1.13x | 0.26x |
| Qwen3-8B | 4096 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139 | 6,425,275 | 39.8 | 163,179.2 | kv_read | Qwen3-8B/b200_sxm-x4016-hybrid | 6,425,600 | 1.00x | hybrid | 304.68 | 190.6 | 780,892.6 | kv_read | 0.21x | 0.21x | 0.29x | 0.27x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 8 | 12,800 | 174.52 | 174.52 | 959.5 | 959.5 |
| Qwen3-8B | 9 | 14,400 | 174.55 | 174.55 | 1,056.4 | 1,056.4 |
| Qwen3-8B | 10 | 16,000 | 174.57 | 174.57 | 1,149.3 | 1,149.3 |
| Qwen3-8B | 12 | 19,200 | 174.60 | 174.60 | 1,323.9 | 1,323.9 |
| Qwen3-8B | 13 | 20,800 | 174.61 | 174.61 | 1,406.1 | 1,406.1 |
| Qwen3-8B | 14 | 22,400 | 174.63 | 174.63 | 1,485.1 | 1,485.1 |
| Qwen3-8B | 15 | 24,000 | 174.64 | 174.64 | 1,561.1 | 1,561.1 |
| Qwen3-8B | 23 | 36,800 | 174.68 | 174.68 | 2,079.3 | 2,079.3 |
| Qwen3-8B | 29 | 46,400 | 174.70 | 174.70 | 2,386.6 | 2,386.6 |
| Qwen3-8B | 31 | 49,600 | 174.70 | 174.70 | 2,477.2 | 2,477.2 |
| Qwen3-8B | 58 | 92,800 | 174.73 | 174.73 | 3,330.1 | 3,330.1 |
| Qwen3-8B | 87 | 139,200 | 176.93 | 176.93 | 2,923.3 | 2,923.3 |
| Qwen3-8B | 116 | 185,600 | 176.93 | 176.93 | 3,305.9 | 3,305.9 |
| Qwen3-8B | 173 | 276,800 | 179.13 | 179.13 | 3,274.7 | 3,274.7 |
| Qwen3-8B | 231 | 369,600 | 181.32 | 181.32 | 3,253.1 | 3,253.1 |
| Qwen3-8B | 347 | 555,200 | 183.51 | 183.51 | 3,453.4 | 3,453.4 |
| Qwen3-8B | 746 | 1,193,600 | 196.68 | 196.68 | 3,278.2 | 3,278.2 |
| Qwen3-8B | 4,016 | 6,425,600 | 251.52 | 251.52 | 2,821.9 | 2,821.9 |

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
| Qwen3-8B | 8 | 12,800 | 138.3 | 959.5 | — | tensor | 174.52 | 16.7% | kv_read |
| Qwen3-8B | 9 | 14,400 | 138.3 | 1,056.4 | 583.4 | tensor | 174.55 | 18.4% | kv_read |
| Qwen3-8B | 10 | 16,000 | 138.3 | 1,149.3 | 640.6 | tensor | 174.57 | 20.1% | kv_read |
| Qwen3-8B | 12 | 19,200 | 138.3 | 1,323.9 | 751.1 | tensor | 174.60 | 23.1% | kv_read |
| Qwen3-8B | 13 | 20,800 | 138.3 | 1,406.1 | 804.5 | tensor | 174.61 | 24.6% | kv_read |
| Qwen3-8B | 14 | 22,400 | 138.3 | 1,485.1 | 856.6 | tensor | 174.63 | 25.9% | kv_read |
| Qwen3-8B | 15 | 24,000 | 138.3 | 1,561.1 | 907.6 | tensor | 174.64 | 27.3% | kv_read |
| Qwen3-8B | 23 | 36,800 | 138.3 | 2,079.3 | 922.5 | tensor | 174.68 | 36.3% | kv_read |
| Qwen3-8B | 29 | 46,400 | 138.3 | 2,386.6 | 878.8 | tensor | 174.70 | 41.7% | link_latency |
| Qwen3-8B | 31 | 49,600 | 138.3 | 2,477.2 | 928.9 | tensor | 174.70 | 43.3% | link_latency |
| Qwen3-8B | 58 | 92,800 | 138.3 | 3,330.1 | 872.1 | tensor | 174.73 | 58.2% | link_latency |
| Qwen3-8B | 87 | 139,200 | 138.3 | 1,752.1 | 2,923.3 | hybrid | 176.93 | 51.7% | link_latency |
| Qwen3-8B | 116 | 185,600 | 138.3 | 1,815.1 | 3,305.9 | hybrid | 176.93 | 58.5% | link_latency |
| Qwen3-8B | 173 | 276,800 | 138.3 | 1,861.2 | 3,274.7 | hybrid | 179.13 | 58.7% | link_latency |
| Qwen3-8B | 231 | 369,600 | 138.3 | 1,886.0 | 3,253.1 | hybrid | 181.32 | 59.0% | link_latency |
| Qwen3-8B | 347 | 555,200 | 138.3 | 1,915.6 | 3,453.4 | hybrid | 183.51 | 63.4% | link_latency |
| Qwen3-8B | 746 | 1,193,600 | 138.3 | 1,940.7 | 3,278.2 | hybrid | 196.68 | 64.5% | link_latency |
| Qwen3-8B | 4016 | 6,425,600 | 138.3 | 1,959.4 | 2,821.9 | hybrid | 251.52 | 71.0% | link_latency |

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
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x16 | Qwen3-8B | 16 | pipeline | rom_package_ucie | rom_board_serdes | 15 | 0.46 us | 218,231.3 tok/s | 2,182,313.4 tok/s | 12 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.14 us; 3 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.31 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x16 | Qwen3-8B | 16 | tensor | rom_package_ucie | rom_board_serdes | 144 | 18.35 us | 5,449.9 tok/s | 54,498.7 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 72 x all_reduce span 4 on rom_board_serdes (traversals 2.2) = 16.58 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x16 | Qwen3-8B | 16 | hybrid | rom_package_ucie | rom_board_serdes | 75 | 2.09 us | 47,951.8 tok/s | 479,517.6 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 3 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.31 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x16 | Qwen3-8B | 16 | pipeline | nvlink5 | infiniband_ndr | 15 | 19.12 us | 5,229.8 tok/s | 52,297.8 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer_n5 | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x16 | Qwen3-8B | 16 | tensor | nvlink5 | infiniband_ndr | 144 | 484.54 us | 206.4 tok/s | 2,063.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hybrid-x16 | Qwen3-8B | 16 | hybrid | nvlink5 | infiniband_ndr | 73 | 176.71 us | 565.9 tok/s | 5,658.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x139 | Qwen3-8B | 139 | pipeline | on_wafer_n5 | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | Qwen3-8B | 139 | tensor | on_wafer_n5 | rom_wafer_serdes | 144 | 313.13 us | 319.4 tok/s | 3,193.5 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us; 72 x all_reduce span 139 on rom_wafer_serdes (traversals 24.2) = 174.53 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139 | Qwen3-8B | 139 | hybrid | on_wafer_n5 | rom_wafer_serdes | 107 | 142.15 us | 703.5 tok/s | 7,034.9 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us; 35 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 3.55 us |
| Qwen3-8B/b200_sxm-x8-pipeline | Qwen3-8B | 8 | pipeline | nvlink5 | infiniband_ndr | 7 | 8.46 us | 11,815.1 tok/s | 118,151.4 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.46 us |
| Qwen3-8B/b200_sxm-x8-tensor | Qwen3-8B | 8 | tensor | nvlink5 | infiniband_ndr | 72 | 174.52 us | 573.0 tok/s | 5,730.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us |
| Qwen3-8B/b200_sxm-x8-nvl72-tensor | Qwen3-8B | 8 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.52 us | 573.0 tok/s | 5,730.0 tok/s | 72 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 174.52 us |
| Qwen3-8B/b200_sxm-x9-pipeline | Qwen3-8B | 9 | pipeline | nvlink5 | infiniband_ndr | 8 | 10.66 us | 9,383.0 tok/s | 93,830.1 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.46 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x9-tensor | Qwen3-8B | 9 | tensor | nvlink5 | infiniband_ndr | 144 | 484.54 us | 206.4 tok/s | 2,063.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x9-hybrid | Qwen3-8B | 9 | hybrid | nvlink5 | infiniband_ndr | 73 | 176.71 us | 565.9 tok/s | 5,658.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x9-nvl72-tensor | Qwen3-8B | 9 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.55 us | 572.9 tok/s | 5,729.1 tok/s | 72 x all_reduce span 9 on nvlink5_nvl72 (traversals 2.0) = 174.55 us |
| Qwen3-8B/b200_sxm-x10-pipeline | Qwen3-8B | 10 | pipeline | nvlink5 | infiniband_ndr | 9 | 11.87 us | 8,427.0 tok/s | 84,269.7 tok/s | 8 x point_to_point span 2 on nvlink5 (traversals 1.0) = 9.67 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x10-tensor | Qwen3-8B | 10 | tensor | nvlink5 | infiniband_ndr | 144 | 484.54 us | 206.4 tok/s | 2,063.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x10-hybrid | Qwen3-8B | 10 | hybrid | nvlink5 | infiniband_ndr | 73 | 176.71 us | 565.9 tok/s | 5,658.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x10-nvl72-tensor | Qwen3-8B | 10 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.57 us | 572.8 tok/s | 5,728.4 tok/s | 72 x all_reduce span 10 on nvlink5_nvl72 (traversals 2.0) = 174.57 us |
| Qwen3-8B/b200_sxm-x12-pipeline | Qwen3-8B | 12 | pipeline | nvlink5 | infiniband_ndr | 11 | 14.28 us | 7,000.4 tok/s | 70,004.2 tok/s | 10 x point_to_point span 2 on nvlink5 (traversals 1.0) = 12.09 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x12-tensor | Qwen3-8B | 12 | tensor | nvlink5 | infiniband_ndr | 144 | 484.54 us | 206.4 tok/s | 2,063.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x12-hybrid | Qwen3-8B | 12 | hybrid | nvlink5 | infiniband_ndr | 73 | 176.71 us | 565.9 tok/s | 5,658.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x12-nvl72-tensor | Qwen3-8B | 12 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.60 us | 572.7 tok/s | 5,727.3 tok/s | 72 x all_reduce span 12 on nvlink5_nvl72 (traversals 2.0) = 174.60 us |
| Qwen3-8B/b200_sxm-x13-pipeline | Qwen3-8B | 13 | pipeline | nvlink5 | infiniband_ndr | 12 | 15.49 us | 6,454.1 tok/s | 64,541.3 tok/s | 11 x point_to_point span 2 on nvlink5 (traversals 1.0) = 13.30 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x13-tensor | Qwen3-8B | 13 | tensor | nvlink5 | infiniband_ndr | 144 | 484.54 us | 206.4 tok/s | 2,063.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x13-hybrid | Qwen3-8B | 13 | hybrid | nvlink5 | infiniband_ndr | 73 | 176.71 us | 565.9 tok/s | 5,658.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x13-nvl72-tensor | Qwen3-8B | 13 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.61 us | 572.7 tok/s | 5,726.9 tok/s | 72 x all_reduce span 13 on nvlink5_nvl72 (traversals 2.0) = 174.61 us |
| Qwen3-8B/b200_sxm-x14-pipeline | Qwen3-8B | 14 | pipeline | nvlink5 | infiniband_ndr | 13 | 16.70 us | 5,986.9 tok/s | 59,869.2 tok/s | 12 x point_to_point span 2 on nvlink5 (traversals 1.0) = 14.51 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x14-tensor | Qwen3-8B | 14 | tensor | nvlink5 | infiniband_ndr | 144 | 484.54 us | 206.4 tok/s | 2,063.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x14-hybrid | Qwen3-8B | 14 | hybrid | nvlink5 | infiniband_ndr | 73 | 176.71 us | 565.9 tok/s | 5,658.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x14-nvl72-tensor | Qwen3-8B | 14 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.63 us | 572.7 tok/s | 5,726.5 tok/s | 72 x all_reduce span 14 on nvlink5_nvl72 (traversals 2.0) = 174.63 us |
| Qwen3-8B/b200_sxm-x15-pipeline | Qwen3-8B | 15 | pipeline | nvlink5 | infiniband_ndr | 14 | 17.91 us | 5,582.8 tok/s | 55,828.0 tok/s | 13 x point_to_point span 2 on nvlink5 (traversals 1.0) = 15.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x15-tensor | Qwen3-8B | 15 | tensor | nvlink5 | infiniband_ndr | 144 | 484.54 us | 206.4 tok/s | 2,063.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x15-hybrid | Qwen3-8B | 15 | hybrid | nvlink5 | infiniband_ndr | 73 | 176.71 us | 565.9 tok/s | 5,658.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x15-nvl72-tensor | Qwen3-8B | 15 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.64 us | 572.6 tok/s | 5,726.2 tok/s | 72 x all_reduce span 15 on nvlink5_nvl72 (traversals 2.0) = 174.64 us |
| Qwen3-8B/b200_sxm-x23-pipeline | Qwen3-8B | 23 | pipeline | nvlink5 | infiniband_ndr | 22 | 28.57 us | 3,500.2 tok/s | 35,002.1 tok/s | 20 x point_to_point span 2 on nvlink5 (traversals 1.0) = 24.18 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| Qwen3-8B/b200_sxm-x23-tensor | Qwen3-8B | 23 | tensor | nvlink5 | infiniband_ndr | 144 | 490.43 us | 203.9 tok/s | 2,039.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 315.91 us |
| Qwen3-8B/b200_sxm-x23-hybrid | Qwen3-8B | 23 | hybrid | nvlink5 | infiniband_ndr | 74 | 178.91 us | 558.9 tok/s | 5,589.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| Qwen3-8B/b200_sxm-x23-nvl72-tensor | Qwen3-8B | 23 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.68 us | 572.5 tok/s | 5,724.7 tok/s | 72 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 174.68 us |
| Qwen3-8B/b200_sxm-x29-pipeline | Qwen3-8B | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x29-tensor | Qwen3-8B | 29 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x29-hybrid | Qwen3-8B | 29 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x29-nvl72-tensor | Qwen3-8B | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.70 us | 572.4 tok/s | 5,724.2 tok/s | 72 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 174.70 us |
| Qwen3-8B/b200_sxm-x31-pipeline | Qwen3-8B | 31 | pipeline | nvlink5 | infiniband_ndr | 30 | 39.23 us | 2,549.2 tok/s | 25,492.5 tok/s | 27 x point_to_point span 2 on nvlink5 (traversals 1.0) = 32.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x31-tensor | Qwen3-8B | 31 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x31-hybrid | Qwen3-8B | 31 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x31-nvl72-tensor | Qwen3-8B | 31 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.70 us | 572.4 tok/s | 5,724.0 tok/s | 72 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 174.70 us |
| Qwen3-8B/b200_sxm-x58-pipeline | Qwen3-8B | 58 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x58-tensor | Qwen3-8B | 58 | tensor | nvlink5 | infiniband_ndr | 144 | 497.81 us | 200.9 tok/s | 2,008.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 323.29 us |
| Qwen3-8B/b200_sxm-x58-hybrid | Qwen3-8B | 58 | hybrid | nvlink5 | infiniband_ndr | 79 | 189.88 us | 526.7 tok/s | 5,266.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| Qwen3-8B/b200_sxm-x58-nvl72-tensor | Qwen3-8B | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.73 us | 572.3 tok/s | 5,723.0 tok/s | 72 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 174.73 us |
| Qwen3-8B/b200_sxm-x87-pipeline | Qwen3-8B | 87 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x87-tensor | Qwen3-8B | 87 | tensor | nvlink5 | infiniband_ndr | 144 | 499.01 us | 200.4 tok/s | 2,004.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 324.49 us |
| Qwen3-8B/b200_sxm-x87-hybrid | Qwen3-8B | 87 | hybrid | nvlink5 | infiniband_ndr | 82 | 196.46 us | 509.0 tok/s | 5,090.1 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| Qwen3-8B/b200_sxm-x87-nvl72-tensor | Qwen3-8B | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x87-nvl72-hybrid | Qwen3-8B | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x116-pipeline | Qwen3-8B | 116 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x116-tensor | Qwen3-8B | 116 | tensor | nvlink5 | infiniband_ndr | 144 | 499.87 us | 200.1 tok/s | 2,000.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 325.35 us |
| Qwen3-8B/b200_sxm-x116-hybrid | Qwen3-8B | 116 | hybrid | nvlink5 | infiniband_ndr | 86 | 205.23 us | 487.2 tok/s | 4,872.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| Qwen3-8B/b200_sxm-x116-nvl72-tensor | Qwen3-8B | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x116-nvl72-hybrid | Qwen3-8B | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x173-pipeline | Qwen3-8B | 173 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x173-tensor | Qwen3-8B | 173 | tensor | nvlink5 | infiniband_ndr | 144 | 500.62 us | 199.8 tok/s | 1,997.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 326.10 us |
| Qwen3-8B/b200_sxm-x173-hybrid | Qwen3-8B | 173 | hybrid | nvlink5 | infiniband_ndr | 93 | 220.59 us | 453.3 tok/s | 4,533.3 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| Qwen3-8B/b200_sxm-x173-nvl72-tensor | Qwen3-8B | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 490.65 us | 203.8 tok/s | 2,038.1 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 315.91 us |
| Qwen3-8B/b200_sxm-x173-nvl72-hybrid | Qwen3-8B | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 74 | 179.13 us | 558.3 tok/s | 5,582.6 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| Qwen3-8B/b200_sxm-x231-pipeline | Qwen3-8B | 231 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x231-tensor | Qwen3-8B | 231 | tensor | nvlink5 | infiniband_ndr | 144 | 501.01 us | 199.6 tok/s | 1,996.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 326.49 us |
| Qwen3-8B/b200_sxm-x231-hybrid | Qwen3-8B | 231 | hybrid | nvlink5 | infiniband_ndr | 100 | 235.95 us | 423.8 tok/s | 4,238.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 61.43 us |
| Qwen3-8B/b200_sxm-x231-nvl72-tensor | Qwen3-8B | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 493.60 us | 202.6 tok/s | 2,025.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x231-nvl72-hybrid | Qwen3-8B | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 75 | 181.32 us | 551.5 tok/s | 5,515.1 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x347-pipeline | Qwen3-8B | 347 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x347-tensor | Qwen3-8B | 347 | tensor | nvlink5 | infiniband_ndr | 144 | 501.43 us | 199.4 tok/s | 1,994.3 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 326.91 us |
| Qwen3-8B/b200_sxm-x347-hybrid | Qwen3-8B | 347 | hybrid | nvlink5 | infiniband_ndr | 107 | 251.30 us | 397.9 tok/s | 3,979.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 35 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 76.78 us |
| Qwen3-8B/b200_sxm-x347-nvl72-tensor | Qwen3-8B | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 495.37 us | 201.9 tok/s | 2,018.7 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 320.63 us |
| Qwen3-8B/b200_sxm-x347-nvl72-hybrid | Qwen3-8B | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 76 | 183.51 us | 544.9 tok/s | 5,449.2 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x746-pipeline | Qwen3-8B | 746 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x746-tensor | Qwen3-8B | 746 | tensor | nvlink5 | infiniband_ndr | 144 | 794.17 us | 125.9 tok/s | 1,259.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 94 on infiniband_ndr (traversals 4.0) = 619.65 us |
| Qwen3-8B/b200_sxm-x746-hybrid | Qwen3-8B | 746 | hybrid | nvlink5 | infiniband_ndr | 107 | 251.30 us | 397.9 tok/s | 3,979.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 35 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 76.78 us |
| Qwen3-8B/b200_sxm-x746-nvl72-tensor | Qwen3-8B | 746 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 499.23 us | 200.3 tok/s | 2,003.1 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 324.49 us |
| Qwen3-8B/b200_sxm-x746-nvl72-hybrid | Qwen3-8B | 746 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 196.68 us | 508.4 tok/s | 5,084.5 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| Qwen3-8B/b200_sxm-x4016-pipeline | Qwen3-8B | 4016 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x4016-tensor | Qwen3-8B | 4016 | tensor | nvlink5 | infiniband_ndr | 144 | 794.48 us | 125.9 tok/s | 1,258.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 502 on infiniband_ndr (traversals 4.0) = 619.96 us |
| Qwen3-8B/b200_sxm-x4016-hybrid | Qwen3-8B | 4016 | hybrid | nvlink5 | infiniband_ndr | 107 | 251.30 us | 397.9 tok/s | 3,979.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 35 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 76.78 us |
| Qwen3-8B/b200_sxm-x4016-nvl72-tensor | Qwen3-8B | 4016 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 501.82 us | 199.3 tok/s | 1,992.8 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 56 on infiniband_ndr (traversals 2.0) = 327.08 us |
| Qwen3-8B/b200_sxm-x4016-nvl72-hybrid | Qwen3-8B | 4016 | hybrid | nvlink5_nvl72 | infiniband_ndr | 107 | 251.52 us | 397.6 tok/s | 3,975.8 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 35 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 76.78 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | array | array | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x26-romfill | 21,190 | 19,208.3 | 0.906 | 19,208.3 (21,190) | 6,464.4 (46,225) | 0.34x | link_latency |
| Qwen3-8B | 2 | wafer | wafer | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139-romfill | 6,425,275 | 3,008.2 | 0.000 | — (—) | 3,008.2 (6,425,275) | — | link_latency |
| Qwen3-8B | 4 | wafer | wafer | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139-romfill | 6,425,275 | 2,896.9 | 0.000 | — (—) | 2,896.9 (6,425,275) | — | link_latency |
| Qwen3-8B | 8 | wafer | wafer | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | 6,425,275 | 2,697.4 | 0.000 | — (—) | 2,697.4 (6,425,275) | — | link_latency |
| Qwen3-8B | 16 | wafer | wafer | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | 6,425,275 | 2,370.7 | 0.000 | — (—) | 2,370.7 (6,425,275) | — | link_latency |
| Qwen3-8B | 32 | wafer | wafer | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | 6,425,275 | 1,908.5 | 0.000 | — (—) | 1,908.5 (6,425,275) | — | link_latency |
| Qwen3-8B | 64 | wafer | wafer | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | 6,425,275 | 1,373.1 | 0.000 | — (—) | 1,373.1 (6,425,275) | — | kv_read |
| Qwen3-8B | 256 | wafer | wafer | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill | 6,425,275 | 585.3 | 0.000 | — (—) | 585.3 (6,425,275) | — | kv_read |
| Qwen3-8B | 1024 | wafer | wafer | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139 | 6,425,275 | 156.6 | 0.000 | — (—) | 156.6 (6,425,275) | — | kv_read |
| Qwen3-8B | 4096 | wafer | wafer | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139 | 6,425,275 | 39.8 | 0.000 | — (—) | 39.8 (6,425,275) | — | kv_read |

## The two ROM floorplans on one die

This probe requests 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. The ROM-plus-MAC floorplan holds the requested weights; the compute-in-ROM floorplan holds only 100.0% and is infeasible at this area. The failed floorplan is retained so the capacity cost of the larger cell remains visible.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 374.6 mm2 | 199.8 mm2 |
| weight capacity | 3.51 GB (100.0%) | 3.51 GB (100.0%) |
| capacity-feasible | yes | **no** |
| compute block | 293.7 mm2 | 146.7 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 321.8 mm2 |
| sustained fp8 compute roof | 2.197e+14 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 1.098e+14 | n/a |
| weight bytes/s the array supplies | 1.019e+14 | 1.019e+14 |
| **can the compute block be fed?** | **0.93x** | there is nothing to feed |
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

The ROM-plus-MAC machine is bandwidth-starved: its array supplies
only 0.93x of the bytes its MAC roof wants,
so some compute capacity cannot be exercised.

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
| Qwen3-8B | 1 | sram | 27,429.6 | 25,402.3 | 25,402.3 | 1.08x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 27,429.6 | 25,402.3 | 25,402.3 | 1.08x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 27,429.6 | 25,402.3 | 25,402.3 | 1.08x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 27,429.6 | 25,402.3 | 25,402.3 | 1.08x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 37,931.9 | 25,402.3 | 25,402.3 | 1.49x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 61,073.5 | 25,402.3 | 25,402.3 | 2.40x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 87,880.8 | 25,402.3 | 25,402.3 | 3.46x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 131,009.2 | 25,722.2 | 25,722.2 | 5.09x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 1024 | sram | 160,325.7 | 26,014.1 | 26,014.1 | 6.16x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 4096 | sram | 163,179.2 | 26,088.2 | 26,088.2 | 6.25x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 1 | rom | 139,601.8 | 139,601.8 | 139,601.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 139,601.8 | 139,601.8 | 139,601.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 139,601.8 | 139,601.8 | 139,601.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 139,601.8 | 139,601.8 | 139,601.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 139,601.8 | 139,601.8 | 139,601.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 139,601.8 | 139,601.8 | 139,601.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 139,601.8 | 139,601.8 | 139,601.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 149,844.4 | 149,844.4 | 149,844.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 1024 | rom | 160,325.7 | 160,325.7 | 160,325.7 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4096 | rom | 163,179.2 | 163,179.2 | 163,179.2 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139 | 6,425,275 | 1.00 | 1.00 | 27,429.6 | 0.004 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill | 6,425,275 | 1,726.21 | 1.00 | 139,601.8 | 0.022 | kv_read | 5.09x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.93x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 5.09x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.93x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 5.09x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139 | 6,425,275 | 1.00 | 1.00 | 27,429.6 | 0.004 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill | 6,425,275 | 1,726.21 | 1.00 | 139,601.8 | 0.022 | kv_read | 5.09x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.93x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 5.09x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.93x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 5.09x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139 | 6,425,275 | 1.00 | 1.00 | 27,429.6 | 0.004 | weight_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill | 6,425,275 | 1,726.21 | 1.00 | 139,601.8 | 0.022 | kv_read | 5.09x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.93x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 5.09x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.93x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 5.09x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139 | 6,425,275 | 1.00 | 1.00 | 27,429.6 | 0.004 | weight_read | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill | 6,425,275 | 1,726.21 | 1.00 | 139,601.8 | 0.022 | kv_read | 5.09x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.93x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 5.09x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.93x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 5.09x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | 6,425,275 | 1.00 | 1.00 | 37,931.9 | 0.006 | link_latency | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill | 6,425,275 | 1,726.21 | 1.00 | 139,601.8 | 0.022 | kv_read | 3.68x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.67x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 3.68x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.67x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 3.68x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | 6,425,275 | 1.00 | 1.00 | 61,073.5 | 0.010 | link_latency | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill | 6,425,275 | 1,726.21 | 1.00 | 139,601.8 | 0.022 | kv_read | 2.29x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.42x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 2.29x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.42x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 2.29x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | 6,425,275 | 1.00 | 1.00 | 87,880.8 | 0.014 | kv_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill | 6,425,275 | 1,726.21 | 1.00 | 139,601.8 | 0.022 | kv_read | 1.59x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.29x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 1.59x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion | 6,425,275 | 1.00 | 1.00 | 25,402.3 | 0.004 | weight_read | 0.29x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion-romfill | 6,425,275 | 5,800.70 | 1.00 | 139,601.8 | 0.022 | kv_read | 1.59x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x139 | 6,425,275 | 1.00 | 1.00 | 131,009.2 | 0.020 | kv_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill | 6,425,275 | 1,726.21 | 1.00 | 149,844.4 | 0.023 | kv_read | 1.14x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream | 6,425,275 | 1.00 | 1.84 | 25,722.2 | 0.004 | weight_read | 0.20x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream-romfill | 6,425,275 | 5,800.70 | 1.84 | 149,844.4 | 0.023 | kv_read | 1.14x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion | 6,425,275 | 1.00 | 1.84 | 25,722.2 | 0.004 | weight_read | 0.20x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion-romfill | 6,425,275 | 5,800.70 | 1.84 | 149,844.4 | 0.023 | kv_read | 1.14x |
| Qwen3-8B | 1024 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139 | 6,425,275 | 1.00 | 1.00 | 160,325.7 | 0.025 | kv_read | 1.00x |
| Qwen3-8B | 1024 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill | 6,425,275 | 1,726.21 | 1.00 | 160,325.7 | 0.025 | kv_read | 1.00x |
| Qwen3-8B | 1024 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream | 6,425,275 | 1.00 | 7.37 | 26,014.1 | 0.004 | weight_read | 0.16x |
| Qwen3-8B | 1024 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream-romfill | 6,425,275 | 5,800.70 | 7.37 | 160,325.7 | 0.025 | kv_read | 1.00x |
| Qwen3-8B | 1024 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion | 6,425,275 | 1.00 | 7.37 | 26,014.1 | 0.004 | weight_read | 0.16x |
| Qwen3-8B | 1024 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion-romfill | 6,425,275 | 5,800.70 | 7.37 | 160,325.7 | 0.025 | kv_read | 1.00x |
| Qwen3-8B | 4096 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139 | 6,425,275 | 1.00 | 1.00 | 163,179.2 | 0.025 | kv_read | 1.00x |
| Qwen3-8B | 4096 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-romfill | 6,425,275 | 1,726.21 | 1.00 | 163,179.2 | 0.025 | kv_read | 1.00x |
| Qwen3-8B | 4096 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream | 6,425,275 | 1.00 | 29.47 | 26,088.2 | 0.004 | weight_read | 0.16x |
| Qwen3-8B | 4096 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perstream-romfill | 6,425,275 | 5,800.70 | 29.47 | 163,179.2 | 0.025 | kv_read | 1.00x |
| Qwen3-8B | 4096 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion | 6,425,275 | 1.00 | 29.47 | 26,088.2 | 0.004 | weight_read | 0.16x |
| Qwen3-8B | 4096 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x139-perregion-romfill | 6,425,275 | 5,800.70 | 29.47 | 163,179.2 | 0.025 | kv_read | 1.00x |

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
| Qwen3-8B | 1 | 16 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4 | 7,884 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 8 | 7,884 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 16 | 7,884 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 32 | 7,884 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 64 | 7,884 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 256 | 7,884 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 1024 | 7,884 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4096 | 7,884 | 1.00 | 1.000 | 1.000 | 1.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|

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
| gpu | Qwen3-8B | 1 | 6.82 | 2.4% |
| rom | Qwen3-8B | 1 | 6.82 | 13.3% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| Qwen3-8B | sram | interleaved | 128 B | 1.00x |
| Qwen3-8B | hbm | interleaved | 32 B | 1.00x |

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
| Qwen3-8B | 1 | 16 | 99.68% | 147.90 | 9.27 |
| Qwen3-8B | 2 | 1 | 26.39% | 139.49 | 9.27 |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 3.6 | 14,710.3 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 3.6 | 14,710.3 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 3.6 | 14,710.3 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 3.6 | 14,710.3 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 3.6 | 14,710.3 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 3.6 | 14,710.3 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 3.6 | 14,710.3 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 3.6 | 14,710.3 |
| Qwen3-8B | 1024 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 3.6 | 14,710.3 |
| Qwen3-8B | 4096 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 3.6 | 14,710.3 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 176 |
| gpu | kv_read | 233 |
| gpu | link_latency | 169 |
| gpu | thermal | 202 |
| rom | compute | 6 |
| rom | infeasible | 2102 |
| rom | kv_read | 122 |
| rom | link_latency | 142 |
| rom | weight_read | 148 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 176 |
| rom | CAPACITY | 2102 |

## Mechanical consistency audit

**FAIL** over 39,489 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x19', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x23', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x30', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x45', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x60', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x19', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x23', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x30', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x45', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x60', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x19', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x23', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x30', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x45', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x60', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x19', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x23', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x30', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x45', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x60', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x2', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x3', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x4', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x8', 'Qwen3-8B', 1)

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

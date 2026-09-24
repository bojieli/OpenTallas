# Area-constrained roofline: n5_vs_b200-mimo-v26-pro-1m

> CANDIDATE MODEL under n5_vs_b200: MiMo-V2.6-Pro at 1,000,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 8,384x (ROM-N5-native-HBMKV-wafer-pipeline-x242-perstream, 13,726 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 91 devices. On the GPU side the correction reaches 128x (b200_sxm-x6992-pipeline, 6,992 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 71 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Pro takes 139 x 815 mm2 (113,285 mm2, array, KV in SRAM) at 4,434 tok/s per user and 39 tok/s per 1,000 mm2, holding 1 session, against 71 copies of one unified HBM die at the same silicon: 2.5x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Pro on 123,880 mm2 of ROM silicon at 4,148 tok/s per user against 123,200 mm2 of b200_sxm-x77-nvl72-hybrid at 1,383 tok/s: **3.0x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 232. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 11,186,450 mm2 on MiMo-V2.6-Pro at batch 1, the iso-area GPU cluster is 6,992 devices. Cut as one serial pipeline that is 98 stages and 562 us of link latency per token; but the model has 70 layers, so at most 70 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 499 us. The iso-area per-user ratio at that point falls from 1.0x to 0.9x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
6. **Letting the GPU choose its own parallelism is worth up to 27.34x to it.** At 114,915 mm2 on MiMo-V2.6-Pro the pipeline-only GPU delivers 66.31 tok/s and the same silicon running tensor delivers 1,813 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.07x (MiMo-V2.6-Pro, ROM binding on `kv_read`) to 0.25x (MiMo-V2.6-Pro, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Pro engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 12 to 49,074 tok/s, and its rate with every slot occupied from 49,266 to 49,266. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 13,726 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,581 us over NVLink, capping per-user decode at 633 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 732.4 us and cap it at 1,365 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 9 of 10 operating points and an array 1; on tokens per second per square millimetre the same points go 1 to the array and 9 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 567 of 1921 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 6.2x of aggregate throughput (MiMo-V2.6-Pro). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 5.64x, on MiMo-V2.6-Pro at batch 4096, where the busiest region carries 3.16x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 10 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 296 of 1,921 feasible points (15.4%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `MiMo-V2.6-Pro/b200_sxm-x1300-pipeline` at batch 4096 on 2,080,000 mm2, throttled 1.08x from 29 to 27 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 69% kv read against 26.8% weight read. The ROM sweep is not what melts it.


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

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x139`** -- 139 x 815 mm2 reticle dies, 113,285 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **4,433.8 tok/s per user** (0.23 ms/token), binding on `link_latency`
- **39.1 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,434 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 8,018 W at 0.071 W/mm2, 1,808.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 71 copies of one unified HBM die -- `b200_sxm-x71-nvl72-tensor`, 113,600 mm2, area ratio 0.9972 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 113,285 | 113,600 | 0.9972 |
| user tok/s | 4,433.8 | 1,804.0 | 2.46x |
| aggregate tok/s | 4,434 | 1,804 | 0.94x |
| resident sessions | 1 | 213 | -- |
| J/token | 1.8083 | 23.5878 | 13.0x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 213 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x72-nvl72-tensor` at 115,200 mm2 and 1,812.9 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-tensor-x139` | 113,285 | 4,433.8 | 39.1 | 1 | 2.46x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-array-hw-tensor-x141` | 114,915 | 4,497.3 | 39.1 | 1 | 2.48x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x113` | 92,095 | 1,494.8 | 16.2 | 1 | 0.89x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x139` | 113,285 | 4,433.8 | 39.1 | 1 | 2.46x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x139` | 113,285 | 4,433.8 | 39.1 | -- | 39.1 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x141` | 114,915 | 4,497.3 | 39.1 | 38.9 | 39.1 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x139` **<-- recommended** | 113,285 | 139 | 4,433.8 | 4,434 | 39.1 | 1 | `link_latency` | 8,018 | 1,808.3 | `b200_sxm-x71-nvl72-tensor` | 2.46x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x141` | 114,915 | 141 | 4,497.3 | 4,497 | 39.1 | 1 | `link_latency` | 8,266 | 1,838.1 | `b200_sxm-x72-nvl72-tensor` | 2.48x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 162 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x139` | 113,285 | 4,433.8 | 39.1 | 1 |
| array | 162 | fastest | `ROM-N5-native-SRAMKV-array-hw-tensor-x141` | 114,915 | 4,497.3 | 39.1 | 1 |
| array | 162 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x113` | 92,095 | 1,494.8 | 16.2 | 1 |
| wafer | 45 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x3` | 138,675 | 2,938.3 | 21.2 | 1 |
| wafer | 45 | fastest | `ROM-N5-native-SRAMKV-wafer-tensor-x4` | 184,900 | 3,040.3 | 16.4 | 1 |
| wafer | 45 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x2` | 92,450 | 1,343.1 | 14.5 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-tensor-x141` | 114,915 | 4,497.3 | 4,497 | 1 | 8,266 | 1,838.1 | `link_latency` | `b200_sxm-x72-nvl72-tensor` | 1,812.9 | 216 | 23,713.1 | 0.998 | 2.48x | 12.9x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-tensor-x4` | 184,900 | 3,040.3 | 3,040 | 1 | 18,134 | 5,964.4 | `link_latency` | `b200_sxm-x116-nvl72-hybrid` | 1,664.6 | 355 | 34,215.9 | 0.996 | 1.83x | 5.7x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-tensor-x232` | 189,080 | 4,005.8 | 4,006 | 1 | 18,926 | 4,724.6 | `link_latency` | `b200_sxm-x118-nvl72-hybrid` | 1,676.0 | 362 | 34,468.0 | 1.001 | 2.39x | 7.3x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-tensor-x4` | 184,900 | 3,040.3 | -- | 1 | -- | 5,964.4 | -- | -- | -- | -- | -- | 1.023 | 0.76x wafer/array | -- |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x242` | 11,186,450 | 1,313.8 | 2,628 | 4,112 | 1,657,860 | 630,956.8 | `link_latency` | `b200_sxm-x6992-nvl72-hybrid` | 1,407.7 | 22,095 | 880,136.9 | 1.000 | 0.93x | 1.4x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x242` | 11,186,450 | 1,290.3 | 5,161 | 4,112 | 1,671,602 | 323,890.4 | `link_latency` | `b200_sxm-x6992-nvl72-hybrid` | 1,407.7 | 22,095 | 444,966.1 | 1.000 | 0.92x | 1.4x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x242` | 11,186,450 | 1,245.7 | 9,965 | 4,112 | 1,697,661 | 170,357.1 | `link_latency` | `b200_sxm-x6992-nvl72-hybrid` | 1,407.7 | 22,095 | 227,380.7 | 1.000 | 0.88x | 1.3x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x242` | 11,186,450 | 1,165.1 | 18,642 | 4,112 | 1,744,720 | 93,590.3 | `link_latency` | `b200_sxm-x6992-nvl72-hybrid` | 1,407.7 | 22,095 | 118,588.0 | 1.000 | 0.83x | 1.3x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x242` | 11,186,450 | 1,031.7 | 33,015 | 4,112 | 1,822,666 | 55,206.6 | `link_latency` | `b200_sxm-x6992-nvl72-hybrid` | 1,407.7 | 22,095 | 64,191.7 | 1.000 | 0.73x | 1.2x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x242` | 11,186,450 | 839.5 | 53,728 | 4,112 | 1,934,965 | 36,014.3 | `link_latency` | `b200_sxm-x6992-nvl72-hybrid` | 1,407.7 | 22,095 | 36,993.5 | 1.000 | 0.60x | 1.0x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 11,186,450 | 541.0 | 138,484 | 4,112 | 2,395,941 | 17,301.2 | `kv_read` | `b200_sxm-x6992-nvl72-hybrid` | 1,038.3 | 22,095 | 17,160.1 | 1.000 | 0.52x | 1.0x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 11,186,450 | 153.4 | 157,109 | 4,112 | 2,496,136 | 15,887.9 | `kv_read` | `b200_sxm-x6992-nvl72-hybrid` | 459.9 | 22,095 | 12,202.9 | 1.000 | 0.33x | 0.7x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 11,186,450 | 39.7 | 162,575 | 4,112 | 2,525,482 | 15,534.2 | `kv_read` | `b200_sxm-x6992-nvl72-expert` | 161.5 | 22,042 | 9,378.9 | 1.000 | 0.25x | 0.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x139` | 113,285 | array | SRAM | 1 |
| 2-64 | `ROM-N5-native-HBMKV-wafer-tensor-x242` | 11,186,450 | wafer | HBM | 4,112 |
| 256-4096 | `ROM-N5-native-HBMKV-wafer-hybrid-x242` | 11,186,450 | wafer | HBM | 4,112 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Pro | SRAM | rom | 113, 139, 141, 152, 167, 170, 174, 222, 227, 260, 261, 262, 333, 340 |
| MiMo-V2.6-Pro | SRAM | sram | 113, 139, 141, 154, 167, 170, 222, 227, 232, 242, 243, 333, 340 |

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

- **296 of 1,921 feasible points (15.4%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 296.
- By area class: wafer (>=40,000 mm2) 296.
- By KV store: hbm 296.
- By batch: B=1 27, B=2 27, B=4 27, B=8 27, B=16 30, B=32 38, B=64 61, B=256 49, B=1024 6, B=4096 4.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 45% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 1,432 | 296 | 75.6% | 100.0% | 0.625 | 46% |
| rom | wafer (>=40,000 mm2) | 489 | 0 | 16.1% | 45.2% | 0.226 | 96% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `MiMo-V2.6-Pro/b200_sxm-x1300-pipeline` | MiMo-V2.6-Pro | 4096 | 2,080,000 | hbm | 1.084x | 1,300,000.0 / 1,300,000.0 W | 35% | 26.6 | 28.9 |
| `MiMo-V2.6-Pro/b200_sxm-x85-pipeline` | MiMo-V2.6-Pro | 256 | 136,000 | hbm | 1.083x | 85,000.0 / 85,000.0 W | 35% | 27.7 | 30.0 |
| `MiMo-V2.6-Pro/b200_sxm-x347-pipeline` | MiMo-V2.6-Pro | 1024 | 555,200 | hbm | 1.083x | 347,000.0 / 347,000.0 W | 35% | 28.2 | 30.5 |
| `MiMo-V2.6-Pro/b200_sxm-x87-pipeline` | MiMo-V2.6-Pro | 256 | 139,200 | hbm | 1.083x | 87,000.0 / 87,000.0 W | 35% | 28.3 | 30.6 |
| `MiMo-V2.6-Pro/b200_sxm-x88-pipeline` | MiMo-V2.6-Pro | 256 | 140,800 | hbm | 1.083x | 88,000.0 / 88,000.0 W | 35% | 28.5 | 30.9 |
| `MiMo-V2.6-Pro/b200_sxm-x89-pipeline` | MiMo-V2.6-Pro | 256 | 142,400 | hbm | 1.083x | 89,000.0 / 89,000.0 W | 35% | 28.8 | 31.2 |
| `MiMo-V2.6-Pro/b200_sxm-x29-pipeline` | MiMo-V2.6-Pro | 64 | 46,400 | hbm | 1.083x | 29,000.0 / 29,000.0 W | 35% | 36.1 | 39.1 |
| `MiMo-V2.6-Pro/b200_sxm-x113-pipeline` | MiMo-V2.6-Pro | 256 | 180,800 | hbm | 1.081x | 113,000.0 / 113,000.0 W | 35% | 35.3 | 38.2 |
| `MiMo-V2.6-Pro/b200_sxm-x116-pipeline` | MiMo-V2.6-Pro | 256 | 185,600 | hbm | 1.080x | 116,000.0 / 116,000.0 W | 35% | 36.1 | 39.0 |
| `MiMo-V2.6-Pro/b200_sxm-x118-pipeline` | MiMo-V2.6-Pro | 256 | 188,800 | hbm | 1.080x | 118,000.0 / 118,000.0 W | 35% | 36.6 | 39.5 |
| `MiMo-V2.6-Pro/b200_sxm-x37-pipeline` | MiMo-V2.6-Pro | 64 | 59,200 | hbm | 1.080x | 37,000.0 / 37,000.0 W | 35% | 44.0 | 47.5 |
| `MiMo-V2.6-Pro/b200_sxm-x123-pipeline` | MiMo-V2.6-Pro | 256 | 196,800 | hbm | 1.080x | 123,000.0 / 123,000.0 W | 35% | 37.9 | 40.9 |

The worst point's dynamic energy is kv read 69.4%, weight read 26.8%, arithmetic 3.5%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| MiMo-V2.6-Pro | 1 | 113,285 | `MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x139` | 1.808335 | 8,017.8 | link_latency | `MiMo-V2.6-Pro/b200_sxm-x71-nvl72-tensor` | 23.587804 | 42,551.8 | link_latency | 13.04x |
| MiMo-V2.6-Pro | 2 | 11,186,450 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242` | 630.956808 | 1,657,859.9 | link_latency | `MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid` | 880.136922 | 3,801,543.8 | link_latency | 1.39x |
| MiMo-V2.6-Pro | 4 | 11,186,450 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242` | 323.890429 | 1,671,602.0 | link_latency | `MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid` | 444.966135 | 3,801,543.8 | link_latency | 1.37x |
| MiMo-V2.6-Pro | 8 | 11,186,450 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242` | 170.357140 | 1,697,660.6 | link_latency | `MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid` | 227.380741 | 3,801,543.8 | link_latency | 1.33x |
| MiMo-V2.6-Pro | 16 | 11,186,450 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242` | 93.590316 | 1,744,720.4 | link_latency | `MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid` | 118.588044 | 3,801,543.8 | link_latency | 1.27x |
| MiMo-V2.6-Pro | 32 | 11,186,450 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242` | 55.206606 | 1,822,665.8 | link_latency | `MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid` | 64.191696 | 3,801,543.8 | link_latency | 1.16x |
| MiMo-V2.6-Pro | 64 | 11,186,450 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242` | 36.014343 | 1,934,965.4 | link_latency | `MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid` | 36.993521 | 3,801,543.8 | link_latency | 1.03x |
| MiMo-V2.6-Pro | 256 | 11,186,450 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242` | 17.301239 | 2,395,940.6 | kv_read | `MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid` | 17.160107 | 4,561,295.7 | link_latency | 0.99x |
| MiMo-V2.6-Pro | 1024 | 11,186,450 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242` | 15.887939 | 2,496,136.0 | kv_read | `MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid` | 12.202904 | 5,747,032.0 | kv_read | 0.72x |
| MiMo-V2.6-Pro | 4096 | 11,186,450 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242` | 15.534240 | 2,525,481.7 | kv_read | `MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-expert` | 9.378898 | 6,203,877.2 | kv_read | 0.60x |

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
| MiMo-V2.6-Pro | 2 | 92,450 | 2,210.3 | wafer-pipeline | 1,343.1 | wafer-tensor | 1.65x | 2,798.5 | pipeline | 1,671.0 | tensor | 1.67x | 0.79x | 0.80x | 1.02x |
| MiMo-V2.6-Pro | 3 | 138,675 | 20,805.1 | wafer-pipeline | 2,938.3 | wafer-tensor | 7.08x | 3,476.3 | pipeline | 1,468.3 | hybrid | 2.37x | 5.98x | 2.00x | 0.33x |
| MiMo-V2.6-Pro | 4 | 184,900 | 27,345.4 | wafer-pipeline | 3,040.3 | wafer-tensor | 8.99x | 4,087.3 | pipeline | 1,664.6 | hybrid | 2.46x | 6.69x | 1.83x | 0.27x |
| MiMo-V2.6-Pro | 6 | 277,350 | 28,814.6 | wafer-pipeline | 2,876.6 | wafer-hybrid | 10.02x | 4,946.7 | pipeline | 1,654.5 | hybrid | 2.99x | 5.83x | 1.74x | 0.30x |
| MiMo-V2.6-Pro | 8 | 369,800 | 28,814.6 | wafer-pipeline | 2,793.6 | wafer-tensor | 10.31x | 5,542.1 | pipeline | 1,649.3 | hybrid | 3.36x | 5.20x | 1.69x | 0.33x |
| MiMo-V2.6-Pro | 12 | 554,700 | 28,814.6 | wafer-pipeline | 2,572.1 | wafer-tensor | 11.20x | 6,297.9 | pipeline | 1,760.6 | hybrid | 3.58x | 4.58x | 1.46x | 0.32x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.27x to 1.02x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Pro | 1 | fastest | MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x141 | 114,915 | 4,497.3 | 4,497.3 | link_latency | MiMo-V2.6-Pro/b200_sxm-x72-nvl72-tensor | 115,200 | 1.00x | tensor | 341.65 | 1,812.9 | 1,812.9 | link_latency | 2.48x | 0.94x | 67.82x | 2.48x |
| MiMo-V2.6-Pro | 1 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x113 | 92,095 | 1,494.8 | 1,494.8 | compute | MiMo-V2.6-Pro/b200_sxm-x58-nvl72-tensor | 92,800 | 0.99x | tensor | 341.64 | 1,671.0 | 1,671.0 | link_latency | 0.89x | 0.39x | 22.54x | 0.89x |
| MiMo-V2.6-Pro | 2 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | 11,186,450 | 1,313.8 | 2,627.5 | link_latency | MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid | 11,187,200 | 1.00x | hybrid | 498.68 | 1,407.7 | 137,949.9 | link_latency | 0.93x | 0.01x | 19.81x | 1.02x |
| MiMo-V2.6-Pro | 4 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | 11,186,450 | 1,290.3 | 5,161.0 | link_latency | MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid | 11,187,200 | 1.00x | hybrid | 498.68 | 1,407.7 | 137,949.9 | link_latency | 0.92x | 0.01x | 19.46x | 1.00x |
| MiMo-V2.6-Pro | 8 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | 11,186,450 | 1,245.7 | 9,965.3 | link_latency | MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid | 11,187,200 | 1.00x | hybrid | 498.68 | 1,407.7 | 137,949.9 | link_latency | 0.88x | 0.02x | 18.78x | 0.96x |
| MiMo-V2.6-Pro | 16 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | 11,186,450 | 1,165.1 | 18,642.1 | link_latency | MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid | 11,187,200 | 1.00x | hybrid | 498.68 | 1,407.7 | 137,949.9 | link_latency | 0.83x | 0.04x | 17.57x | 0.90x |
| MiMo-V2.6-Pro | 32 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | 11,186,450 | 1,031.7 | 33,015.4 | link_latency | MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid | 11,187,200 | 1.00x | hybrid | 498.68 | 1,407.7 | 137,949.9 | link_latency | 0.73x | 0.07x | 15.56x | 0.80x |
| MiMo-V2.6-Pro | 64 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | 11,186,450 | 839.5 | 53,727.6 | link_latency | MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid | 11,187,200 | 1.00x | hybrid | 498.68 | 1,407.7 | 137,949.9 | link_latency | 0.60x | 0.12x | 12.66x | 0.65x |
| MiMo-V2.6-Pro | 256 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 541.0 | 138,483.8 | kv_read | MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid | 11,187,200 | 1.00x | hybrid | 535.14 | 1,038.3 | 265,808.1 | link_latency | 0.52x | 0.30x | 8.16x | 0.56x |
| MiMo-V2.6-Pro | 1024 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 153.4 | 157,108.9 | kv_read | MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid | 11,187,200 | 1.00x | hybrid | 712.34 | 459.9 | 470,956.1 | kv_read | 0.33x | 0.33x | 2.31x | 0.35x |
| MiMo-V2.6-Pro | 4096 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 39.7 | 162,575.2 | kv_read | MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-expert | 11,187,200 | 1.00x | expert | 1,020.23 | 161.5 | 661,471.9 | kv_read | 0.25x | 0.25x | 0.60x | 0.25x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| MiMo-V2.6-Pro | 29 | 46,400 | 341.54 | 341.54 | 1,191.4 | 1,191.4 |
| MiMo-V2.6-Pro | 37 | 59,200 | 341.58 | 341.58 | 1,360.2 | 1,360.2 |
| MiMo-V2.6-Pro | 46 | 73,600 | 341.61 | 341.61 | 1,512.2 | 1,512.2 |
| MiMo-V2.6-Pro | 57 | 91,200 | 341.63 | 341.63 | 1,659.3 | 1,659.3 |
| MiMo-V2.6-Pro | 58 | 92,800 | 341.64 | 341.64 | 1,671.0 | 1,671.0 |
| MiMo-V2.6-Pro | 71 | 113,600 | 341.65 | 341.65 | 1,804.0 | 1,804.0 |
| MiMo-V2.6-Pro | 72 | 115,200 | 341.65 | 341.65 | 1,812.9 | 1,812.9 |
| MiMo-V2.6-Pro | 77 | 123,200 | 343.93 | 343.93 | 1,383.5 | 1,383.5 |
| MiMo-V2.6-Pro | 78 | 124,800 | 343.93 | 343.93 | 1,392.5 | 1,392.5 |
| MiMo-V2.6-Pro | 85 | 136,000 | 343.93 | 343.93 | 1,452.2 | 1,452.2 |
| MiMo-V2.6-Pro | 87 | 139,200 | 343.93 | 343.93 | 1,468.3 | 1,468.3 |
| MiMo-V2.6-Pro | 88 | 140,800 | 343.93 | 343.93 | 1,476.2 | 1,476.2 |
| MiMo-V2.6-Pro | 89 | 142,400 | 343.93 | 343.93 | 1,484.0 | 1,484.0 |
| MiMo-V2.6-Pro | 113 | 180,800 | 343.93 | 343.93 | 1,647.1 | 1,647.1 |
| MiMo-V2.6-Pro | 116 | 185,600 | 343.93 | 343.93 | 1,664.6 | 1,664.6 |
| MiMo-V2.6-Pro | 118 | 188,800 | 343.93 | 343.93 | 1,676.0 | 1,676.0 |
| MiMo-V2.6-Pro | 123 | 196,800 | 343.93 | 343.93 | 1,703.5 | 1,703.5 |
| MiMo-V2.6-Pro | 124 | 198,400 | 343.93 | 343.93 | 1,708.9 | 1,708.9 |
| MiMo-V2.6-Pro | 132 | 211,200 | 343.93 | 343.93 | 1,749.7 | 1,749.7 |
| MiMo-V2.6-Pro | 133 | 212,800 | 343.93 | 343.93 | 1,754.6 | 1,754.6 |
| MiMo-V2.6-Pro | 144 | 230,400 | 343.93 | 343.93 | 1,805.5 | 1,805.5 |
| MiMo-V2.6-Pro | 170 | 272,000 | 346.21 | 346.21 | 1,642.9 | 1,642.9 |
| MiMo-V2.6-Pro | 173 | 276,800 | 346.21 | 346.21 | 1,654.5 | 1,654.5 |
| MiMo-V2.6-Pro | 231 | 369,600 | 348.48 | 348.48 | 1,649.3 | 1,649.3 |
| MiMo-V2.6-Pro | 347 | 555,200 | 350.76 | 350.76 | 1,760.6 | 1,760.6 |
| MiMo-V2.6-Pro | 1,300 | 2,080,000 | 382.62 | 382.62 | 1,659.2 | 1,659.2 |
| MiMo-V2.6-Pro | 6,992 | 11,187,200 | 498.68 | 498.68 | 1,407.7 | 1,407.7 |

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
| MiMo-V2.6-Pro | 29 | 46,400 | 66.3 | 1,191.4 | 436.4 | tensor | 341.54 | 40.7% | link_latency |
| MiMo-V2.6-Pro | 37 | 59,200 | 66.3 | 1,360.2 | 443.5 | tensor | 341.58 | 46.5% | link_latency |
| MiMo-V2.6-Pro | 46 | 73,600 | 66.3 | 1,512.2 | 456.3 | tensor | 341.61 | 51.7% | link_latency |
| MiMo-V2.6-Pro | 57 | 91,200 | 66.3 | 1,659.3 | 428.3 | tensor | 341.63 | 56.7% | link_latency |
| MiMo-V2.6-Pro | 58 | 92,800 | 66.3 | 1,671.0 | 434.6 | tensor | 341.64 | 57.1% | link_latency |
| MiMo-V2.6-Pro | 71 | 113,600 | 66.3 | 1,804.0 | 465.8 | tensor | 341.65 | 61.6% | link_latency |
| MiMo-V2.6-Pro | 72 | 115,200 | 66.3 | 1,812.9 | 471.2 | tensor | 341.65 | 61.9% | link_latency |
| MiMo-V2.6-Pro | 77 | 123,200 | 66.3 | 862.8 | 1,383.5 | hybrid | 343.93 | 47.6% | link_latency |
| MiMo-V2.6-Pro | 78 | 124,800 | 66.3 | 864.5 | 1,392.5 | hybrid | 343.93 | 47.9% | link_latency |
| MiMo-V2.6-Pro | 85 | 136,000 | 66.3 | 875.7 | 1,452.2 | hybrid | 343.93 | 49.9% | link_latency |
| MiMo-V2.6-Pro | 87 | 139,200 | 66.3 | 878.6 | 1,468.3 | hybrid | 343.93 | 50.5% | link_latency |
| MiMo-V2.6-Pro | 88 | 140,800 | 66.3 | 880.0 | 1,476.2 | hybrid | 343.93 | 50.8% | link_latency |
| MiMo-V2.6-Pro | 89 | 142,400 | 66.3 | 881.4 | 1,484.0 | hybrid | 343.93 | 51.0% | link_latency |
| MiMo-V2.6-Pro | 113 | 180,800 | 66.3 | 908.1 | 1,647.1 | hybrid | 343.93 | 56.6% | link_latency |
| MiMo-V2.6-Pro | 116 | 185,600 | 66.3 | 910.8 | 1,664.6 | hybrid | 343.93 | 57.3% | link_latency |
| MiMo-V2.6-Pro | 118 | 188,800 | 66.3 | 912.5 | 1,676.0 | hybrid | 343.93 | 57.6% | link_latency |
| MiMo-V2.6-Pro | 123 | 196,800 | 66.3 | 916.5 | 1,703.5 | hybrid | 343.93 | 58.6% | link_latency |
| MiMo-V2.6-Pro | 124 | 198,400 | 66.3 | 917.3 | 1,708.9 | hybrid | 343.93 | 58.8% | link_latency |
| MiMo-V2.6-Pro | 132 | 211,200 | 66.3 | 923.1 | 1,749.7 | hybrid | 343.93 | 60.2% | link_latency |
| MiMo-V2.6-Pro | 133 | 212,800 | 66.3 | 923.7 | 1,754.6 | hybrid | 343.93 | 60.3% | link_latency |
| MiMo-V2.6-Pro | 144 | 230,400 | 66.3 | 930.6 | 1,805.5 | hybrid | 343.93 | 62.1% | link_latency |
| MiMo-V2.6-Pro | 170 | 272,000 | 66.3 | 928.6 | 1,642.9 | hybrid | 346.21 | 56.9% | link_latency |
| MiMo-V2.6-Pro | 173 | 276,800 | 66.3 | 929.8 | 1,654.5 | hybrid | 346.21 | 57.3% | link_latency |
| MiMo-V2.6-Pro | 231 | 369,600 | 66.3 | 940.0 | 1,649.3 | hybrid | 348.48 | 57.5% | link_latency |
| MiMo-V2.6-Pro | 347 | 555,200 | 66.3 | 953.6 | 1,760.6 | hybrid | 350.76 | 61.8% | link_latency |
| MiMo-V2.6-Pro | 1300 | 2,080,000 | 66.3 | 966.8 | 1,659.2 | hybrid | 382.62 | 63.5% | link_latency |
| MiMo-V2.6-Pro | 6992 | 11,187,200 | 66.3 | 625.6 | 1,407.7 | hybrid | 498.68 | 70.2% | link_latency |

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
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x243 | MiMo-V2.6-Pro | 243 | pipeline | rom_package_ucie | rom_board_serdes | 69 | 2.50 us | 40,067.4 tok/s | 400,673.6 tok/s | 52 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.68 us; 17 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.82 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x141 | MiMo-V2.6-Pro | 141 | tensor | rom_package_ucie | rom_board_serdes | 280 | 160.56 us | 622.8 tok/s | 6,228.4 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 140 x all_reduce span 36 on rom_board_serdes (traversals 11.0) = 156.79 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x243 | MiMo-V2.6-Pro | 243 | hybrid | rom_package_ucie | rom_board_serdes | 200 | 10.18 us | 9,825.8 tok/s | 98,258.1 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.41 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x242 | MiMo-V2.6-Pro | 242 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x4 | MiMo-V2.6-Pro | 4 | pipeline | on_wafer_n5 | rom_wafer_serdes | 69 | 8.60 us | 11,625.1 tok/s | 116,251.0 tok/s | 68 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-tensor-x154 | MiMo-V2.6-Pro | 154 | tensor | nvlink5 | infiniband_ndr | 280 | 1,007.48 us | 99.3 tok/s | 992.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 666.46 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x4 | MiMo-V2.6-Pro | 4 | tensor | on_wafer_n5 | rom_wafer_serdes | 280 | 300.95 us | 332.3 tok/s | 3,322.9 tok/s | 140 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 269.50 us; 140 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 31.45 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hybrid-x232 | MiMo-V2.6-Pro | 232 | hybrid | nvlink5 | infiniband_ndr | 168 | 404.74 us | 247.1 tok/s | 2,470.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 63.72 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x4 | MiMo-V2.6-Pro | 4 | hybrid | on_wafer_n5 | rom_wafer_serdes | 143 | 269.81 us | 370.6 tok/s | 3,706.4 tok/s | 140 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 269.50 us; 3 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.31 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x242 | MiMo-V2.6-Pro | 242 | pipeline | on_wafer_n5 | rom_wafer_serdes | 69 | 8.60 us | 11,625.1 tok/s | 116,251.0 tok/s | 68 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | MiMo-V2.6-Pro | 242 | tensor | on_wafer_n5 | rom_wafer_serdes | 280 | 732.36 us | 136.5 tok/s | 1,365.5 tok/s | 140 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 269.50 us; 140 x all_reduce span 241 on rom_wafer_serdes (traversals 33.0) = 462.86 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | MiMo-V2.6-Pro | 242 | hybrid | on_wafer_n5 | rom_wafer_serdes | 209 | 276.54 us | 361.6 tok/s | 3,616.1 tok/s | 140 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 269.50 us; 69 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 7.04 us |
| MiMo-V2.6-Pro/b200_sxm-x29-pipeline | MiMo-V2.6-Pro | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 37.17 us | 2,690.4 tok/s | 26,904.4 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.34 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x29-tensor | MiMo-V2.6-Pro | 29 | tensor | nvlink5 | infiniband_ndr | 280 | 986.83 us | 101.3 tok/s | 1,013.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 645.81 us |
| MiMo-V2.6-Pro/b200_sxm-x29-hybrid | MiMo-V2.6-Pro | 29 | hybrid | nvlink5 | infiniband_ndr | 143 | 347.84 us | 287.5 tok/s | 2,874.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x29-nvl72-tensor | MiMo-V2.6-Pro | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.54 us | 292.8 tok/s | 2,927.9 tok/s | 140 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 341.54 us |
| MiMo-V2.6-Pro/b200_sxm-x29-expert | MiMo-V2.6-Pro | 29 | expert | nvlink5 | infiniband_ndr | 280 | 631.36 us | 158.4 tok/s | 1,583.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.67 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 293.69 us |
| MiMo-V2.6-Pro/b200_sxm-x29-nvl72-expert | MiMo-V2.6-Pro | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.06 us | 196.1 tok/s | 1,960.5 tok/s | 140 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 341.54 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.53 us |
| MiMo-V2.6-Pro/b200_sxm-x37-pipeline | MiMo-V2.6-Pro | 37 | pipeline | nvlink5 | infiniband_ndr | 36 | 47.94 us | 2,085.9 tok/s | 20,859.4 tok/s | 32 x point_to_point span 2 on nvlink5 (traversals 1.0) = 38.84 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.10 us |
| MiMo-V2.6-Pro/b200_sxm-x37-tensor | MiMo-V2.6-Pro | 37 | tensor | nvlink5 | infiniband_ndr | 280 | 991.99 us | 100.8 tok/s | 1,008.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 650.98 us |
| MiMo-V2.6-Pro/b200_sxm-x37-hybrid | MiMo-V2.6-Pro | 37 | hybrid | nvlink5 | infiniband_ndr | 144 | 350.12 us | 285.6 tok/s | 2,856.2 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.10 us |
| MiMo-V2.6-Pro/b200_sxm-x37-nvl72-tensor | MiMo-V2.6-Pro | 37 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.58 us | 292.8 tok/s | 2,927.6 tok/s | 140 x all_reduce span 37 on nvlink5_nvl72 (traversals 2.0) = 341.58 us |
| MiMo-V2.6-Pro/b200_sxm-x37-expert | MiMo-V2.6-Pro | 37 | expert | nvlink5 | infiniband_ndr | 280 | 628.89 us | 159.0 tok/s | 1,590.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.25 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 291.64 us |
| MiMo-V2.6-Pro/b200_sxm-x37-nvl72-expert | MiMo-V2.6-Pro | 37 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.99 us | 196.1 tok/s | 1,960.8 tok/s | 140 x all_reduce span 37 on nvlink5_nvl72 (traversals 2.0) = 341.58 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.41 us |
| MiMo-V2.6-Pro/b200_sxm-x46-pipeline | MiMo-V2.6-Pro | 46 | pipeline | nvlink5 | infiniband_ndr | 45 | 59.92 us | 1,668.8 tok/s | 16,687.5 tok/s | 40 x point_to_point span 2 on nvlink5 (traversals 1.0) = 48.55 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.38 us |
| MiMo-V2.6-Pro/b200_sxm-x46-tensor | MiMo-V2.6-Pro | 46 | tensor | nvlink5 | infiniband_ndr | 280 | 995.43 us | 100.5 tok/s | 1,004.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 654.42 us |
| MiMo-V2.6-Pro/b200_sxm-x46-hybrid | MiMo-V2.6-Pro | 46 | hybrid | nvlink5 | infiniband_ndr | 145 | 352.40 us | 283.8 tok/s | 2,837.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.38 us |
| MiMo-V2.6-Pro/b200_sxm-x46-nvl72-tensor | MiMo-V2.6-Pro | 46 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.61 us | 292.7 tok/s | 2,927.3 tok/s | 140 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 341.61 us |
| MiMo-V2.6-Pro/b200_sxm-x46-expert | MiMo-V2.6-Pro | 46 | expert | nvlink5 | infiniband_ndr | 280 | 627.19 us | 159.4 tok/s | 1,594.4 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.00 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 290.18 us |
| MiMo-V2.6-Pro/b200_sxm-x46-nvl72-expert | MiMo-V2.6-Pro | 46 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.94 us | 196.1 tok/s | 1,961.0 tok/s | 140 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 341.61 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.33 us |
| MiMo-V2.6-Pro/b200_sxm-x57-pipeline | MiMo-V2.6-Pro | 57 | pipeline | nvlink5 | infiniband_ndr | 56 | 75.40 us | 1,326.3 tok/s | 13,262.7 tok/s | 49 x point_to_point span 2 on nvlink5 (traversals 1.0) = 59.47 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.93 us |
| MiMo-V2.6-Pro/b200_sxm-x57-tensor | MiMo-V2.6-Pro | 57 | tensor | nvlink5 | infiniband_ndr | 280 | 999.73 us | 100.0 tok/s | 1,000.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 658.72 us |
| MiMo-V2.6-Pro/b200_sxm-x57-hybrid | MiMo-V2.6-Pro | 57 | hybrid | nvlink5 | infiniband_ndr | 147 | 356.95 us | 280.2 tok/s | 2,801.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.93 us |
| MiMo-V2.6-Pro/b200_sxm-x57-nvl72-tensor | MiMo-V2.6-Pro | 57 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.63 us | 292.7 tok/s | 2,927.1 tok/s | 140 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 341.63 us |
| MiMo-V2.6-Pro/b200_sxm-x57-expert | MiMo-V2.6-Pro | 57 | expert | nvlink5 | infiniband_ndr | 280 | 625.75 us | 159.8 tok/s | 1,598.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.72 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 289.03 us |
| MiMo-V2.6-Pro/b200_sxm-x57-nvl72-expert | MiMo-V2.6-Pro | 57 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.90 us | 196.1 tok/s | 1,961.2 tok/s | 140 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 341.63 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.27 us |
| MiMo-V2.6-Pro/b200_sxm-x58-pipeline | MiMo-V2.6-Pro | 58 | pipeline | nvlink5 | infiniband_ndr | 57 | 76.61 us | 1,305.3 tok/s | 13,052.6 tok/s | 50 x point_to_point span 2 on nvlink5 (traversals 1.0) = 60.68 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.93 us |
| MiMo-V2.6-Pro/b200_sxm-x58-tensor | MiMo-V2.6-Pro | 58 | tensor | nvlink5 | infiniband_ndr | 280 | 999.73 us | 100.0 tok/s | 1,000.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 658.72 us |
| MiMo-V2.6-Pro/b200_sxm-x58-hybrid | MiMo-V2.6-Pro | 58 | hybrid | nvlink5 | infiniband_ndr | 147 | 356.95 us | 280.2 tok/s | 2,801.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.93 us |
| MiMo-V2.6-Pro/b200_sxm-x58-nvl72-tensor | MiMo-V2.6-Pro | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.64 us | 292.7 tok/s | 2,927.1 tok/s | 140 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 341.64 us |
| MiMo-V2.6-Pro/b200_sxm-x58-expert | MiMo-V2.6-Pro | 58 | expert | nvlink5 | infiniband_ndr | 280 | 625.66 us | 159.8 tok/s | 1,598.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.72 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 288.95 us |
| MiMo-V2.6-Pro/b200_sxm-x58-nvl72-expert | MiMo-V2.6-Pro | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.90 us | 196.1 tok/s | 1,961.2 tok/s | 140 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 341.64 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.26 us |
| MiMo-V2.6-Pro/b200_sxm-x71-pipeline | MiMo-V2.6-Pro | 71 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x71-tensor | MiMo-V2.6-Pro | 71 | tensor | nvlink5 | infiniband_ndr | 280 | 1,001.17 us | 99.9 tok/s | 998.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 660.15 us |
| MiMo-V2.6-Pro/b200_sxm-x71-hybrid | MiMo-V2.6-Pro | 71 | hybrid | nvlink5 | infiniband_ndr | 148 | 359.22 us | 278.4 tok/s | 2,783.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x71-nvl72-tensor | MiMo-V2.6-Pro | 71 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.65 us | 292.7 tok/s | 2,926.9 tok/s | 140 x all_reduce span 71 on nvlink5_nvl72 (traversals 2.0) = 341.65 us |
| MiMo-V2.6-Pro/b200_sxm-x71-expert | MiMo-V2.6-Pro | 71 | expert | nvlink5 | infiniband_ndr | 280 | 624.70 us | 160.1 tok/s | 1,600.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.63 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 288.08 us |
| MiMo-V2.6-Pro/b200_sxm-x71-nvl72-expert | MiMo-V2.6-Pro | 71 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.87 us | 196.1 tok/s | 1,961.3 tok/s | 140 x all_reduce span 71 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.22 us |
| MiMo-V2.6-Pro/b200_sxm-x72-pipeline | MiMo-V2.6-Pro | 72 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x72-tensor | MiMo-V2.6-Pro | 72 | tensor | nvlink5 | infiniband_ndr | 280 | 1,001.17 us | 99.9 tok/s | 998.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 660.15 us |
| MiMo-V2.6-Pro/b200_sxm-x72-hybrid | MiMo-V2.6-Pro | 72 | hybrid | nvlink5 | infiniband_ndr | 148 | 359.22 us | 278.4 tok/s | 2,783.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x72-nvl72-tensor | MiMo-V2.6-Pro | 72 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.65 us | 292.7 tok/s | 2,926.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us |
| MiMo-V2.6-Pro/b200_sxm-x72-expert | MiMo-V2.6-Pro | 72 | expert | nvlink5 | infiniband_ndr | 280 | 624.58 us | 160.1 tok/s | 1,601.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.56 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 288.02 us |
| MiMo-V2.6-Pro/b200_sxm-x72-nvl72-expert | MiMo-V2.6-Pro | 72 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.87 us | 196.1 tok/s | 1,961.3 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.21 us |
| MiMo-V2.6-Pro/b200_sxm-x77-pipeline | MiMo-V2.6-Pro | 77 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x77-tensor | MiMo-V2.6-Pro | 77 | tensor | nvlink5 | infiniband_ndr | 280 | 1,002.31 us | 99.8 tok/s | 997.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 661.30 us |
| MiMo-V2.6-Pro/b200_sxm-x77-hybrid | MiMo-V2.6-Pro | 77 | hybrid | nvlink5 | infiniband_ndr | 149 | 361.50 us | 276.6 tok/s | 2,766.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.48 us |
| MiMo-V2.6-Pro/b200_sxm-x77-nvl72-tensor | MiMo-V2.6-Pro | 77 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x77-nvl72-hybrid | MiMo-V2.6-Pro | 77 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x77-expert | MiMo-V2.6-Pro | 77 | expert | nvlink5 | infiniband_ndr | 280 | 624.33 us | 160.2 tok/s | 1,601.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.56 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.77 us |
| MiMo-V2.6-Pro/b200_sxm-x77-nvl72-expert | MiMo-V2.6-Pro | 77 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 629.43 us | 158.9 tok/s | 1,588.7 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.77 us |
| MiMo-V2.6-Pro/b200_sxm-x78-pipeline | MiMo-V2.6-Pro | 78 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x78-tensor | MiMo-V2.6-Pro | 78 | tensor | nvlink5 | infiniband_ndr | 280 | 1,002.31 us | 99.8 tok/s | 997.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 661.30 us |
| MiMo-V2.6-Pro/b200_sxm-x78-hybrid | MiMo-V2.6-Pro | 78 | hybrid | nvlink5 | infiniband_ndr | 149 | 361.50 us | 276.6 tok/s | 2,766.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.48 us |
| MiMo-V2.6-Pro/b200_sxm-x78-nvl72-tensor | MiMo-V2.6-Pro | 78 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x78-nvl72-hybrid | MiMo-V2.6-Pro | 78 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x78-expert | MiMo-V2.6-Pro | 78 | expert | nvlink5 | infiniband_ndr | 280 | 624.29 us | 160.2 tok/s | 1,601.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.56 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.73 us |
| MiMo-V2.6-Pro/b200_sxm-x78-nvl72-expert | MiMo-V2.6-Pro | 78 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 629.38 us | 158.9 tok/s | 1,588.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.73 us |
| MiMo-V2.6-Pro/b200_sxm-x85-pipeline | MiMo-V2.6-Pro | 85 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x85-tensor | MiMo-V2.6-Pro | 85 | tensor | nvlink5 | infiniband_ndr | 280 | 1,003.25 us | 99.7 tok/s | 996.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 662.24 us |
| MiMo-V2.6-Pro/b200_sxm-x85-hybrid | MiMo-V2.6-Pro | 85 | hybrid | nvlink5 | infiniband_ndr | 150 | 363.78 us | 274.9 tok/s | 2,749.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.76 us |
| MiMo-V2.6-Pro/b200_sxm-x85-nvl72-tensor | MiMo-V2.6-Pro | 85 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x85-nvl72-hybrid | MiMo-V2.6-Pro | 85 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x85-expert | MiMo-V2.6-Pro | 85 | expert | nvlink5 | infiniband_ndr | 280 | 623.94 us | 160.3 tok/s | 1,602.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.50 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.44 us |
| MiMo-V2.6-Pro/b200_sxm-x85-nvl72-expert | MiMo-V2.6-Pro | 85 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 629.09 us | 159.0 tok/s | 1,589.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.44 us |
| MiMo-V2.6-Pro/b200_sxm-x87-pipeline | MiMo-V2.6-Pro | 87 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x87-tensor | MiMo-V2.6-Pro | 87 | tensor | nvlink5 | infiniband_ndr | 280 | 1,003.25 us | 99.7 tok/s | 996.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 662.24 us |
| MiMo-V2.6-Pro/b200_sxm-x87-hybrid | MiMo-V2.6-Pro | 87 | hybrid | nvlink5 | infiniband_ndr | 150 | 363.78 us | 274.9 tok/s | 2,749.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.76 us |
| MiMo-V2.6-Pro/b200_sxm-x87-nvl72-tensor | MiMo-V2.6-Pro | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x87-nvl72-hybrid | MiMo-V2.6-Pro | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x87-expert | MiMo-V2.6-Pro | 87 | expert | nvlink5 | infiniband_ndr | 280 | 623.87 us | 160.3 tok/s | 1,602.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.50 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.36 us |
| MiMo-V2.6-Pro/b200_sxm-x87-nvl72-expert | MiMo-V2.6-Pro | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 629.02 us | 159.0 tok/s | 1,589.8 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.36 us |
| MiMo-V2.6-Pro/b200_sxm-x88-pipeline | MiMo-V2.6-Pro | 88 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x88-tensor | MiMo-V2.6-Pro | 88 | tensor | nvlink5 | infiniband_ndr | 280 | 1,003.25 us | 99.7 tok/s | 996.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 662.24 us |
| MiMo-V2.6-Pro/b200_sxm-x88-hybrid | MiMo-V2.6-Pro | 88 | hybrid | nvlink5 | infiniband_ndr | 150 | 363.78 us | 274.9 tok/s | 2,749.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.76 us |
| MiMo-V2.6-Pro/b200_sxm-x88-nvl72-tensor | MiMo-V2.6-Pro | 88 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x88-nvl72-hybrid | MiMo-V2.6-Pro | 88 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x88-expert | MiMo-V2.6-Pro | 88 | expert | nvlink5 | infiniband_ndr | 280 | 623.78 us | 160.3 tok/s | 1,603.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.46 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.33 us |
| MiMo-V2.6-Pro/b200_sxm-x88-nvl72-expert | MiMo-V2.6-Pro | 88 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.98 us | 159.0 tok/s | 1,589.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.33 us |
| MiMo-V2.6-Pro/b200_sxm-x89-pipeline | MiMo-V2.6-Pro | 89 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x89-tensor | MiMo-V2.6-Pro | 89 | tensor | nvlink5 | infiniband_ndr | 280 | 1,004.04 us | 99.6 tok/s | 996.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 663.02 us |
| MiMo-V2.6-Pro/b200_sxm-x89-hybrid | MiMo-V2.6-Pro | 89 | hybrid | nvlink5 | infiniband_ndr | 151 | 366.05 us | 273.2 tok/s | 2,731.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.03 us |
| MiMo-V2.6-Pro/b200_sxm-x89-nvl72-tensor | MiMo-V2.6-Pro | 89 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x89-nvl72-hybrid | MiMo-V2.6-Pro | 89 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x89-expert | MiMo-V2.6-Pro | 89 | expert | nvlink5 | infiniband_ndr | 280 | 623.75 us | 160.3 tok/s | 1,603.2 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.46 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.29 us |
| MiMo-V2.6-Pro/b200_sxm-x89-nvl72-expert | MiMo-V2.6-Pro | 89 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.95 us | 159.0 tok/s | 1,590.0 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.29 us |
| MiMo-V2.6-Pro/b200_sxm-x113-pipeline | MiMo-V2.6-Pro | 113 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x113-tensor | MiMo-V2.6-Pro | 113 | tensor | nvlink5 | infiniband_ndr | 280 | 1,005.76 us | 99.4 tok/s | 994.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 664.74 us |
| MiMo-V2.6-Pro/b200_sxm-x113-hybrid | MiMo-V2.6-Pro | 113 | hybrid | nvlink5 | infiniband_ndr | 154 | 372.88 us | 268.2 tok/s | 2,681.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 31.86 us |
| MiMo-V2.6-Pro/b200_sxm-x113-nvl72-tensor | MiMo-V2.6-Pro | 113 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x113-nvl72-hybrid | MiMo-V2.6-Pro | 113 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x113-expert | MiMo-V2.6-Pro | 113 | expert | nvlink5 | infiniband_ndr | 280 | 622.99 us | 160.5 tok/s | 1,605.2 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.36 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.64 us |
| MiMo-V2.6-Pro/b200_sxm-x113-nvl72-expert | MiMo-V2.6-Pro | 113 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.29 us | 159.2 tok/s | 1,591.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.64 us |
| MiMo-V2.6-Pro/b200_sxm-x116-pipeline | MiMo-V2.6-Pro | 116 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x116-tensor | MiMo-V2.6-Pro | 116 | tensor | nvlink5 | infiniband_ndr | 280 | 1,005.76 us | 99.4 tok/s | 994.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 664.74 us |
| MiMo-V2.6-Pro/b200_sxm-x116-hybrid | MiMo-V2.6-Pro | 116 | hybrid | nvlink5 | infiniband_ndr | 154 | 372.88 us | 268.2 tok/s | 2,681.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 31.86 us |
| MiMo-V2.6-Pro/b200_sxm-x116-nvl72-tensor | MiMo-V2.6-Pro | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x116-nvl72-hybrid | MiMo-V2.6-Pro | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x116-expert | MiMo-V2.6-Pro | 116 | expert | nvlink5 | infiniband_ndr | 280 | 622.93 us | 160.5 tok/s | 1,605.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.36 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.57 us |
| MiMo-V2.6-Pro/b200_sxm-x116-nvl72-expert | MiMo-V2.6-Pro | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.23 us | 159.2 tok/s | 1,591.8 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.57 us |
| MiMo-V2.6-Pro/b200_sxm-x118-pipeline | MiMo-V2.6-Pro | 118 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x118-tensor | MiMo-V2.6-Pro | 118 | tensor | nvlink5 | infiniband_ndr | 280 | 1,005.76 us | 99.4 tok/s | 994.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 664.74 us |
| MiMo-V2.6-Pro/b200_sxm-x118-hybrid | MiMo-V2.6-Pro | 118 | hybrid | nvlink5 | infiniband_ndr | 154 | 372.88 us | 268.2 tok/s | 2,681.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 31.86 us |
| MiMo-V2.6-Pro/b200_sxm-x118-nvl72-tensor | MiMo-V2.6-Pro | 118 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x118-nvl72-hybrid | MiMo-V2.6-Pro | 118 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x118-expert | MiMo-V2.6-Pro | 118 | expert | nvlink5 | infiniband_ndr | 280 | 622.89 us | 160.5 tok/s | 1,605.4 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.36 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.53 us |
| MiMo-V2.6-Pro/b200_sxm-x118-nvl72-expert | MiMo-V2.6-Pro | 118 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.19 us | 159.2 tok/s | 1,591.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.53 us |
| MiMo-V2.6-Pro/b200_sxm-x123-pipeline | MiMo-V2.6-Pro | 123 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x123-tensor | MiMo-V2.6-Pro | 123 | tensor | nvlink5 | infiniband_ndr | 280 | 1,006.19 us | 99.4 tok/s | 993.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 665.17 us |
| MiMo-V2.6-Pro/b200_sxm-x123-hybrid | MiMo-V2.6-Pro | 123 | hybrid | nvlink5 | infiniband_ndr | 155 | 375.15 us | 266.6 tok/s | 2,665.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 34.14 us |
| MiMo-V2.6-Pro/b200_sxm-x123-nvl72-tensor | MiMo-V2.6-Pro | 123 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x123-nvl72-hybrid | MiMo-V2.6-Pro | 123 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x123-expert | MiMo-V2.6-Pro | 123 | expert | nvlink5 | infiniband_ndr | 280 | 622.77 us | 160.6 tok/s | 1,605.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.33 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.44 us |
| MiMo-V2.6-Pro/b200_sxm-x123-nvl72-expert | MiMo-V2.6-Pro | 123 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.09 us | 159.2 tok/s | 1,592.1 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.44 us |
| MiMo-V2.6-Pro/b200_sxm-x124-pipeline | MiMo-V2.6-Pro | 124 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x124-tensor | MiMo-V2.6-Pro | 124 | tensor | nvlink5 | infiniband_ndr | 280 | 1,006.19 us | 99.4 tok/s | 993.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 665.17 us |
| MiMo-V2.6-Pro/b200_sxm-x124-hybrid | MiMo-V2.6-Pro | 124 | hybrid | nvlink5 | infiniband_ndr | 155 | 375.15 us | 266.6 tok/s | 2,665.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 34.14 us |
| MiMo-V2.6-Pro/b200_sxm-x124-nvl72-tensor | MiMo-V2.6-Pro | 124 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x124-nvl72-hybrid | MiMo-V2.6-Pro | 124 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x124-expert | MiMo-V2.6-Pro | 124 | expert | nvlink5 | infiniband_ndr | 280 | 622.75 us | 160.6 tok/s | 1,605.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.33 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.42 us |
| MiMo-V2.6-Pro/b200_sxm-x124-nvl72-expert | MiMo-V2.6-Pro | 124 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.07 us | 159.2 tok/s | 1,592.2 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.42 us |
| MiMo-V2.6-Pro/b200_sxm-x132-pipeline | MiMo-V2.6-Pro | 132 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x132-tensor | MiMo-V2.6-Pro | 132 | tensor | nvlink5 | infiniband_ndr | 280 | 1,006.57 us | 99.3 tok/s | 993.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 665.55 us |
| MiMo-V2.6-Pro/b200_sxm-x132-hybrid | MiMo-V2.6-Pro | 132 | hybrid | nvlink5 | infiniband_ndr | 156 | 377.43 us | 264.9 tok/s | 2,649.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 36.41 us |
| MiMo-V2.6-Pro/b200_sxm-x132-nvl72-tensor | MiMo-V2.6-Pro | 132 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x132-nvl72-hybrid | MiMo-V2.6-Pro | 132 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x132-expert | MiMo-V2.6-Pro | 132 | expert | nvlink5 | infiniband_ndr | 280 | 622.60 us | 160.6 tok/s | 1,606.2 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.31 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.29 us |
| MiMo-V2.6-Pro/b200_sxm-x132-nvl72-expert | MiMo-V2.6-Pro | 132 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 627.94 us | 159.3 tok/s | 1,592.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.29 us |
| MiMo-V2.6-Pro/b200_sxm-x133-pipeline | MiMo-V2.6-Pro | 133 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x133-tensor | MiMo-V2.6-Pro | 133 | tensor | nvlink5 | infiniband_ndr | 280 | 1,006.57 us | 99.3 tok/s | 993.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 665.55 us |
| MiMo-V2.6-Pro/b200_sxm-x133-hybrid | MiMo-V2.6-Pro | 133 | hybrid | nvlink5 | infiniband_ndr | 156 | 377.43 us | 264.9 tok/s | 2,649.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 36.41 us |
| MiMo-V2.6-Pro/b200_sxm-x133-nvl72-tensor | MiMo-V2.6-Pro | 133 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x133-nvl72-hybrid | MiMo-V2.6-Pro | 133 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x133-expert | MiMo-V2.6-Pro | 133 | expert | nvlink5 | infiniband_ndr | 280 | 622.58 us | 160.6 tok/s | 1,606.2 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.31 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.27 us |
| MiMo-V2.6-Pro/b200_sxm-x133-nvl72-expert | MiMo-V2.6-Pro | 133 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 627.92 us | 159.3 tok/s | 1,592.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.27 us |
| MiMo-V2.6-Pro/b200_sxm-x144-pipeline | MiMo-V2.6-Pro | 144 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x144-tensor | MiMo-V2.6-Pro | 144 | tensor | nvlink5 | infiniband_ndr | 280 | 1,006.90 us | 99.3 tok/s | 993.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 18 on infiniband_ndr (traversals 2.0) = 665.88 us |
| MiMo-V2.6-Pro/b200_sxm-x144-hybrid | MiMo-V2.6-Pro | 144 | hybrid | nvlink5 | infiniband_ndr | 157 | 379.71 us | 263.4 tok/s | 2,633.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 38.69 us |
| MiMo-V2.6-Pro/b200_sxm-x144-nvl72-tensor | MiMo-V2.6-Pro | 144 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x144-nvl72-hybrid | MiMo-V2.6-Pro | 144 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x144-expert | MiMo-V2.6-Pro | 144 | expert | nvlink5 | infiniband_ndr | 280 | 622.39 us | 160.7 tok/s | 1,606.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.28 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.11 us |
| MiMo-V2.6-Pro/b200_sxm-x144-nvl72-expert | MiMo-V2.6-Pro | 144 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 624.94 us | 160.0 tok/s | 1,600.2 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 338.83 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.11 us |
| MiMo-V2.6-Pro/b200_sxm-x170-pipeline | MiMo-V2.6-Pro | 170 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x170-tensor | MiMo-V2.6-Pro | 170 | tensor | nvlink5 | infiniband_ndr | 280 | 1,007.95 us | 99.2 tok/s | 992.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 666.93 us |
| MiMo-V2.6-Pro/b200_sxm-x170-hybrid | MiMo-V2.6-Pro | 170 | hybrid | nvlink5 | infiniband_ndr | 161 | 388.81 us | 257.2 tok/s | 2,572.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 47.79 us |
| MiMo-V2.6-Pro/b200_sxm-x170-nvl72-tensor | MiMo-V2.6-Pro | 170 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 978.87 us | 102.2 tok/s | 1,021.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 637.21 us |
| MiMo-V2.6-Pro/b200_sxm-x170-nvl72-hybrid | MiMo-V2.6-Pro | 170 | hybrid | nvlink5_nvl72 | infiniband_ndr | 142 | 346.21 us | 288.8 tok/s | 2,888.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x170-expert | MiMo-V2.6-Pro | 170 | expert | nvlink5 | infiniband_ndr | 280 | 622.06 us | 160.8 tok/s | 1,607.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.24 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.82 us |
| MiMo-V2.6-Pro/b200_sxm-x170-nvl72-expert | MiMo-V2.6-Pro | 170 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 624.65 us | 160.1 tok/s | 1,600.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 338.83 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.82 us |
| MiMo-V2.6-Pro/b200_sxm-x173-pipeline | MiMo-V2.6-Pro | 173 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x173-tensor | MiMo-V2.6-Pro | 173 | tensor | nvlink5 | infiniband_ndr | 280 | 1,007.95 us | 99.2 tok/s | 992.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 666.93 us |
| MiMo-V2.6-Pro/b200_sxm-x173-hybrid | MiMo-V2.6-Pro | 173 | hybrid | nvlink5 | infiniband_ndr | 161 | 388.81 us | 257.2 tok/s | 2,572.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 47.79 us |
| MiMo-V2.6-Pro/b200_sxm-x173-nvl72-tensor | MiMo-V2.6-Pro | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 978.87 us | 102.2 tok/s | 1,021.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 637.21 us |
| MiMo-V2.6-Pro/b200_sxm-x173-nvl72-hybrid | MiMo-V2.6-Pro | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 142 | 346.21 us | 288.8 tok/s | 2,888.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x173-expert | MiMo-V2.6-Pro | 173 | expert | nvlink5 | infiniband_ndr | 280 | 622.03 us | 160.8 tok/s | 1,607.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.24 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.79 us |
| MiMo-V2.6-Pro/b200_sxm-x173-nvl72-expert | MiMo-V2.6-Pro | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 624.62 us | 160.1 tok/s | 1,601.0 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 338.83 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.79 us |
| MiMo-V2.6-Pro/b200_sxm-x231-pipeline | MiMo-V2.6-Pro | 231 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x231-tensor | MiMo-V2.6-Pro | 231 | tensor | nvlink5 | infiniband_ndr | 280 | 1,009.08 us | 99.1 tok/s | 991.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 668.06 us |
| MiMo-V2.6-Pro/b200_sxm-x231-hybrid | MiMo-V2.6-Pro | 231 | hybrid | nvlink5 | infiniband_ndr | 168 | 404.74 us | 247.1 tok/s | 2,470.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 63.72 us |
| MiMo-V2.6-Pro/b200_sxm-x231-nvl72-tensor | MiMo-V2.6-Pro | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 987.47 us | 101.3 tok/s | 1,012.7 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 645.81 us |
| MiMo-V2.6-Pro/b200_sxm-x231-nvl72-hybrid | MiMo-V2.6-Pro | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 143 | 348.48 us | 287.0 tok/s | 2,869.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x231-expert | MiMo-V2.6-Pro | 231 | expert | nvlink5 | infiniband_ndr | 280 | 621.57 us | 160.9 tok/s | 1,608.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.18 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.39 us |
| MiMo-V2.6-Pro/b200_sxm-x231-nvl72-expert | MiMo-V2.6-Pro | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 623.28 us | 160.4 tok/s | 1,604.4 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 337.88 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.39 us |
| MiMo-V2.6-Pro/b200_sxm-x347-pipeline | MiMo-V2.6-Pro | 347 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x347-tensor | MiMo-V2.6-Pro | 347 | tensor | nvlink5 | infiniband_ndr | 280 | 1,010.29 us | 99.0 tok/s | 989.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 669.27 us |
| MiMo-V2.6-Pro/b200_sxm-x347-hybrid | MiMo-V2.6-Pro | 347 | hybrid | nvlink5 | infiniband_ndr | 183 | 438.88 us | 227.9 tok/s | 2,278.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 97.86 us |
| MiMo-V2.6-Pro/b200_sxm-x347-nvl72-tensor | MiMo-V2.6-Pro | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 992.63 us | 100.7 tok/s | 1,007.4 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 650.98 us |
| MiMo-V2.6-Pro/b200_sxm-x347-nvl72-hybrid | MiMo-V2.6-Pro | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 144 | 350.76 us | 285.1 tok/s | 2,851.0 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.10 us |
| MiMo-V2.6-Pro/b200_sxm-x347-expert | MiMo-V2.6-Pro | 347 | expert | nvlink5 | infiniband_ndr | 280 | 621.11 us | 161.0 tok/s | 1,610.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.12 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 284.99 us |
| MiMo-V2.6-Pro/b200_sxm-x347-nvl72-expert | MiMo-V2.6-Pro | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 622.41 us | 160.7 tok/s | 1,606.7 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 337.41 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 284.99 us |
| MiMo-V2.6-Pro/b200_sxm-x1300-pipeline | MiMo-V2.6-Pro | 1300 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x1300-tensor | MiMo-V2.6-Pro | 1300 | tensor | nvlink5 | infiniband_ndr | 280 | 1,580.40 us | 63.3 tok/s | 632.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 163 on infiniband_ndr (traversals 4.0) = 1,239.39 us |
| MiMo-V2.6-Pro/b200_sxm-x1300-hybrid | MiMo-V2.6-Pro | 1300 | hybrid | nvlink5 | infiniband_ndr | 209 | 498.05 us | 200.8 tok/s | 2,007.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 69 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 157.03 us |
| MiMo-V2.6-Pro/b200_sxm-x1300-nvl72-tensor | MiMo-V2.6-Pro | 1300 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 1,007.84 us | 99.2 tok/s | 992.2 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 666.19 us |
| MiMo-V2.6-Pro/b200_sxm-x1300-nvl72-hybrid | MiMo-V2.6-Pro | 1300 | hybrid | nvlink5_nvl72 | infiniband_ndr | 158 | 382.62 us | 261.4 tok/s | 2,613.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 40.96 us |
| MiMo-V2.6-Pro/b200_sxm-x1300-expert | MiMo-V2.6-Pro | 1300 | expert | nvlink5 | infiniband_ndr | 280 | 620.44 us | 161.2 tok/s | 1,611.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.03 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 284.41 us |
| MiMo-V2.6-Pro/b200_sxm-x1300-nvl72-expert | MiMo-V2.6-Pro | 1300 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 620.73 us | 161.1 tok/s | 1,611.0 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 336.31 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 284.41 us |
| MiMo-V2.6-Pro/b200_sxm-x6992-pipeline | MiMo-V2.6-Pro | 6992 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x6992-tensor | MiMo-V2.6-Pro | 6992 | tensor | nvlink5 | infiniband_ndr | 280 | 1,580.92 us | 63.3 tok/s | 632.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 874 on infiniband_ndr (traversals 4.0) = 1,239.90 us |
| MiMo-V2.6-Pro/b200_sxm-x6992-hybrid | MiMo-V2.6-Pro | 6992 | hybrid | nvlink5 | infiniband_ndr | 209 | 498.05 us | 200.8 tok/s | 2,007.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 69 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 157.03 us |
| MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-tensor | MiMo-V2.6-Pro | 6992 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 1,580.62 us | 63.3 tok/s | 632.7 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 98 on infiniband_ndr (traversals 4.0) = 1,238.97 us |
| MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-hybrid | MiMo-V2.6-Pro | 6992 | hybrid | nvlink5_nvl72 | infiniband_ndr | 209 | 498.68 us | 200.5 tok/s | 2,005.3 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 69 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 157.03 us |
| MiMo-V2.6-Pro/b200_sxm-x6992-expert | MiMo-V2.6-Pro | 6992 | expert | nvlink5 | infiniband_ndr | 280 | 620.25 us | 161.2 tok/s | 1,612.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.01 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 284.24 us |
| MiMo-V2.6-Pro/b200_sxm-x6992-nvl72-expert | MiMo-V2.6-Pro | 6992 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 620.30 us | 161.2 tok/s | 1,612.1 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 336.06 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 284.24 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Pro | 1 | array | array | MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x139 | 113,285 | 4,433.8 | 0.039 | 4,433.8 (113,285) | 2,938.3 (138,675) | 0.66x | link_latency |
| MiMo-V2.6-Pro | 2 | wafer | wafer | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | 11,186,450 | 1,313.8 | 0.000 | — (—) | 1,313.8 (11,186,450) | — | link_latency |
| MiMo-V2.6-Pro | 4 | wafer | wafer | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | 11,186,450 | 1,290.3 | 0.000 | — (—) | 1,290.3 (11,186,450) | — | link_latency |
| MiMo-V2.6-Pro | 8 | wafer | wafer | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | 11,186,450 | 1,245.7 | 0.000 | — (—) | 1,245.7 (11,186,450) | — | link_latency |
| MiMo-V2.6-Pro | 16 | wafer | wafer | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | 11,186,450 | 1,165.1 | 0.000 | — (—) | 1,165.1 (11,186,450) | — | link_latency |
| MiMo-V2.6-Pro | 32 | wafer | wafer | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | 11,186,450 | 1,031.7 | 0.000 | — (—) | 1,031.7 (11,186,450) | — | link_latency |
| MiMo-V2.6-Pro | 64 | wafer | wafer | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242 | 11,186,450 | 839.5 | 0.000 | — (—) | 839.5 (11,186,450) | — | link_latency |
| MiMo-V2.6-Pro | 256 | wafer | wafer | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 541.0 | 0.000 | — (—) | 541.0 (11,186,450) | — | kv_read |
| MiMo-V2.6-Pro | 1024 | wafer | wafer | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 153.4 | 0.000 | — (—) | 153.4 (11,186,450) | — | kv_read |
| MiMo-V2.6-Pro | 4096 | wafer | wafer | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 39.7 | 0.000 | — (—) | 39.7 (11,186,450) | — | kv_read |

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

## Sizing one expert region

The per-region machine's cost is not arithmetic; it is a
pre-compute block and an activation distribution network per
region. The block is small against the array it serves. The
distribution network is the real cost and this model does not
price it.

| Model | Experts | Routed bytes/expert | One region | Pre-compute/region | All regions | All pre-compute | Whole checkpoint |
|---|---:|---:|---:|---:|---:|---:|---:|
| MiMo-V2.6-Pro | 384 | 1,383.7 MB | 236.0 mm2 | 42.49 mm2 (18.0%) | 90,640 mm2 | 16,315 mm2 | 96,556 mm2 = 118.5 reticles |

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
| MiMo-V2.6-Pro | 1 | sram | 137,134.6 | 25,311.4 | 25,311.4 | 5.42x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 2 | sram | 137,134.6 | 25,311.4 | 25,311.4 | 5.42x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 4 | sram | 137,134.6 | 25,311.4 | 25,311.4 | 5.42x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 8 | sram | 137,134.6 | 25,311.4 | 25,311.4 | 5.42x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 16 | sram | 137,134.6 | 25,311.4 | 25,311.4 | 5.42x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 32 | sram | 137,134.6 | 25,311.4 | 33,015.4 | 5.42x | 1.30x | kv_read | weight_read | link_latency |
| MiMo-V2.6-Pro | 64 | sram | 137,134.6 | 25,311.4 | 53,727.6 | 5.42x | 2.12x | kv_read | weight_read | link_latency |
| MiMo-V2.6-Pro | 256 | sram | 138,483.8 | 25,357.0 | 101,471.4 | 5.46x | 4.00x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Pro | 1024 | sram | 157,108.9 | 25,919.6 | 130,452.3 | 6.06x | 5.03x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Pro | 4096 | sram | 162,575.2 | 26,064.2 | 146,984.8 | 6.24x | 5.64x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 1 | rom | 137,134.6 | 137,134.6 | 137,134.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 2 | rom | 137,134.6 | 137,134.6 | 137,134.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 4 | rom | 137,134.6 | 137,134.6 | 137,134.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 8 | rom | 137,134.6 | 137,134.6 | 137,134.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 16 | rom | 137,134.6 | 137,134.6 | 137,134.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 32 | rom | 137,134.6 | 137,134.6 | 137,134.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 64 | rom | 137,134.6 | 137,134.6 | 137,134.6 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 256 | rom | 138,483.8 | 138,483.8 | 138,483.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 1024 | rom | 157,108.9 | 157,108.9 | 157,108.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 4096 | rom | 162,575.2 | 162,575.2 | 162,575.2 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| MiMo-V2.6-Pro | 1 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 1.00 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-romfill | 11,186,450 | 86.98 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream | 11,186,450 | 1.00 | 1.00 | 25,311.4 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 1 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion | 11,186,450 | 1.00 | 1.00 | 25,311.4 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 1 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 2 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 1.00 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 2 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-romfill | 11,186,450 | 86.98 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 2 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream | 11,186,450 | 1.00 | 1.00 | 25,311.4 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 2 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 2 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion | 11,186,450 | 1.00 | 1.00 | 25,311.4 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 2 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 1.00 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-romfill | 11,186,450 | 86.98 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream | 11,186,450 | 1.00 | 1.00 | 25,311.4 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 4 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion | 11,186,450 | 1.00 | 1.00 | 25,311.4 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 4 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 8 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 1.00 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 8 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-romfill | 11,186,450 | 86.98 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 8 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream | 11,186,450 | 1.00 | 1.00 | 25,311.4 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 8 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 8 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion | 11,186,450 | 1.00 | 1.00 | 25,311.4 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 8 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 16 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 1.00 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 16 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-romfill | 11,186,450 | 86.98 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 16 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream | 11,186,450 | 1.00 | 1.00 | 25,311.4 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 16 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 16 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion | 11,186,450 | 1.00 | 1.00 | 25,311.4 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 16 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 32 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 1.00 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 32 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-romfill | 11,186,450 | 86.98 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 32 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream | 11,186,450 | 1.00 | 1.00 | 25,311.4 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 32 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 32 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242-perregion | 11,186,450 | 1.00 | 4.00 | 33,015.4 | 0.003 | link_latency | 0.24x |
| MiMo-V2.6-Pro | 32 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 64 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 1.00 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 64 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-romfill | 11,186,450 | 86.98 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 64 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream | 11,186,450 | 1.00 | 1.00 | 25,311.4 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 64 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 64 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242-perregion | 11,186,450 | 1.00 | 5.71 | 53,727.6 | 0.005 | link_latency | 0.39x |
| MiMo-V2.6-Pro | 64 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion-romfill | 11,186,450 | 292.28 | 1.00 | 137,134.6 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 256 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 1.00 | 1.00 | 138,483.8 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 256 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-romfill | 11,186,450 | 86.98 | 1.00 | 138,483.8 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 256 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream | 11,186,450 | 1.00 | 1.06 | 25,357.0 | 0.002 | weight_read | 0.18x |
| MiMo-V2.6-Pro | 256 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream-romfill | 11,186,450 | 292.28 | 1.06 | 138,483.8 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 256 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242-perregion | 11,186,450 | 1.00 | 13.19 | 101,471.4 | 0.009 | kv_read | 0.73x |
| MiMo-V2.6-Pro | 256 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion-romfill | 11,186,450 | 292.28 | 1.01 | 138,483.8 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 1.00 | 1.00 | 157,108.9 | 0.014 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-romfill | 11,186,450 | 86.98 | 1.00 | 157,108.9 | 0.014 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream | 11,186,450 | 1.00 | 4.25 | 25,919.6 | 0.002 | weight_read | 0.16x |
| MiMo-V2.6-Pro | 1024 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream-romfill | 11,186,450 | 292.28 | 4.25 | 157,108.9 | 0.014 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x242-perregion | 11,186,450 | 1.00 | 36.01 | 130,452.3 | 0.012 | kv_read | 0.83x |
| MiMo-V2.6-Pro | 1024 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion-romfill | 11,186,450 | 292.28 | 1.68 | 157,108.9 | 0.014 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242 | 11,186,450 | 1.00 | 1.00 | 162,575.2 | 0.015 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-romfill | 11,186,450 | 86.98 | 1.00 | 162,575.2 | 0.015 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream | 11,186,450 | 1.00 | 17.00 | 26,064.2 | 0.002 | weight_read | 0.16x |
| MiMo-V2.6-Pro | 4096 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perstream-romfill | 11,186,450 | 292.28 | 17.00 | 162,575.2 | 0.015 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion | 11,186,450 | 1.00 | 2.99 | 146,984.8 | 0.013 | weight_read | 0.90x |
| MiMo-V2.6-Pro | 4096 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x242-perregion-romfill | 11,186,450 | 292.28 | 2.99 | 162,575.2 | 0.015 | kv_read | 1.00x |

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
| MiMo-V2.6-Pro | 1 | 72 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 4 | 13,726 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 8 | 13,726 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 16 | 13,726 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 32 | 13,726 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 64 | 13,726 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 256 | 13,726 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 1024 | 13,726 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 4096 | 13,726 | 1.00 | 1.000 | 1.000 | 1.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Pro | 1 | 29 | 7.10 | 4.90 | 1.45x |
| MiMo-V2.6-Pro | 2 | 29 | 12.36 | 6.65 | 1.86x |
| MiMo-V2.6-Pro | 4 | 29 | 19.23 | 8.80 | 2.19x |
| MiMo-V2.6-Pro | 8 | 29 | 25.41 | 11.17 | 2.27x |
| MiMo-V2.6-Pro | 16 | 29 | 28.39 | 13.54 | 2.10x |
| MiMo-V2.6-Pro | 32 | 29 | 28.96 | 15.65 | 1.85x |
| MiMo-V2.6-Pro | 64 | 29 | 29.00 | 17.22 | 1.68x |
| MiMo-V2.6-Pro | 1 | 37 | 7.28 | 5.22 | 1.40x |
| MiMo-V2.6-Pro | 2 | 37 | 13.02 | 7.15 | 1.82x |
| MiMo-V2.6-Pro | 4 | 37 | 21.18 | 9.68 | 2.19x |
| MiMo-V2.6-Pro | 8 | 37 | 29.76 | 12.54 | 2.37x |
| MiMo-V2.6-Pro | 16 | 37 | 35.17 | 15.50 | 2.27x |
| MiMo-V2.6-Pro | 32 | 37 | 36.79 | 18.20 | 2.02x |
| MiMo-V2.6-Pro | 64 | 37 | 36.98 | 20.26 | 1.83x |
| MiMo-V2.6-Pro | 1 | 46 | 7.42 | 5.50 | 1.35x |
| MiMo-V2.6-Pro | 2 | 46 | 13.52 | 7.59 | 1.78x |
| MiMo-V2.6-Pro | 4 | 46 | 22.73 | 10.49 | 2.17x |
| MiMo-V2.6-Pro | 8 | 46 | 33.57 | 13.83 | 2.43x |
| MiMo-V2.6-Pro | 16 | 46 | 41.88 | 17.38 | 2.41x |
| MiMo-V2.6-Pro | 32 | 46 | 45.27 | 20.70 | 2.19x |
| MiMo-V2.6-Pro | 64 | 46 | 45.91 | 23.28 | 1.97x |
| MiMo-V2.6-Pro | 1 | 57 | 7.53 | 5.78 | 1.30x |
| MiMo-V2.6-Pro | 2 | 57 | 13.93 | 8.03 | 1.73x |
| MiMo-V2.6-Pro | 4 | 57 | 24.08 | 11.32 | 2.13x |
| MiMo-V2.6-Pro | 8 | 57 | 37.12 | 15.14 | 2.45x |
| MiMo-V2.6-Pro | 16 | 57 | 48.84 | 19.32 | 2.53x |
| MiMo-V2.6-Pro | 32 | 57 | 54.96 | 23.35 | 2.35x |
| MiMo-V2.6-Pro | 64 | 57 | 56.63 | 26.54 | 2.13x |
| MiMo-V2.6-Pro | 1 | 58 | 7.53 | 5.80 | 1.30x |
| MiMo-V2.6-Pro | 2 | 58 | 13.96 | 8.07 | 1.73x |
| MiMo-V2.6-Pro | 4 | 58 | 24.18 | 11.39 | 2.12x |
| MiMo-V2.6-Pro | 8 | 58 | 37.40 | 15.25 | 2.45x |
| MiMo-V2.6-Pro | 16 | 58 | 49.41 | 19.49 | 2.54x |
| MiMo-V2.6-Pro | 32 | 58 | 55.80 | 23.57 | 2.37x |
| MiMo-V2.6-Pro | 64 | 58 | 57.59 | 26.82 | 2.15x |
| MiMo-V2.6-Pro | 1 | 71 | 7.62 | 6.05 | 1.26x |
| MiMo-V2.6-Pro | 2 | 71 | 14.28 | 8.50 | 1.68x |
| MiMo-V2.6-Pro | 4 | 71 | 25.27 | 12.16 | 2.08x |
| MiMo-V2.6-Pro | 8 | 71 | 40.48 | 16.51 | 2.45x |
| MiMo-V2.6-Pro | 16 | 71 | 56.05 | 21.42 | 2.62x |
| MiMo-V2.6-Pro | 32 | 71 | 66.08 | 26.26 | 2.52x |
| MiMo-V2.6-Pro | 64 | 71 | 69.74 | 30.17 | 2.31x |
| MiMo-V2.6-Pro | 1 | 72 | 7.62 | 6.07 | 1.26x |
| MiMo-V2.6-Pro | 2 | 72 | 14.30 | 8.53 | 1.68x |
| MiMo-V2.6-Pro | 4 | 72 | 25.34 | 12.22 | 2.07x |
| MiMo-V2.6-Pro | 8 | 72 | 40.68 | 16.60 | 2.45x |
| MiMo-V2.6-Pro | 16 | 72 | 56.50 | 21.56 | 2.62x |
| MiMo-V2.6-Pro | 32 | 72 | 66.82 | 26.45 | 2.53x |
| MiMo-V2.6-Pro | 64 | 72 | 70.65 | 30.41 | 2.32x |
| MiMo-V2.6-Pro | 1 | 77 | 7.65 | 6.15 | 1.24x |
| MiMo-V2.6-Pro | 2 | 77 | 14.40 | 8.67 | 1.66x |
| MiMo-V2.6-Pro | 4 | 77 | 25.66 | 12.47 | 2.06x |
| MiMo-V2.6-Pro | 8 | 77 | 41.64 | 17.02 | 2.45x |
| MiMo-V2.6-Pro | 16 | 77 | 58.68 | 22.22 | 2.64x |
| MiMo-V2.6-Pro | 32 | 77 | 70.43 | 27.38 | 2.57x |
| MiMo-V2.6-Pro | 64 | 77 | 75.12 | 31.59 | 2.38x |
| MiMo-V2.6-Pro | 1 | 78 | 7.65 | 6.16 | 1.24x |
| MiMo-V2.6-Pro | 2 | 78 | 14.41 | 8.70 | 1.66x |
| MiMo-V2.6-Pro | 4 | 78 | 25.72 | 12.52 | 2.06x |
| MiMo-V2.6-Pro | 8 | 78 | 41.81 | 17.10 | 2.45x |
| MiMo-V2.6-Pro | 16 | 78 | 59.09 | 22.35 | 2.64x |
| MiMo-V2.6-Pro | 32 | 78 | 71.13 | 27.56 | 2.58x |
| MiMo-V2.6-Pro | 64 | 78 | 76.01 | 31.82 | 2.39x |
| MiMo-V2.6-Pro | 1 | 85 | 7.68 | 6.26 | 1.23x |
| MiMo-V2.6-Pro | 2 | 85 | 14.52 | 8.89 | 1.63x |
| MiMo-V2.6-Pro | 4 | 85 | 26.11 | 12.83 | 2.03x |
| MiMo-V2.6-Pro | 8 | 85 | 42.98 | 17.63 | 2.44x |
| MiMo-V2.6-Pro | 16 | 85 | 61.83 | 23.21 | 2.66x |
| MiMo-V2.6-Pro | 32 | 85 | 75.84 | 28.78 | 2.64x |
| MiMo-V2.6-Pro | 64 | 85 | 82.06 | 33.36 | 2.46x |
| MiMo-V2.6-Pro | 256 | 85 | 84.08 | 36.77 | 2.29x |
| MiMo-V2.6-Pro | 1 | 87 | 7.69 | 6.29 | 1.22x |
| MiMo-V2.6-Pro | 2 | 87 | 14.55 | 8.95 | 1.63x |
| MiMo-V2.6-Pro | 4 | 87 | 26.21 | 12.92 | 2.03x |
| MiMo-V2.6-Pro | 8 | 87 | 43.28 | 17.78 | 2.43x |
| MiMo-V2.6-Pro | 16 | 87 | 62.56 | 23.44 | 2.67x |
| MiMo-V2.6-Pro | 32 | 87 | 77.13 | 29.11 | 2.65x |
| MiMo-V2.6-Pro | 64 | 87 | 83.74 | 33.79 | 2.48x |
| MiMo-V2.6-Pro | 256 | 87 | 85.95 | 37.27 | 2.31x |
| MiMo-V2.6-Pro | 1 | 88 | 7.69 | 6.30 | 1.22x |
| MiMo-V2.6-Pro | 2 | 88 | 14.57 | 8.97 | 1.62x |
| MiMo-V2.6-Pro | 4 | 88 | 26.26 | 12.96 | 2.03x |
| MiMo-V2.6-Pro | 8 | 88 | 43.43 | 17.85 | 2.43x |
| MiMo-V2.6-Pro | 16 | 88 | 62.92 | 23.55 | 2.67x |
| MiMo-V2.6-Pro | 32 | 88 | 77.76 | 29.28 | 2.66x |
| MiMo-V2.6-Pro | 64 | 88 | 84.58 | 34.00 | 2.49x |
| MiMo-V2.6-Pro | 256 | 88 | 86.89 | 37.51 | 2.32x |
| MiMo-V2.6-Pro | 1 | 89 | 7.69 | 6.32 | 1.22x |
| MiMo-V2.6-Pro | 2 | 89 | 14.58 | 9.00 | 1.62x |
| MiMo-V2.6-Pro | 4 | 89 | 26.31 | 13.00 | 2.02x |
| MiMo-V2.6-Pro | 8 | 89 | 43.58 | 17.92 | 2.43x |
| MiMo-V2.6-Pro | 16 | 89 | 63.27 | 23.67 | 2.67x |
| MiMo-V2.6-Pro | 32 | 89 | 78.39 | 29.44 | 2.66x |
| MiMo-V2.6-Pro | 64 | 89 | 85.41 | 34.21 | 2.50x |
| MiMo-V2.6-Pro | 256 | 89 | 87.82 | 37.76 | 2.33x |
| MiMo-V2.6-Pro | 1 | 113 | 7.76 | 6.57 | 1.18x |
| MiMo-V2.6-Pro | 2 | 113 | 14.84 | 9.56 | 1.55x |
| MiMo-V2.6-Pro | 4 | 113 | 27.23 | 13.82 | 1.97x |
| MiMo-V2.6-Pro | 8 | 113 | 46.43 | 19.46 | 2.39x |
| MiMo-V2.6-Pro | 16 | 113 | 70.43 | 26.12 | 2.70x |
| MiMo-V2.6-Pro | 32 | 113 | 91.80 | 32.99 | 2.78x |
| MiMo-V2.6-Pro | 64 | 113 | 103.96 | 38.79 | 2.68x |
| MiMo-V2.6-Pro | 256 | 113 | 109.22 | 43.17 | 2.53x |
| MiMo-V2.6-Pro | 1 | 116 | 7.76 | 6.60 | 1.18x |
| MiMo-V2.6-Pro | 2 | 116 | 14.86 | 9.62 | 1.55x |
| MiMo-V2.6-Pro | 4 | 116 | 27.32 | 13.91 | 1.96x |
| MiMo-V2.6-Pro | 8 | 116 | 46.71 | 19.63 | 2.38x |
| MiMo-V2.6-Pro | 16 | 116 | 71.17 | 26.40 | 2.70x |
| MiMo-V2.6-Pro | 32 | 116 | 93.27 | 33.39 | 2.79x |
| MiMo-V2.6-Pro | 64 | 116 | 106.10 | 39.31 | 2.70x |
| MiMo-V2.6-Pro | 256 | 116 | 111.76 | 43.79 | 2.55x |
| MiMo-V2.6-Pro | 1 | 118 | 7.77 | 6.62 | 1.17x |
| MiMo-V2.6-Pro | 2 | 118 | 14.88 | 9.66 | 1.54x |
| MiMo-V2.6-Pro | 4 | 118 | 27.37 | 13.97 | 1.96x |
| MiMo-V2.6-Pro | 8 | 118 | 46.90 | 19.74 | 2.38x |
| MiMo-V2.6-Pro | 16 | 118 | 71.66 | 26.58 | 2.70x |
| MiMo-V2.6-Pro | 32 | 118 | 94.22 | 33.66 | 2.80x |
| MiMo-V2.6-Pro | 64 | 118 | 107.49 | 39.65 | 2.71x |
| MiMo-V2.6-Pro | 256 | 118 | 113.44 | 44.20 | 2.57x |
| MiMo-V2.6-Pro | 1 | 123 | 7.78 | 6.66 | 1.17x |
| MiMo-V2.6-Pro | 2 | 123 | 14.91 | 9.76 | 1.53x |
| MiMo-V2.6-Pro | 4 | 123 | 27.51 | 14.10 | 1.95x |
| MiMo-V2.6-Pro | 8 | 123 | 47.34 | 20.02 | 2.36x |
| MiMo-V2.6-Pro | 16 | 123 | 72.82 | 27.03 | 2.69x |
| MiMo-V2.6-Pro | 32 | 123 | 96.54 | 34.30 | 2.81x |
| MiMo-V2.6-Pro | 64 | 123 | 110.91 | 40.49 | 2.74x |
| MiMo-V2.6-Pro | 256 | 123 | 117.57 | 45.20 | 2.60x |
| MiMo-V2.6-Pro | 1 | 124 | 7.78 | 6.67 | 1.17x |
| MiMo-V2.6-Pro | 2 | 124 | 14.92 | 9.78 | 1.53x |
| MiMo-V2.6-Pro | 4 | 124 | 27.54 | 14.13 | 1.95x |
| MiMo-V2.6-Pro | 8 | 124 | 47.42 | 20.08 | 2.36x |
| MiMo-V2.6-Pro | 16 | 124 | 73.04 | 27.11 | 2.69x |
| MiMo-V2.6-Pro | 32 | 124 | 96.99 | 34.42 | 2.82x |
| MiMo-V2.6-Pro | 64 | 124 | 111.58 | 40.65 | 2.74x |
| MiMo-V2.6-Pro | 256 | 124 | 118.39 | 45.40 | 2.61x |
| MiMo-V2.6-Pro | 1 | 132 | 7.79 | 6.73 | 1.16x |
| MiMo-V2.6-Pro | 2 | 132 | 14.97 | 9.93 | 1.51x |
| MiMo-V2.6-Pro | 4 | 132 | 27.73 | 14.33 | 1.94x |
| MiMo-V2.6-Pro | 8 | 132 | 48.06 | 20.50 | 2.34x |
| MiMo-V2.6-Pro | 16 | 132 | 74.74 | 27.79 | 2.69x |
| MiMo-V2.6-Pro | 32 | 132 | 100.46 | 35.40 | 2.84x |
| MiMo-V2.6-Pro | 64 | 132 | 116.80 | 41.93 | 2.79x |
| MiMo-V2.6-Pro | 256 | 132 | 124.79 | 46.93 | 2.66x |
| MiMo-V2.6-Pro | 1 | 133 | 7.79 | 6.74 | 1.16x |
| MiMo-V2.6-Pro | 2 | 133 | 14.98 | 9.95 | 1.51x |
| MiMo-V2.6-Pro | 4 | 133 | 27.76 | 14.35 | 1.93x |
| MiMo-V2.6-Pro | 8 | 133 | 48.13 | 20.55 | 2.34x |
| MiMo-V2.6-Pro | 16 | 133 | 74.94 | 27.87 | 2.69x |
| MiMo-V2.6-Pro | 32 | 133 | 100.87 | 35.52 | 2.84x |
| MiMo-V2.6-Pro | 64 | 133 | 117.43 | 42.08 | 2.79x |
| MiMo-V2.6-Pro | 256 | 133 | 125.57 | 47.11 | 2.67x |
| MiMo-V2.6-Pro | 1 | 144 | 7.81 | 6.81 | 1.15x |
| MiMo-V2.6-Pro | 2 | 144 | 15.04 | 10.15 | 1.48x |
| MiMo-V2.6-Pro | 4 | 144 | 27.99 | 14.61 | 1.92x |
| MiMo-V2.6-Pro | 8 | 144 | 48.89 | 21.11 | 2.32x |
| MiMo-V2.6-Pro | 16 | 144 | 77.01 | 28.74 | 2.68x |
| MiMo-V2.6-Pro | 32 | 144 | 105.21 | 36.79 | 2.86x |
| MiMo-V2.6-Pro | 64 | 144 | 124.13 | 43.74 | 2.84x |
| MiMo-V2.6-Pro | 256 | 144 | 133.97 | 49.10 | 2.73x |
| MiMo-V2.6-Pro | 1 | 170 | 7.84 | 6.96 | 1.13x |
| MiMo-V2.6-Pro | 2 | 170 | 15.16 | 10.56 | 1.44x |
| MiMo-V2.6-Pro | 4 | 170 | 28.43 | 15.13 | 1.88x |
| MiMo-V2.6-Pro | 8 | 170 | 50.34 | 22.28 | 2.26x |
| MiMo-V2.6-Pro | 16 | 170 | 81.07 | 30.55 | 2.65x |
| MiMo-V2.6-Pro | 32 | 170 | 114.00 | 39.48 | 2.89x |
| MiMo-V2.6-Pro | 64 | 170 | 138.21 | 47.31 | 2.92x |
| MiMo-V2.6-Pro | 256 | 170 | 152.17 | 53.40 | 2.85x |
| MiMo-V2.6-Pro | 1 | 173 | 7.84 | 6.97 | 1.12x |
| MiMo-V2.6-Pro | 2 | 173 | 15.17 | 10.61 | 1.43x |
| MiMo-V2.6-Pro | 4 | 173 | 28.47 | 15.19 | 1.87x |
| MiMo-V2.6-Pro | 8 | 173 | 50.49 | 22.41 | 2.25x |
| MiMo-V2.6-Pro | 16 | 173 | 81.47 | 30.74 | 2.65x |
| MiMo-V2.6-Pro | 32 | 173 | 114.90 | 39.77 | 2.89x |
| MiMo-V2.6-Pro | 64 | 173 | 139.69 | 47.69 | 2.93x |
| MiMo-V2.6-Pro | 256 | 173 | 154.13 | 53.87 | 2.86x |
| MiMo-V2.6-Pro | 1 | 231 | 7.88 | 7.19 | 1.10x |
| MiMo-V2.6-Pro | 2 | 231 | 15.33 | 11.34 | 1.35x |
| MiMo-V2.6-Pro | 4 | 231 | 29.08 | 16.14 | 1.80x |
| MiMo-V2.6-Pro | 8 | 231 | 52.57 | 24.42 | 2.15x |
| MiMo-V2.6-Pro | 16 | 231 | 87.55 | 33.78 | 2.59x |
| MiMo-V2.6-Pro | 32 | 231 | 128.92 | 44.54 | 2.89x |
| MiMo-V2.6-Pro | 64 | 231 | 163.68 | 54.17 | 3.02x |
| MiMo-V2.6-Pro | 256 | 231 | 187.01 | 61.81 | 3.03x |
| MiMo-V2.6-Pro | 1 | 347 | 7.92 | 7.43 | 1.07x |
| MiMo-V2.6-Pro | 2 | 347 | 15.50 | 12.32 | 1.26x |
| MiMo-V2.6-Pro | 4 | 347 | 29.71 | 17.67 | 1.68x |
| MiMo-V2.6-Pro | 8 | 347 | 54.77 | 26.85 | 2.04x |
| MiMo-V2.6-Pro | 16 | 347 | 94.25 | 38.30 | 2.46x |
| MiMo-V2.6-Pro | 32 | 347 | 145.44 | 51.79 | 2.81x |
| MiMo-V2.6-Pro | 64 | 347 | 194.20 | 63.82 | 3.04x |
| MiMo-V2.6-Pro | 256 | 347 | 231.86 | 73.74 | 3.14x |
| MiMo-V2.6-Pro | 1024 | 347 | 232.44 | 73.90 | 3.15x |
| MiMo-V2.6-Pro | 1 | 1300 | 7.98 | 7.84 | 1.02x |
| MiMo-V2.6-Pro | 2 | 1300 | 15.74 | 14.58 | 1.08x |
| MiMo-V2.6-Pro | 4 | 1300 | 30.66 | 23.86 | 1.29x |
| MiMo-V2.6-Pro | 8 | 1300 | 58.20 | 34.07 | 1.71x |
| MiMo-V2.6-Pro | 16 | 1300 | 105.35 | 52.24 | 2.02x |
| MiMo-V2.6-Pro | 32 | 1300 | 175.30 | 76.45 | 2.29x |
| MiMo-V2.6-Pro | 64 | 1300 | 255.36 | 96.24 | 2.65x |
| MiMo-V2.6-Pro | 256 | 1300 | 331.29 | 116.62 | 2.84x |
| MiMo-V2.6-Pro | 1024 | 1300 | 332.59 | 116.97 | 2.84x |
| MiMo-V2.6-Pro | 1 | 6992 | 8.00 | 7.97 | 1.00x |
| MiMo-V2.6-Pro | 2 | 6992 | 15.82 | 15.57 | 1.02x |
| MiMo-V2.6-Pro | 4 | 6992 | 30.95 | 29.14 | 1.06x |
| MiMo-V2.6-Pro | 8 | 6992 | 59.27 | 48.78 | 1.22x |
| MiMo-V2.6-Pro | 16 | 6992 | 108.97 | 69.72 | 1.56x |
| MiMo-V2.6-Pro | 32 | 6992 | 185.73 | 97.14 | 1.91x |
| MiMo-V2.6-Pro | 64 | 6992 | 278.52 | 137.33 | 2.03x |
| MiMo-V2.6-Pro | 256 | 6992 | 372.01 | 176.29 | 2.11x |
| MiMo-V2.6-Pro | 1024 | 6992 | 373.67 | 176.92 | 2.11x |
| MiMo-V2.6-Pro | 4096 | 6992 | 373.67 | 176.92 | 2.11x |

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
| gpu | MiMo-V2.6-Pro | 1 | 15.80 | 2.9% |
| rom | MiMo-V2.6-Pro | 1 | 15.80 | 9.2% |

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
| MiMo-V2.6-Pro | 1 | 72 | 98.71% | 659.09 | 9.27 |
| MiMo-V2.6-Pro | 2 | 2 | 37.81% | 399.69 | 9.27 |

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
| MiMo-V2.6-Pro | 1 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 12.0 | 49,265.7 |
| MiMo-V2.6-Pro | 2 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 12.0 | 49,265.7 |
| MiMo-V2.6-Pro | 4 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 12.0 | 49,265.7 |
| MiMo-V2.6-Pro | 8 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 12.0 | 49,265.7 |
| MiMo-V2.6-Pro | 16 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 12.0 | 49,265.7 |
| MiMo-V2.6-Pro | 32 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 12.0 | 49,265.7 |
| MiMo-V2.6-Pro | 64 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 12.0 | 49,265.7 |
| MiMo-V2.6-Pro | 256 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 12.0 | 49,265.7 |
| MiMo-V2.6-Pro | 1024 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 12.0 | 49,265.7 |
| MiMo-V2.6-Pro | 4096 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 12.0 | 49,265.7 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 388 |
| gpu | kv_read | 461 |
| gpu | link_latency | 529 |
| gpu | thermal | 296 |
| gpu | weight_read | 146 |
| rom | compute | 106 |
| rom | infeasible | 2721 |
| rom | kv_read | 106 |
| rom | link_latency | 182 |
| rom | weight_read | 95 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 388 |
| rom | CAPACITY | 2721 |

## Mechanical consistency audit

**FAIL** over 66,795 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x139', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x141', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x154', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x167', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x222', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x232', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x242', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x243', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x333', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x139', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x141', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x154', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x167', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x222', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x232', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x242', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x243', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x333', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x139', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x141', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x154', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x167', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x222', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x232', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x242', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x243', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x333', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x113', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x139', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x141', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x154', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x167', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x222', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x232', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x242', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x243', 'MiMo-V2.6-Pro', 1)

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

# Area-constrained roofline: n5_vs_b200-mimo-v26-pro-8k

> CANDIDATE MODEL under n5_vs_b200: MiMo-V2.6-Pro at 8,192 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 42x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 1 device. On the GPU side the correction reaches 5x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 48 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Pro takes 2 x 46,225 mm2 (92,450 mm2, wafer, KV in SRAM) at 4,764 tok/s per user and 52 tok/s per 1,000 mm2, holding 1 session, against 58 copies of one unified HBM die at the same silicon: 9.5x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Pro on 138,675 mm2 of ROM silicon at 4,947 tok/s per user against 139,200 mm2 of b200_sxm-x87-nvl72-hybrid at 494 tok/s: **10.0x**, ROM binding on `layer_fixed_latency` and the GPU on `layer_fixed_latency`. It holds 5,694 resident sessions against the GPU cluster's 29,488. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 3.87x to it.** At 114,100 mm2 on MiMo-V2.6-Pro the pipeline-only GPU delivers 131.54 tok/s and the same silicon running tensor delivers 509 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (MiMo-V2.6-Pro, ROM binding on `link_latency`) to 3.87x (MiMo-V2.6-Pro, ROM binding on `weight_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Pro engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 301 to 32,194 tok/s, and its rate with every slot occupied from 31,007 to 32,194. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 103 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,010 us over NVLink, capping per-user decode at 990 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 300.9 us and cap it at 3,324 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 6 of 10 operating points and an array 4; on tokens per second per square millimetre the same points go 9 to the array and 1 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 174 of 4908 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 54.3x of aggregate throughput (MiMo-V2.6-Pro). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 9.53x, on MiMo-V2.6-Pro at batch 4096, where the busiest region carries 3.17x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 44 of 4,908 feasible points (0.9%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `MiMo-V2.6-Pro/b200_sxm-x16-pipeline` at batch 4096 on 25,600 mm2, throttled 1.06x from 9 to 9 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 81% weight read against 80.6% weight read. The ROM sweep is not what melts it.


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

### MiMo-V2.6-Pro at 8,192 tokens

**Recommended: `ROM-N5-native-SRAMKV-wafer-hybrid-x2`** -- 2 x 46,225 mm2 wafers, 92,450 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **4,763.9 tok/s per user** (0.21 ms/token), binding on `layer_fixed_latency`
- **51.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,764 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 5,895 W at 0.064 W/mm2, 1,237.4 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 58 copies of one unified HBM die -- `b200_sxm-x58-nvl72-tensor`, 92,800 mm2, area ratio 0.9962 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 92,450 | 92,800 | 0.9962 |
| user tok/s | 4,763.9 | 504.1 | 9.45x |
| aggregate tok/s | 4,764 | 504 | 0.62x |
| resident sessions | 1 | 19,247 | -- |
| J/token | 1.2374 | 44.5120 | 36.0x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 19,247 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x71-nvl72-tensor` at 113,600 mm2 and 509.0 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,763.9 | 51.5 | 1 | 9.45x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,965.7 | 26.9 | 7,592 | 9.87x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-hybrid-x95` | 77,425 | 2,681.7 | 34.6 | 1 | 5.38x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,763.9 | 51.5 | 1 | 9.45x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,763.9 | 51.5 | -- | 51.5 | ACCEPT |
| `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 4,947.3 | 35.7 | 4.0 | 51.5 | stop |
| `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,965.7 | 26.9 | 2.2 | 51.5 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x2` **<-- recommended** | 92,450 | 2 | 4,763.9 | 4,764 | 51.5 | 1 | `layer_fixed_latency` | 5,895 | 1,237.4 | `b200_sxm-x58-nvl72-tensor` | 9.45x |
| `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3 | 4,947.3 | 14,842 | 35.7 | 5,694 | `layer_fixed_latency` | 13,843 | 2,670.0 | `b200_sxm-x87-nvl72-hybrid` | 10.01x |
| `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4 | 4,965.7 | 19,863 | 26.9 | 7,592 | `layer_fixed_latency` | 20,987 | 4,034.4 | `b200_sxm-x116-nvl72-hybrid` | 9.87x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 348 | densest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 85,575 | 3,433.0 | 40.1 | 1 |
| array | 348 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 125,510 | 4,293.8 | 34.2 | 33,988 |
| array | 348 | smallest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x95` | 77,425 | 2,681.7 | 34.6 | 1 |
| wafer | 66 | densest | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,763.9 | 51.5 | 1 |
| wafer | 66 | fastest | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,965.7 | 26.9 | 7,592 |
| wafer | 66 | smallest | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,763.9 | 51.5 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 125,510 | 4,293.8 | 42,938 | 33,988 | 15,527 | 3,040.0 | `layer_fixed_latency` | `b200_sxm-x78-nvl72-hybrid` | 490.3 | 26,310 | 59,944.4 | 1.006 | 8.76x | 19.7x |
| 1 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,965.7 | 19,863 | 7,592 | 20,987 | 4,034.4 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 503.0 | 39,729 | 85,009.8 | 0.996 | 9.87x | 21.1x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 4,248.1 | 63,722 | 50,100 | 23,884 | 4,726.0 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 503.0 | 39,729 | 85,009.8 | 0.997 | 8.45x | 18.0x |
| 1 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,965.7 | -- | 7,592 | -- | 4,034.4 | -- | -- | -- | -- | -- | 1.001 | 1.17x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 125,510 | 4,293.8 | 42,938 | 33,988 | 15,527 | 1,552.0 | `layer_fixed_latency` | `b200_sxm-x78-nvl72-hybrid` | 490.3 | 26,310 | 32,067.0 | 1.006 | 8.76x | 20.7x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,965.7 | 19,863 | 7,592 | 20,987 | 2,049.2 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 503.0 | 39,729 | 44,599.7 | 0.996 | 9.87x | 21.8x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 4,248.1 | 63,722 | 50,100 | 23,884 | 2,395.0 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 503.0 | 39,729 | 44,599.7 | 0.997 | 8.45x | 18.6x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,965.7 | -- | 7,592 | -- | 2,049.2 | -- | -- | -- | -- | -- | 1.001 | 1.17x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 125,510 | 4,293.8 | 42,938 | 33,988 | 15,527 | 808.0 | `layer_fixed_latency` | `b200_sxm-x78-nvl72-hybrid` | 477.9 | 26,310 | 16,989.9 | 1.006 | 8.98x | 21.0x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,965.7 | 19,863 | 7,592 | 20,987 | 1,056.6 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 493.6 | 39,729 | 23,282.5 | 0.996 | 10.06x | 22.0x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 4,248.1 | 63,722 | 50,100 | 23,884 | 1,229.5 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 493.6 | 39,729 | 23,282.5 | 0.997 | 8.61x | 18.9x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,965.7 | -- | 7,592 | -- | 1,056.6 | -- | -- | -- | -- | -- | 1.001 | 1.17x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x154` | 125,510 | 4,293.8 | 42,938 | 33,988 | 15,527 | 436.0 | `layer_fixed_latency` | `b200_sxm-x78-nvl72-hybrid` | 455.6 | 26,310 | 9,424.5 | 1.006 | 9.42x | 21.6x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,952.9 | 39,623 | 7,592 | 22,252 | 561.6 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 476.1 | 39,729 | 12,597.1 | 0.996 | 10.40x | 22.4x |
| 8 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 4,248.1 | 63,722 | 50,100 | 23,884 | 646.8 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 476.1 | 39,729 | 12,597.1 | 0.997 | 8.92x | 19.5x |
| 8 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,952.9 | -- | 7,592 | -- | 561.6 | -- | -- | -- | -- | -- | 1.001 | 1.17x wafer/array | -- |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 239,610 | 4,249.4 | 80,739 | 64,888 | 30,819 | 441.3 | `layer_fixed_latency` | `b200_sxm-x150-nvl72-hybrid` | 456.9 | 51,735 | 8,914.9 | 0.998 | 9.30x | 20.2x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,899.2 | 107,782 | 22,777 | 56,098 | 691.7 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 487.5 | 121,302 | 17,709.8 | 0.999 | 10.05x | 25.6x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x294-romfill` | 239,610 | 4,179.8 | 154,654 | 64,888 | 35,550 | 255.8 | `layer_fixed_latency` | `b200_sxm-x150-nvl72-hybrid` | 417.5 | 51,735 | 5,321.2 | 0.998 | 10.01x | 20.8x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,678.8 | 201,189 | 22,777 | 62,078 | 392.6 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 464.2 | 121,302 | 9,804.6 | 0.999 | 10.08x | 25.0x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 319,480 | 3,902.5 | 249,760 | 86,517 | 49,673 | 198.9 | `layer_fixed_latency` | `b200_sxm-x200-nvl72-hybrid` | 387.1 | 69,392 | 3,970.2 | 0.998 | 10.08x | 20.0x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,970.0 | 341,421 | 22,777 | 71,055 | 257.6 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 426.2 | 121,302 | 5,775.1 | 0.999 | 9.31x | 22.4x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 319,480 | 2,400.0 | 614,394 | 86,517 | 72,262 | 117.6 | `weight_read` | `b200_sxm-x200-nvl72-hybrid` | 266.4 | 69,392 | 1,663.1 | 0.998 | 9.01x | 14.1x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,311.8 | 591,823 | 22,777 | 85,351 | 144.2 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 310.8 | 121,302 | 2,360.5 | 0.999 | 7.44x | 16.4x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 881.9 | 903,087 | 75,040 | 87,583 | 97.0 | `weight_read` | `b200_sxm-x173-nvl72-hybrid` | 152.2 | 59,857 | 615.7 | 1.001 | 5.79x | 6.3x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 792.6 | 811,607 | 22,777 | 98,756 | 121.7 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 197.6 | 121,302 | 991.1 | 0.999 | 4.01x | 8.1x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 319,480 | 345.6 | 1,415,486 | 86,517 | 121,147 | 85.6 | `weight_read` | `b200_sxm-x200-nvl72-hybrid` | 89.2 | 69,392 | 347.0 | 0.998 | 3.87x | 4.1x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 554,700 | 215.4 | 882,186 | 22,777 | 124,173 | 140.8 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 114.4 | 121,302 | 472.1 | 0.999 | 1.88x | 3.4x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | wafer | SRAM | 1 |
| 2-16 | `ROM-N5-native-HBMKV-array-hw-hybrid-x123` | 100,245 | array | HBM | 27,147 |
| 32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x151` | 123,065 | array | HBM | 33,326 |
| 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 138,550 | array | HBM | 37,520 |
| 256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x196` | 159,740 | array | HBM | 43,258 |
| 1024 | `ROM-N5-native-HBMKV-array-hw-pipeline-x227` | 185,005 | array | HBM | 50,100 |
| 4096 | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | array | HBM | 75,040 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Pro | HBM | rom | 103, 112, 113, 123, 140, 147, 151, 153, 154, 170, 196, 227, 294, 340, 392 |
| MiMo-V2.6-Pro | HBM | sram | 103, 112, 113, 123, 140, 147, 151, 153, 154, 170, 196, 227, 294, 340, 392 |
| MiMo-V2.6-Pro | SRAM | rom | 95, 99, 103, 105, 109, 113, 114, 137, 170, 182, 227, 273, 340, 364 |
| MiMo-V2.6-Pro | SRAM | sram | 95, 99, 103, 105, 109, 113, 114, 137, 170, 182, 227, 273, 340, 364 |

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
| MiMo-V2.6-Pro | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 1 | 57 on `rom_wafer_express` | 3.00 | centre_mesh, one_shot | 162.98 | 30.98 | 20.62 | 34.44 | 4,763.9 |
| MiMo-V2.6-Pro | `b200_sxm-x58-nvl72-tensor` | 1 | 58 | 3.00 | measured_floor | 1,366.30 | 511.63 | 105.90 | 357.43 | 504.1 |
| MiMo-V2.6-Pro | `b200_sxm-x58-nvl72-tensor` | 64 | 58 | 3.00 | measured_floor | 1,366.30 | 992.31 | 1,199.72 | 712.47 | 281.0 |

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
(5.563e+11 B/s/mm2).

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

**The thermal limit binds here, and this is the first version of this
study in which it could.**
Static power is charged per mm2 per second whether or not a byte moves,
so the coolable step time solves
`t >= E_dynamic / (cooling_limit - P_static)` rather than dividing the
total energy by the total limit. Under the old rule stretching a step
always reduced modelled power, so every design was coolable at some speed
and `thermal_scale` was exactly 1.0 at all 11,747 feasible points across
both studies.

- **44 of 4,908 feasible points (0.9%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 44.
- By area class: large array (5,000-40,000 mm2) 5, wafer (>=40,000 mm2) 39.
- By KV store: hbm 44.
- By batch: B=256 1, B=1024 14, B=4096 29.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 45% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 256 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 120 | 5 | 54.8% | 100.0% | 0.625 | 64% |
| gpu | wafer (>=40,000 mm2) | 1,820 | 39 | 41.2% | 100.0% | 0.625 | 85% |
| rom | large array (5,000-40,000 mm2) | 36 | 0 | 13.1% | 13.8% | 0.069 | 99% |
| rom | wafer (>=40,000 mm2) | 2,932 | 0 | 24.2% | 80.3% | 0.402 | 83% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `MiMo-V2.6-Pro/b200_sxm-x16-pipeline` | MiMo-V2.6-Pro | 4096 | 25,600 | hbm | 1.057x | 16,000.0 / 16,000.0 W | 35% | 9.0 | 9.5 |
| `MiMo-V2.6-Pro/b200_sxm-x24-pipeline` | MiMo-V2.6-Pro | 4096 | 38,400 | hbm | 1.049x | 24,000.0 / 24,000.0 W | 35% | 9.8 | 10.2 |
| `MiMo-V2.6-Pro/b200_sxm-x26-pipeline` | MiMo-V2.6-Pro | 4096 | 41,600 | hbm | 1.047x | 26,000.0 / 26,000.0 W | 35% | 9.9 | 10.4 |
| `MiMo-V2.6-Pro/b200_sxm-x27-pipeline` | MiMo-V2.6-Pro | 4096 | 43,200 | hbm | 1.047x | 27,000.0 / 27,000.0 W | 35% | 10.0 | 10.5 |
| `MiMo-V2.6-Pro/b200_sxm-x29-pipeline` | MiMo-V2.6-Pro | 4096 | 46,400 | hbm | 1.046x | 29,000.0 / 29,000.0 W | 35% | 10.2 | 10.7 |
| `MiMo-V2.6-Pro/b200_sxm-x30-pipeline` | MiMo-V2.6-Pro | 4096 | 48,000 | hbm | 1.045x | 30,000.0 / 30,000.0 W | 35% | 10.3 | 10.8 |
| `MiMo-V2.6-Pro/b200_sxm-x48-pipeline` | MiMo-V2.6-Pro | 4096 | 76,800 | hbm | 1.038x | 48,000.0 / 48,000.0 W | 35% | 12.0 | 12.4 |
| `MiMo-V2.6-Pro/b200_sxm-x50-pipeline` | MiMo-V2.6-Pro | 4096 | 80,000 | hbm | 1.037x | 50,000.0 / 50,000.0 W | 35% | 12.2 | 12.6 |
| `MiMo-V2.6-Pro/b200_sxm-x52-pipeline` | MiMo-V2.6-Pro | 4096 | 83,200 | hbm | 1.037x | 52,000.0 / 52,000.0 W | 35% | 12.4 | 12.8 |
| `MiMo-V2.6-Pro/b200_sxm-x53-pipeline` | MiMo-V2.6-Pro | 4096 | 84,800 | hbm | 1.037x | 53,000.0 / 53,000.0 W | 35% | 12.5 | 12.9 |
| `MiMo-V2.6-Pro/b200_sxm-x16-pipeline` | MiMo-V2.6-Pro | 1024 | 25,600 | hbm | 1.036x | 16,000.0 / 16,000.0 W | 35% | 13.6 | 14.1 |
| `MiMo-V2.6-Pro/b200_sxm-x56-pipeline` | MiMo-V2.6-Pro | 4096 | 89,600 | hbm | 1.036x | 56,000.0 / 56,000.0 W | 35% | 12.8 | 13.2 |

The worst point's dynamic energy is weight read 80.6%, kv read 17.0%, arithmetic 2.2%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| MiMo-V2.6-Pro | 1 | 92,450 | `MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 1.237406 | 5,894.8 | layer_fixed_latency | `MiMo-V2.6-Pro/b200_sxm-x58-nvl72-tensor` | 44.511957 | 22,437.4 | layer_fixed_latency | 35.97x |
| MiMo-V2.6-Pro | 2 | 138,675 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3` | 1.367003 | 13,842.6 | layer_fixed_latency | `MiMo-V2.6-Pro/b200_sxm-x87-nvl72-hybrid` | 35.035313 | 34,629.4 | layer_fixed_latency | 25.63x |
| MiMo-V2.6-Pro | 4 | 138,675 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3` | 0.719394 | 14,781.4 | layer_fixed_latency | `MiMo-V2.6-Pro/b200_sxm-x87-nvl72-hybrid` | 18.480239 | 35,686.3 | layer_fixed_latency | 25.69x |
| MiMo-V2.6-Pro | 8 | 138,675 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3` | 0.405944 | 16,211.3 | layer_fixed_latency | `MiMo-V2.6-Pro/b200_sxm-x87-nvl72-hybrid` | 10.175927 | 37,602.2 | layer_fixed_latency | 25.07x |
| MiMo-V2.6-Pro | 16 | 277,350 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 0.391968 | 31,201.6 | layer_fixed_latency | `MiMo-V2.6-Pro/b200_sxm-x173-nvl72-hybrid` | 9.882001 | 73,437.9 | layer_fixed_latency | 25.21x |
| MiMo-V2.6-Pro | 32 | 554,700 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.392616 | 62,077.7 | layer_fixed_latency | `MiMo-V2.6-Pro/b200_sxm-x347-nvl72-hybrid` | 9.804643 | 145,653.2 | layer_fixed_latency | 24.97x |
| MiMo-V2.6-Pro | 64 | 277,100 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.183976 | 44,421.4 | layer_fixed_latency | `MiMo-V2.6-Pro/b200_sxm-x173-nvl72-hybrid` | 3.666843 | 88,017.3 | layer_fixed_latency | 19.93x |
| MiMo-V2.6-Pro | 256 | 319,480 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill` | 0.117615 | 72,261.8 | weight_read | `MiMo-V2.6-Pro/b200_sxm-x200-nvl72-hybrid` | 1.663052 | 113,418.0 | layer_fixed_latency | 14.14x |
| MiMo-V2.6-Pro | 1024 | 239,610 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x294` | 0.091698 | 79,161.3 | weight_read | `MiMo-V2.6-Pro/b200_sxm-x150-nvl72-hybrid` | 0.689845 | 103,107.5 | weight_read | 7.52x |
| MiMo-V2.6-Pro | 4096 | 319,480 | `MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392` | 0.085587 | 121,146.8 | weight_read | `MiMo-V2.6-Pro/b200_sxm-x200-nvl72-hybrid` | 0.346969 | 126,755.4 | link_latency | 4.05x |

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
| MiMo-V2.6-Pro | 8,192 | 1,020 B | 566.0 GB | 4.44 | 0.459 GB | 0.459 GB | 85.8 |

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
| MiMo-V2.6-Pro | 2 | 92,450 | 5,823.4 | wafer-pipeline | 4,763.9 | wafer-hybrid | 1.22x | 644.8 | pipeline | 504.1 | tensor | 1.28x | 9.03x | 9.45x | 1.05x |
| MiMo-V2.6-Pro | 3 | 138,675 | 6,018.9 | wafer-pipeline | 4,947.3 | wafer-hybrid | 1.22x | 653.1 | pipeline | 494.2 | hybrid | 1.32x | 9.22x | 10.01x | 1.09x |
| MiMo-V2.6-Pro | 4 | 184,900 | 6,051.0 | wafer-pipeline | 4,965.7 | wafer-hybrid | 1.22x | 660.7 | pipeline | 503.0 | hybrid | 1.31x | 9.16x | 9.87x | 1.08x |
| MiMo-V2.6-Pro | 6 | 277,350 | 6,073.0 | wafer-pipeline | 4,959.9 | wafer-hybrid | 1.22x | 668.4 | pipeline | 502.3 | hybrid | 1.33x | 9.09x | 9.88x | 1.09x |
| MiMo-V2.6-Pro | 8 | 369,800 | 6,085.2 | wafer-pipeline | 4,928.8 | wafer-hybrid | 1.23x | 672.4 | pipeline | 501.7 | hybrid | 1.34x | 9.05x | 9.82x | 1.09x |
| MiMo-V2.6-Pro | 12 | 554,700 | 6,090.7 | wafer-pipeline | 4,918.3 | wafer-hybrid | 1.24x | 676.5 | pipeline | 505.7 | hybrid | 1.34x | 9.00x | 9.73x | 1.08x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.05x to 1.09x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Pro | 1 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 4,965.7 | 19,862.8 | layer_fixed_latency | MiMo-V2.6-Pro/b200_sxm-x116-nvl72-hybrid | 185,600 | 1.00x | hybrid | 515.95 | 503.0 | 1,006.0 | layer_fixed_latency | 9.87x | 1.30x | 37.75x | 9.87x |
| MiMo-V2.6-Pro | 1 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x95 | 77,425 | 2,681.7 | 2,681.7 | layer_fixed_latency | MiMo-V2.6-Pro/b200_sxm-x48-nvl72-tensor | 76,800 | 1.01x | tensor | 511.60 | 498.5 | 498.5 | layer_fixed_latency | 5.38x | 0.42x | 20.31x | 5.38x |
| MiMo-V2.6-Pro | 2 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 4,965.7 | 19,862.8 | layer_fixed_latency | MiMo-V2.6-Pro/b200_sxm-x116-nvl72-hybrid | 185,600 | 1.00x | hybrid | 515.95 | 503.0 | 1,006.0 | layer_fixed_latency | 9.87x | 1.30x | 37.75x | 9.87x |
| MiMo-V2.6-Pro | 2 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x103 | 83,945 | 2,600.0 | 5,200.1 | layer_fixed_latency | MiMo-V2.6-Pro/b200_sxm-x52-nvl72-tensor | 83,200 | 1.01x | tensor | 519.23 | 490.9 | 981.8 | layer_fixed_latency | 5.30x | 0.76x | 19.70x | 5.30x |
| MiMo-V2.6-Pro | 4 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 4,965.7 | 19,862.8 | layer_fixed_latency | MiMo-V2.6-Pro/b200_sxm-x116-nvl72-hybrid | 185,600 | 1.00x | hybrid | 523.84 | 493.6 | 1,974.2 | layer_fixed_latency | 10.06x | 1.30x | 37.75x | 10.06x |
| MiMo-V2.6-Pro | 4 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x103 | 83,945 | 2,553.5 | 10,214.1 | layer_fixed_latency | MiMo-V2.6-Pro/b200_sxm-x52-nvl72-tensor | 83,200 | 1.01x | tensor | 534.46 | 472.3 | 1,889.1 | layer_fixed_latency | 5.41x | 1.49x | 19.35x | 5.41x |
| MiMo-V2.6-Pro | 8 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 4,952.9 | 39,623.5 | layer_fixed_latency | MiMo-V2.6-Pro/b200_sxm-x116-nvl72-hybrid | 185,600 | 1.00x | hybrid | 539.61 | 476.1 | 3,809.2 | layer_fixed_latency | 10.40x | 2.60x | 37.65x | 10.40x |
| MiMo-V2.6-Pro | 8 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x103 | 83,945 | 2,117.3 | 16,938.7 | compute | MiMo-V2.6-Pro/b200_sxm-x52-nvl72-tensor | 83,200 | 1.01x | tensor | 564.91 | 440.4 | 3,523.5 | layer_fixed_latency | 4.81x | 2.47x | 16.05x | 4.81x |
| MiMo-V2.6-Pro | 16 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,899.2 | 107,781.7 | layer_fixed_latency | MiMo-V2.6-Pro/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 541.79 | 487.5 | 7,800.3 | layer_fixed_latency | 10.05x | 2.36x | 37.25x | 10.05x |
| MiMo-V2.6-Pro | 16 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x103 | 83,945 | 1,443.6 | 23,097.2 | compute | MiMo-V2.6-Pro/b200_sxm-x52-nvl72-tensor | 83,200 | 1.01x | tensor | 625.83 | 392.3 | 6,277.5 | layer_fixed_latency | 3.68x | 3.37x | 10.94x | 3.68x |
| MiMo-V2.6-Pro | 32 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,678.8 | 201,188.5 | layer_fixed_latency | MiMo-V2.6-Pro/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 569.44 | 464.2 | 14,855.5 | layer_fixed_latency | 10.08x | 4.41x | 35.57x | 10.08x |
| MiMo-V2.6-Pro | 32 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x103 | 83,945 | 868.3 | 27,786.2 | compute | MiMo-V2.6-Pro/b200_sxm-x52-nvl72-tensor | 83,200 | 1.01x | tensor | 747.66 | 331.7 | 10,615.6 | layer_fixed_latency | 2.62x | 2.62x | 6.58x | 2.62x |
| MiMo-V2.6-Pro | 64 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,970.0 | 341,421.0 | layer_fixed_latency | MiMo-V2.6-Pro/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 624.73 | 426.2 | 27,279.7 | layer_fixed_latency | 9.31x | 7.48x | 30.18x | 9.31x |
| MiMo-V2.6-Pro | 64 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x103 | 83,945 | 468.8 | 30,003.7 | compute | MiMo-V2.6-Pro/b200_sxm-x52-nvl72-tensor | 83,200 | 1.01x | tensor | 991.32 | 270.6 | 17,317.1 | layer_fixed_latency | 1.73x | 1.73x | 3.74x | 1.73x |
| MiMo-V2.6-Pro | 256 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill | 319,480 | 2,400.0 | 614,393.7 | weight_read | MiMo-V2.6-Pro/b200_sxm-x200-nvl72-hybrid | 320,000 | 1.00x | hybrid | 1,205.34 | 266.4 | 68,198.7 | layer_fixed_latency | 9.01x | 9.01x | 19.43x | 9.01x |
| MiMo-V2.6-Pro | 256 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x103 | 83,945 | 123.9 | 31,723.3 | compute | MiMo-V2.6-Pro/b200_sxm-x52-nvl72-tensor | 83,200 | 1.01x | tensor | 2,453.27 | 171.8 | 43,971.4 | link_latency | 0.72x | 0.72x | 1.76x | 0.72x |
| MiMo-V2.6-Pro | 1024 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 881.9 | 903,087.4 | weight_read | MiMo-V2.6-Pro/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 3,286.50 | 152.2 | 155,891.1 | link_latency | 5.79x | 5.79x | 13.99x | 5.79x |
| MiMo-V2.6-Pro | 1024 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x103 | 83,945 | 31.3 | 32,099.1 | compute | MiMo-V2.6-Pro/b200_sxm-x52-nvl72-tensor | 83,200 | 1.01x | tensor | 8,301.08 | 78.6 | 80,481.7 | link_latency | 0.40x | 0.40x | 1.11x | 0.40x |
| MiMo-V2.6-Pro | 4096 | fastest | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392 | 319,480 | 345.6 | 1,415,485.7 | weight_read | MiMo-V2.6-Pro/b200_sxm-x200-nvl72-hybrid | 320,000 | 1.00x | hybrid | 5,372.07 | 89.2 | 365,322.2 | link_latency | 3.87x | 3.87x | 12.58x | 3.87x |
| MiMo-V2.6-Pro | 4096 | smallest silicon | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x103 | 83,945 | 7.9 | 32,194.5 | compute | MiMo-V2.6-Pro/b200_sxm-x52-hybrid | 83,200 | 1.01x | hybrid | 5,356.11 | 41.8 | 171,174.7 | weight_read | 0.19x | 0.19x | 0.64x | 0.19x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| MiMo-V2.6-Pro | 16 | 25,600 | 511.28 | 341.38 | 442.2 | 478.1 |
| MiMo-V2.6-Pro | 24 | 38,400 | 511.44 | 341.50 | 468.7 | 509.2 |
| MiMo-V2.6-Pro | 26 | 41,600 | 511.47 | 341.51 | 473.0 | 514.4 |
| MiMo-V2.6-Pro | 27 | 43,200 | 511.48 | 341.52 | 475.0 | 516.7 |
| MiMo-V2.6-Pro | 29 | 46,400 | 511.50 | 341.54 | 478.6 | 520.9 |
| MiMo-V2.6-Pro | 30 | 48,000 | 511.50 | 341.54 | 480.2 | 522.9 |
| MiMo-V2.6-Pro | 48 | 76,800 | 511.60 | 341.61 | 498.5 | 544.7 |
| MiMo-V2.6-Pro | 50 | 80,000 | 511.61 | 341.62 | 499.8 | 546.2 |
| MiMo-V2.6-Pro | 52 | 83,200 | 511.61 | 341.62 | 501.0 | 547.6 |
| MiMo-V2.6-Pro | 53 | 84,800 | 511.62 | 341.63 | 501.6 | 548.3 |
| MiMo-V2.6-Pro | 56 | 89,600 | 511.62 | 341.63 | 503.1 | 550.2 |
| MiMo-V2.6-Pro | 57 | 91,200 | 511.63 | 341.63 | 503.6 | 550.8 |
| MiMo-V2.6-Pro | 58 | 92,800 | 511.63 | 341.64 | 504.1 | 551.3 |
| MiMo-V2.6-Pro | 63 | 100,800 | 511.64 | 341.64 | 506.2 | 553.9 |
| MiMo-V2.6-Pro | 70 | 112,000 | 511.65 | 341.65 | 508.7 | 556.9 |
| MiMo-V2.6-Pro | 71 | 113,600 | 511.65 | 341.65 | 509.0 | 557.3 |
| MiMo-V2.6-Pro | 75 | 120,000 | 515.95 | 343.93 | 488.8 | 533.6 |
| MiMo-V2.6-Pro | 77 | 123,200 | 515.95 | 343.93 | 489.8 | 534.8 |
| MiMo-V2.6-Pro | 78 | 124,800 | 515.95 | 343.93 | 490.3 | 535.4 |
| MiMo-V2.6-Pro | 87 | 139,200 | 515.95 | 343.93 | 494.2 | 540.1 |
| MiMo-V2.6-Pro | 93 | 148,800 | 515.95 | 343.93 | 496.4 | 542.8 |
| MiMo-V2.6-Pro | 100 | 160,000 | 515.95 | 343.93 | 498.7 | 545.5 |
| MiMo-V2.6-Pro | 116 | 185,600 | 515.95 | 343.93 | 503.0 | 550.6 |
| MiMo-V2.6-Pro | 139 | 222,400 | 515.96 | 343.93 | 507.5 | 556.0 |
| MiMo-V2.6-Pro | 150 | 240,000 | 518.22 | 346.21 | 498.2 | 544.9 |
| MiMo-V2.6-Pro | 173 | 276,800 | 518.22 | 346.21 | 502.3 | 549.7 |
| MiMo-V2.6-Pro | 185 | 296,000 | 518.22 | 346.21 | 504.0 | 551.8 |
| MiMo-V2.6-Pro | 200 | 320,000 | 518.24 | 346.21 | 505.9 | 554.1 |
| MiMo-V2.6-Pro | 231 | 369,600 | 520.50 | 348.48 | 501.7 | 549.1 |
| MiMo-V2.6-Pro | 347 | 555,200 | 522.79 | 350.76 | 505.7 | 553.8 |

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
| MiMo-V2.6-Pro | 16 | 25,600 | 132.8 | 442.2 | 377.5 | tensor | 511.28 | 22.6% | layer_fixed_latency |
| MiMo-V2.6-Pro | 24 | 38,400 | 132.6 | 468.7 | 377.2 | tensor | 511.44 | 24.0% | layer_fixed_latency |
| MiMo-V2.6-Pro | 26 | 41,600 | 132.6 | 473.0 | 353.2 | tensor | 511.47 | 24.2% | layer_fixed_latency |
| MiMo-V2.6-Pro | 27 | 43,200 | 132.5 | 475.0 | 357.7 | tensor | 511.48 | 24.3% | layer_fixed_latency |
| MiMo-V2.6-Pro | 29 | 46,400 | 132.5 | 478.6 | 365.9 | tensor | 511.50 | 24.5% | layer_fixed_latency |
| MiMo-V2.6-Pro | 30 | 48,000 | 132.5 | 480.2 | 369.7 | tensor | 511.50 | 24.6% | layer_fixed_latency |
| MiMo-V2.6-Pro | 48 | 76,800 | 132.1 | 498.5 | 376.2 | tensor | 511.60 | 25.5% | layer_fixed_latency |
| MiMo-V2.6-Pro | 50 | 80,000 | 132.0 | 499.8 | 363.3 | tensor | 511.61 | 25.6% | layer_fixed_latency |
| MiMo-V2.6-Pro | 52 | 83,200 | 132.0 | 501.0 | 367.7 | tensor | 511.61 | 25.6% | layer_fixed_latency |
| MiMo-V2.6-Pro | 53 | 84,800 | 131.9 | 501.6 | 369.8 | tensor | 511.62 | 25.7% | layer_fixed_latency |
| MiMo-V2.6-Pro | 56 | 89,600 | 131.9 | 503.1 | 375.9 | tensor | 511.62 | 25.7% | layer_fixed_latency |
| MiMo-V2.6-Pro | 57 | 91,200 | 131.8 | 503.6 | 362.7 | tensor | 511.63 | 25.8% | layer_fixed_latency |
| MiMo-V2.6-Pro | 58 | 92,800 | 131.8 | 504.1 | 364.7 | tensor | 511.63 | 25.8% | layer_fixed_latency |
| MiMo-V2.6-Pro | 63 | 100,800 | 131.7 | 506.2 | 373.8 | tensor | 511.64 | 25.9% | layer_fixed_latency |
| MiMo-V2.6-Pro | 70 | 112,000 | 131.5 | 508.7 | 372.2 | tensor | 511.65 | 26.0% | layer_fixed_latency |
| MiMo-V2.6-Pro | 71 | 113,600 | 131.5 | 509.0 | 373.7 | tensor | 511.65 | 26.0% | layer_fixed_latency |
| MiMo-V2.6-Pro | 75 | 120,000 | 131.5 | 310.0 | 488.8 | hybrid | 515.95 | 25.2% | layer_fixed_latency |
| MiMo-V2.6-Pro | 77 | 123,200 | 131.5 | 310.2 | 489.8 | hybrid | 515.95 | 25.3% | layer_fixed_latency |
| MiMo-V2.6-Pro | 78 | 124,800 | 131.5 | 310.3 | 490.3 | hybrid | 515.95 | 25.3% | layer_fixed_latency |
| MiMo-V2.6-Pro | 87 | 139,200 | 131.5 | 311.1 | 494.2 | hybrid | 515.95 | 25.5% | layer_fixed_latency |
| MiMo-V2.6-Pro | 93 | 148,800 | 131.5 | 311.5 | 496.4 | hybrid | 515.95 | 25.6% | layer_fixed_latency |
| MiMo-V2.6-Pro | 100 | 160,000 | 131.5 | 312.0 | 498.7 | hybrid | 515.95 | 25.7% | layer_fixed_latency |
| MiMo-V2.6-Pro | 116 | 185,600 | 131.5 | 312.8 | 503.0 | hybrid | 515.95 | 26.0% | layer_fixed_latency |
| MiMo-V2.6-Pro | 139 | 222,400 | 131.5 | 313.7 | 507.5 | hybrid | 515.96 | 26.2% | layer_fixed_latency |
| MiMo-V2.6-Pro | 150 | 240,000 | 131.5 | 311.7 | 498.2 | hybrid | 518.22 | 25.8% | layer_fixed_latency |
| MiMo-V2.6-Pro | 173 | 276,800 | 131.5 | 312.2 | 502.3 | hybrid | 518.22 | 26.0% | layer_fixed_latency |
| MiMo-V2.6-Pro | 185 | 296,000 | 131.5 | 312.5 | 504.0 | hybrid | 518.22 | 26.1% | layer_fixed_latency |
| MiMo-V2.6-Pro | 200 | 320,000 | 131.5 | 312.7 | 505.9 | hybrid | 518.24 | 26.2% | layer_fixed_latency |
| MiMo-V2.6-Pro | 231 | 369,600 | 131.5 | 312.0 | 501.7 | hybrid | 520.50 | 26.1% | layer_fixed_latency |
| MiMo-V2.6-Pro | 347 | 555,200 | 131.5 | 312.1 | 505.7 | hybrid | 522.79 | 26.4% | layer_fixed_latency |

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
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x105 | MiMo-V2.6-Pro | 105 | pipeline | rom_package_ucie | rom_board_serdes | 69 | 2.50 us | 40,067.4 tok/s | 400,673.6 tok/s | 52 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.68 us; 17 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.82 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x99 | MiMo-V2.6-Pro | 99 | tensor | rom_package_ucie | rom_board_serdes | 280 | 129.72 us | 770.9 tok/s | 7,708.9 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 140 x all_reduce span 25 on rom_board_serdes (traversals 8.8) = 125.95 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x109 | MiMo-V2.6-Pro | 109 | hybrid | rom_package_ucie | rom_board_serdes | 167 | 6.65 us | 15,033.1 tok/s | 150,330.7 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 27 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.88 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x105 | MiMo-V2.6-Pro | 105 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | MiMo-V2.6-Pro | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 69 | 8.60 us | 11,625.1 tok/s | 116,251.0 tok/s | 68 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-tensor-x95 | MiMo-V2.6-Pro | 95 | tensor | nvlink5 | infiniband_ndr | 280 | 1,004.04 us | 99.6 tok/s | 996.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 663.02 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x2 | MiMo-V2.6-Pro | 2 | tensor | on_wafer_n5 | rom_wafer_serdes | 280 | 300.73 us | 332.5 tok/s | 3,325.2 tok/s | 140 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 269.50 us; 140 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 31.23 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hybrid-x103 | MiMo-V2.6-Pro | 103 | hybrid | nvlink5 | infiniband_ndr | 152 | 368.33 us | 271.5 tok/s | 2,715.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 27.31 us |
| MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | MiMo-V2.6-Pro | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 141 | 269.60 us | 370.9 tok/s | 3,709.2 tok/s | 140 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 269.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x154 | MiMo-V2.6-Pro | 154 | pipeline | rom_package_ucie | rom_board_serdes | 69 | 2.50 us | 40,067.4 tok/s | 400,673.6 tok/s | 52 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.68 us; 17 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.82 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x112 | MiMo-V2.6-Pro | 112 | tensor | rom_package_ucie | rom_board_serdes | 280 | 160.53 us | 622.9 tok/s | 6,229.3 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 140 x all_reduce span 28 on rom_board_serdes (traversals 11.0) = 156.76 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x151 | MiMo-V2.6-Pro | 151 | hybrid | rom_package_ucie | rom_board_serdes | 177 | 7.72 us | 12,952.9 tok/s | 129,529.2 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 37 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 3.95 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-pipeline-x153 | MiMo-V2.6-Pro | 153 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3 | MiMo-V2.6-Pro | 3 | pipeline | on_wafer_n5 | rom_wafer_serdes | 69 | 8.60 us | 11,625.1 tok/s | 116,251.0 tok/s | 68 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-tensor-x103 | MiMo-V2.6-Pro | 103 | tensor | nvlink5 | infiniband_ndr | 280 | 1,004.70 us | 99.5 tok/s | 995.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 663.68 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-tensor-x3 | MiMo-V2.6-Pro | 3 | tensor | on_wafer_n5 | rom_wafer_serdes | 280 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 140 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 269.50 us; 140 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 31.37 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hybrid-x140 | MiMo-V2.6-Pro | 140 | hybrid | nvlink5 | infiniband_ndr | 157 | 379.71 us | 263.4 tok/s | 2,633.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 38.69 us |
| MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | MiMo-V2.6-Pro | 3 | hybrid | on_wafer_n5 | rom_wafer_serdes | 142 | 269.70 us | 370.8 tok/s | 3,707.8 tok/s | 140 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 269.50 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.20 us |
| MiMo-V2.6-Pro/b200_sxm-x16-pipeline | MiMo-V2.6-Pro | 16 | pipeline | nvlink5 | infiniband_ndr | 15 | 19.27 us | 5,190.2 tok/s | 51,902.5 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.99 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x16-tensor | MiMo-V2.6-Pro | 16 | tensor | nvlink5 | infiniband_ndr | 280 | 961.03 us | 104.1 tok/s | 1,040.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x16-hybrid | MiMo-V2.6-Pro | 16 | hybrid | nvlink5 | infiniband_ndr | 141 | 343.29 us | 291.3 tok/s | 2,913.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x16-nvl72-tensor | MiMo-V2.6-Pro | 16 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.38 us | 292.9 tok/s | 2,929.3 tok/s | 140 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 341.38 us |
| MiMo-V2.6-Pro/b200_sxm-x16-expert | MiMo-V2.6-Pro | 16 | expert | nvlink5 | infiniband_ndr | 280 | 639.91 us | 156.3 tok/s | 1,562.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 338.51 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 301.40 us |
| MiMo-V2.6-Pro/b200_sxm-x16-nvl72-expert | MiMo-V2.6-Pro | 16 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.33 us | 196.0 tok/s | 1,959.5 tok/s | 140 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 341.38 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.96 us |
| MiMo-V2.6-Pro/b200_sxm-x24-pipeline | MiMo-V2.6-Pro | 24 | pipeline | nvlink5 | infiniband_ndr | 23 | 30.04 us | 3,329.1 tok/s | 33,290.9 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.49 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x24-tensor | MiMo-V2.6-Pro | 24 | tensor | nvlink5 | infiniband_ndr | 280 | 978.23 us | 102.2 tok/s | 1,022.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 637.21 us |
| MiMo-V2.6-Pro/b200_sxm-x24-hybrid | MiMo-V2.6-Pro | 24 | hybrid | nvlink5 | infiniband_ndr | 142 | 345.57 us | 289.4 tok/s | 2,893.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x24-nvl72-tensor | MiMo-V2.6-Pro | 24 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.50 us | 292.8 tok/s | 2,928.3 tok/s | 140 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 341.50 us |
| MiMo-V2.6-Pro/b200_sxm-x24-expert | MiMo-V2.6-Pro | 24 | expert | nvlink5 | infiniband_ndr | 280 | 633.34 us | 157.9 tok/s | 1,578.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.67 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 295.67 us |
| MiMo-V2.6-Pro/b200_sxm-x24-nvl72-expert | MiMo-V2.6-Pro | 24 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.13 us | 196.0 tok/s | 1,960.3 tok/s | 140 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 341.50 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.64 us |
| MiMo-V2.6-Pro/b200_sxm-x26-pipeline | MiMo-V2.6-Pro | 26 | pipeline | nvlink5 | infiniband_ndr | 25 | 33.53 us | 2,982.6 tok/s | 29,826.1 tok/s | 22 x point_to_point span 2 on nvlink5 (traversals 1.0) = 26.70 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x26-tensor | MiMo-V2.6-Pro | 26 | tensor | nvlink5 | infiniband_ndr | 280 | 986.83 us | 101.3 tok/s | 1,013.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 645.81 us |
| MiMo-V2.6-Pro/b200_sxm-x26-hybrid | MiMo-V2.6-Pro | 26 | hybrid | nvlink5 | infiniband_ndr | 143 | 347.84 us | 287.5 tok/s | 2,874.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x26-nvl72-tensor | MiMo-V2.6-Pro | 26 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.51 us | 292.8 tok/s | 2,928.1 tok/s | 140 x all_reduce span 26 on nvlink5_nvl72 (traversals 2.0) = 341.51 us |
| MiMo-V2.6-Pro/b200_sxm-x26-expert | MiMo-V2.6-Pro | 26 | expert | nvlink5 | infiniband_ndr | 280 | 632.46 us | 158.1 tok/s | 1,581.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.67 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 294.79 us |
| MiMo-V2.6-Pro/b200_sxm-x26-nvl72-expert | MiMo-V2.6-Pro | 26 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.10 us | 196.0 tok/s | 1,960.4 tok/s | 140 x all_reduce span 26 on nvlink5_nvl72 (traversals 2.0) = 341.51 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.59 us |
| MiMo-V2.6-Pro/b200_sxm-x27-pipeline | MiMo-V2.6-Pro | 27 | pipeline | nvlink5 | infiniband_ndr | 26 | 34.74 us | 2,878.4 tok/s | 28,784.2 tok/s | 23 x point_to_point span 2 on nvlink5 (traversals 1.0) = 27.91 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x27-tensor | MiMo-V2.6-Pro | 27 | tensor | nvlink5 | infiniband_ndr | 280 | 986.83 us | 101.3 tok/s | 1,013.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 645.81 us |
| MiMo-V2.6-Pro/b200_sxm-x27-hybrid | MiMo-V2.6-Pro | 27 | hybrid | nvlink5 | infiniband_ndr | 143 | 347.84 us | 287.5 tok/s | 2,874.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x27-nvl72-tensor | MiMo-V2.6-Pro | 27 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.52 us | 292.8 tok/s | 2,928.1 tok/s | 140 x all_reduce span 27 on nvlink5_nvl72 (traversals 2.0) = 341.52 us |
| MiMo-V2.6-Pro/b200_sxm-x27-expert | MiMo-V2.6-Pro | 27 | expert | nvlink5 | infiniband_ndr | 280 | 632.07 us | 158.2 tok/s | 1,582.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.67 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 294.39 us |
| MiMo-V2.6-Pro/b200_sxm-x27-nvl72-expert | MiMo-V2.6-Pro | 27 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.09 us | 196.0 tok/s | 1,960.4 tok/s | 140 x all_reduce span 27 on nvlink5_nvl72 (traversals 2.0) = 341.52 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.57 us |
| MiMo-V2.6-Pro/b200_sxm-x29-pipeline | MiMo-V2.6-Pro | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 37.17 us | 2,690.4 tok/s | 26,904.4 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.34 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x29-tensor | MiMo-V2.6-Pro | 29 | tensor | nvlink5 | infiniband_ndr | 280 | 986.83 us | 101.3 tok/s | 1,013.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 645.81 us |
| MiMo-V2.6-Pro/b200_sxm-x29-hybrid | MiMo-V2.6-Pro | 29 | hybrid | nvlink5 | infiniband_ndr | 143 | 347.84 us | 287.5 tok/s | 2,874.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x29-nvl72-tensor | MiMo-V2.6-Pro | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.54 us | 292.8 tok/s | 2,927.9 tok/s | 140 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 341.54 us |
| MiMo-V2.6-Pro/b200_sxm-x29-expert | MiMo-V2.6-Pro | 29 | expert | nvlink5 | infiniband_ndr | 280 | 631.36 us | 158.4 tok/s | 1,583.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.67 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 293.69 us |
| MiMo-V2.6-Pro/b200_sxm-x29-nvl72-expert | MiMo-V2.6-Pro | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.06 us | 196.1 tok/s | 1,960.5 tok/s | 140 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 341.54 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.53 us |
| MiMo-V2.6-Pro/b200_sxm-x30-pipeline | MiMo-V2.6-Pro | 30 | pipeline | nvlink5 | infiniband_ndr | 29 | 38.38 us | 2,605.4 tok/s | 26,053.7 tok/s | 26 x point_to_point span 2 on nvlink5 (traversals 1.0) = 31.55 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x30-tensor | MiMo-V2.6-Pro | 30 | tensor | nvlink5 | infiniband_ndr | 280 | 986.83 us | 101.3 tok/s | 1,013.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 645.81 us |
| MiMo-V2.6-Pro/b200_sxm-x30-hybrid | MiMo-V2.6-Pro | 30 | hybrid | nvlink5 | infiniband_ndr | 143 | 347.84 us | 287.5 tok/s | 2,874.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.83 us |
| MiMo-V2.6-Pro/b200_sxm-x30-nvl72-tensor | MiMo-V2.6-Pro | 30 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.54 us | 292.8 tok/s | 2,927.9 tok/s | 140 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 341.54 us |
| MiMo-V2.6-Pro/b200_sxm-x30-expert | MiMo-V2.6-Pro | 30 | expert | nvlink5 | infiniband_ndr | 280 | 631.05 us | 158.5 tok/s | 1,584.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 337.67 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 293.38 us |
| MiMo-V2.6-Pro/b200_sxm-x30-nvl72-expert | MiMo-V2.6-Pro | 30 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 510.05 us | 196.1 tok/s | 1,960.6 tok/s | 140 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 341.54 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.51 us |
| MiMo-V2.6-Pro/b200_sxm-x48-pipeline | MiMo-V2.6-Pro | 48 | pipeline | nvlink5 | infiniband_ndr | 47 | 62.35 us | 1,603.8 tok/s | 16,037.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.97 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.38 us |
| MiMo-V2.6-Pro/b200_sxm-x48-tensor | MiMo-V2.6-Pro | 48 | tensor | nvlink5 | infiniband_ndr | 280 | 995.43 us | 100.5 tok/s | 1,004.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 654.42 us |
| MiMo-V2.6-Pro/b200_sxm-x48-hybrid | MiMo-V2.6-Pro | 48 | hybrid | nvlink5 | infiniband_ndr | 145 | 352.40 us | 283.8 tok/s | 2,837.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.38 us |
| MiMo-V2.6-Pro/b200_sxm-x48-nvl72-tensor | MiMo-V2.6-Pro | 48 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.61 us | 292.7 tok/s | 2,927.3 tok/s | 140 x all_reduce span 48 on nvlink5_nvl72 (traversals 2.0) = 341.61 us |
| MiMo-V2.6-Pro/b200_sxm-x48-expert | MiMo-V2.6-Pro | 48 | expert | nvlink5 | infiniband_ndr | 280 | 626.77 us | 159.5 tok/s | 1,595.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.84 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 289.93 us |
| MiMo-V2.6-Pro/b200_sxm-x48-nvl72-expert | MiMo-V2.6-Pro | 48 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.93 us | 196.1 tok/s | 1,961.0 tok/s | 140 x all_reduce span 48 on nvlink5_nvl72 (traversals 2.0) = 341.61 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.32 us |
| MiMo-V2.6-Pro/b200_sxm-x50-pipeline | MiMo-V2.6-Pro | 50 | pipeline | nvlink5 | infiniband_ndr | 49 | 65.84 us | 1,518.8 tok/s | 15,188.0 tok/s | 43 x point_to_point span 2 on nvlink5 (traversals 1.0) = 52.19 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.65 us |
| MiMo-V2.6-Pro/b200_sxm-x50-tensor | MiMo-V2.6-Pro | 50 | tensor | nvlink5 | infiniband_ndr | 280 | 997.89 us | 100.2 tok/s | 1,002.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 656.87 us |
| MiMo-V2.6-Pro/b200_sxm-x50-hybrid | MiMo-V2.6-Pro | 50 | hybrid | nvlink5 | infiniband_ndr | 146 | 354.67 us | 282.0 tok/s | 2,819.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.65 us |
| MiMo-V2.6-Pro/b200_sxm-x50-nvl72-tensor | MiMo-V2.6-Pro | 50 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.62 us | 292.7 tok/s | 2,927.2 tok/s | 140 x all_reduce span 50 on nvlink5_nvl72 (traversals 2.0) = 341.62 us |
| MiMo-V2.6-Pro/b200_sxm-x50-expert | MiMo-V2.6-Pro | 50 | expert | nvlink5 | infiniband_ndr | 280 | 626.54 us | 159.6 tok/s | 1,596.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.84 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 289.71 us |
| MiMo-V2.6-Pro/b200_sxm-x50-nvl72-expert | MiMo-V2.6-Pro | 50 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.93 us | 196.1 tok/s | 1,961.1 tok/s | 140 x all_reduce span 50 on nvlink5_nvl72 (traversals 2.0) = 341.62 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.31 us |
| MiMo-V2.6-Pro/b200_sxm-x52-pipeline | MiMo-V2.6-Pro | 52 | pipeline | nvlink5 | infiniband_ndr | 51 | 68.27 us | 1,464.8 tok/s | 14,647.9 tok/s | 45 x point_to_point span 2 on nvlink5 (traversals 1.0) = 54.61 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.65 us |
| MiMo-V2.6-Pro/b200_sxm-x52-tensor | MiMo-V2.6-Pro | 52 | tensor | nvlink5 | infiniband_ndr | 280 | 997.89 us | 100.2 tok/s | 1,002.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 656.87 us |
| MiMo-V2.6-Pro/b200_sxm-x52-hybrid | MiMo-V2.6-Pro | 52 | hybrid | nvlink5 | infiniband_ndr | 146 | 354.67 us | 282.0 tok/s | 2,819.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.65 us |
| MiMo-V2.6-Pro/b200_sxm-x52-nvl72-tensor | MiMo-V2.6-Pro | 52 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.62 us | 292.7 tok/s | 2,927.2 tok/s | 140 x all_reduce span 52 on nvlink5_nvl72 (traversals 2.0) = 341.62 us |
| MiMo-V2.6-Pro/b200_sxm-x52-expert | MiMo-V2.6-Pro | 52 | expert | nvlink5 | infiniband_ndr | 280 | 626.33 us | 159.7 tok/s | 1,596.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.84 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 289.49 us |
| MiMo-V2.6-Pro/b200_sxm-x52-nvl72-expert | MiMo-V2.6-Pro | 52 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.92 us | 196.1 tok/s | 1,961.1 tok/s | 140 x all_reduce span 52 on nvlink5_nvl72 (traversals 2.0) = 341.62 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.29 us |
| MiMo-V2.6-Pro/b200_sxm-x53-pipeline | MiMo-V2.6-Pro | 53 | pipeline | nvlink5 | infiniband_ndr | 52 | 69.48 us | 1,439.2 tok/s | 14,392.1 tok/s | 46 x point_to_point span 2 on nvlink5 (traversals 1.0) = 55.83 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.65 us |
| MiMo-V2.6-Pro/b200_sxm-x53-tensor | MiMo-V2.6-Pro | 53 | tensor | nvlink5 | infiniband_ndr | 280 | 997.89 us | 100.2 tok/s | 1,002.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 656.87 us |
| MiMo-V2.6-Pro/b200_sxm-x53-hybrid | MiMo-V2.6-Pro | 53 | hybrid | nvlink5 | infiniband_ndr | 146 | 354.67 us | 282.0 tok/s | 2,819.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.65 us |
| MiMo-V2.6-Pro/b200_sxm-x53-nvl72-tensor | MiMo-V2.6-Pro | 53 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.63 us | 292.7 tok/s | 2,927.2 tok/s | 140 x all_reduce span 53 on nvlink5_nvl72 (traversals 2.0) = 341.63 us |
| MiMo-V2.6-Pro/b200_sxm-x53-expert | MiMo-V2.6-Pro | 53 | expert | nvlink5 | infiniband_ndr | 280 | 626.23 us | 159.7 tok/s | 1,596.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.84 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 289.39 us |
| MiMo-V2.6-Pro/b200_sxm-x53-nvl72-expert | MiMo-V2.6-Pro | 53 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.91 us | 196.1 tok/s | 1,961.1 tok/s | 140 x all_reduce span 53 on nvlink5_nvl72 (traversals 2.0) = 341.63 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.29 us |
| MiMo-V2.6-Pro/b200_sxm-x56-pipeline | MiMo-V2.6-Pro | 56 | pipeline | nvlink5 | infiniband_ndr | 55 | 73.12 us | 1,367.5 tok/s | 13,675.5 tok/s | 49 x point_to_point span 2 on nvlink5 (traversals 1.0) = 59.47 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.65 us |
| MiMo-V2.6-Pro/b200_sxm-x56-tensor | MiMo-V2.6-Pro | 56 | tensor | nvlink5 | infiniband_ndr | 280 | 997.89 us | 100.2 tok/s | 1,002.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 656.87 us |
| MiMo-V2.6-Pro/b200_sxm-x56-hybrid | MiMo-V2.6-Pro | 56 | hybrid | nvlink5 | infiniband_ndr | 146 | 354.67 us | 282.0 tok/s | 2,819.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.65 us |
| MiMo-V2.6-Pro/b200_sxm-x56-nvl72-tensor | MiMo-V2.6-Pro | 56 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.63 us | 292.7 tok/s | 2,927.1 tok/s | 140 x all_reduce span 56 on nvlink5_nvl72 (traversals 2.0) = 341.63 us |
| MiMo-V2.6-Pro/b200_sxm-x56-expert | MiMo-V2.6-Pro | 56 | expert | nvlink5 | infiniband_ndr | 280 | 625.83 us | 159.8 tok/s | 1,597.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.72 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 289.12 us |
| MiMo-V2.6-Pro/b200_sxm-x56-nvl72-expert | MiMo-V2.6-Pro | 56 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.91 us | 196.1 tok/s | 1,961.1 tok/s | 140 x all_reduce span 56 on nvlink5_nvl72 (traversals 2.0) = 341.63 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.27 us |
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
| MiMo-V2.6-Pro/b200_sxm-x63-pipeline | MiMo-V2.6-Pro | 63 | pipeline | nvlink5 | infiniband_ndr | 62 | 82.68 us | 1,209.5 tok/s | 12,094.6 tok/s | 55 x point_to_point span 2 on nvlink5 (traversals 1.0) = 66.75 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.93 us |
| MiMo-V2.6-Pro/b200_sxm-x63-tensor | MiMo-V2.6-Pro | 63 | tensor | nvlink5 | infiniband_ndr | 280 | 999.73 us | 100.0 tok/s | 1,000.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 658.72 us |
| MiMo-V2.6-Pro/b200_sxm-x63-hybrid | MiMo-V2.6-Pro | 63 | hybrid | nvlink5 | infiniband_ndr | 147 | 356.95 us | 280.2 tok/s | 2,801.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.93 us |
| MiMo-V2.6-Pro/b200_sxm-x63-nvl72-tensor | MiMo-V2.6-Pro | 63 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.64 us | 292.7 tok/s | 2,927.0 tok/s | 140 x all_reduce span 63 on nvlink5_nvl72 (traversals 2.0) = 341.64 us |
| MiMo-V2.6-Pro/b200_sxm-x63-expert | MiMo-V2.6-Pro | 63 | expert | nvlink5 | infiniband_ndr | 280 | 625.29 us | 159.9 tok/s | 1,599.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.72 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 288.57 us |
| MiMo-V2.6-Pro/b200_sxm-x63-nvl72-expert | MiMo-V2.6-Pro | 63 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.89 us | 196.1 tok/s | 1,961.2 tok/s | 140 x all_reduce span 63 on nvlink5_nvl72 (traversals 2.0) = 341.64 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.24 us |
| MiMo-V2.6-Pro/b200_sxm-x70-pipeline | MiMo-V2.6-Pro | 70 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x70-tensor | MiMo-V2.6-Pro | 70 | tensor | nvlink5 | infiniband_ndr | 280 | 1,001.17 us | 99.9 tok/s | 998.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 660.15 us |
| MiMo-V2.6-Pro/b200_sxm-x70-hybrid | MiMo-V2.6-Pro | 70 | hybrid | nvlink5 | infiniband_ndr | 148 | 359.22 us | 278.4 tok/s | 2,783.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x70-nvl72-tensor | MiMo-V2.6-Pro | 70 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.65 us | 292.7 tok/s | 2,927.0 tok/s | 140 x all_reduce span 70 on nvlink5_nvl72 (traversals 2.0) = 341.65 us |
| MiMo-V2.6-Pro/b200_sxm-x70-expert | MiMo-V2.6-Pro | 70 | expert | nvlink5 | infiniband_ndr | 280 | 624.76 us | 160.1 tok/s | 1,600.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.63 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 288.13 us |
| MiMo-V2.6-Pro/b200_sxm-x70-nvl72-expert | MiMo-V2.6-Pro | 70 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.87 us | 196.1 tok/s | 1,961.3 tok/s | 140 x all_reduce span 70 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.22 us |
| MiMo-V2.6-Pro/b200_sxm-x71-pipeline | MiMo-V2.6-Pro | 71 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x71-tensor | MiMo-V2.6-Pro | 71 | tensor | nvlink5 | infiniband_ndr | 280 | 1,001.17 us | 99.9 tok/s | 998.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 660.15 us |
| MiMo-V2.6-Pro/b200_sxm-x71-hybrid | MiMo-V2.6-Pro | 71 | hybrid | nvlink5 | infiniband_ndr | 148 | 359.22 us | 278.4 tok/s | 2,783.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x71-nvl72-tensor | MiMo-V2.6-Pro | 71 | tensor | nvlink5_nvl72 | infiniband_ndr | 140 | 341.65 us | 292.7 tok/s | 2,926.9 tok/s | 140 x all_reduce span 71 on nvlink5_nvl72 (traversals 2.0) = 341.65 us |
| MiMo-V2.6-Pro/b200_sxm-x71-expert | MiMo-V2.6-Pro | 71 | expert | nvlink5 | infiniband_ndr | 280 | 624.70 us | 160.1 tok/s | 1,600.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.63 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 288.08 us |
| MiMo-V2.6-Pro/b200_sxm-x71-nvl72-expert | MiMo-V2.6-Pro | 71 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 509.87 us | 196.1 tok/s | 1,961.3 tok/s | 140 x all_reduce span 71 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 168.22 us |
| MiMo-V2.6-Pro/b200_sxm-x75-pipeline | MiMo-V2.6-Pro | 75 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x75-tensor | MiMo-V2.6-Pro | 75 | tensor | nvlink5 | infiniband_ndr | 280 | 1,002.31 us | 99.8 tok/s | 997.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 661.30 us |
| MiMo-V2.6-Pro/b200_sxm-x75-hybrid | MiMo-V2.6-Pro | 75 | hybrid | nvlink5 | infiniband_ndr | 149 | 361.50 us | 276.6 tok/s | 2,766.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.48 us |
| MiMo-V2.6-Pro/b200_sxm-x75-nvl72-tensor | MiMo-V2.6-Pro | 75 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x75-nvl72-hybrid | MiMo-V2.6-Pro | 75 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x75-expert | MiMo-V2.6-Pro | 75 | expert | nvlink5 | infiniband_ndr | 280 | 624.43 us | 160.1 tok/s | 1,601.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.56 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.87 us |
| MiMo-V2.6-Pro/b200_sxm-x75-nvl72-expert | MiMo-V2.6-Pro | 75 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 629.52 us | 158.8 tok/s | 1,588.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.87 us |
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
| MiMo-V2.6-Pro/b200_sxm-x87-pipeline | MiMo-V2.6-Pro | 87 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x87-tensor | MiMo-V2.6-Pro | 87 | tensor | nvlink5 | infiniband_ndr | 280 | 1,003.25 us | 99.7 tok/s | 996.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 662.24 us |
| MiMo-V2.6-Pro/b200_sxm-x87-hybrid | MiMo-V2.6-Pro | 87 | hybrid | nvlink5 | infiniband_ndr | 150 | 363.78 us | 274.9 tok/s | 2,749.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.76 us |
| MiMo-V2.6-Pro/b200_sxm-x87-nvl72-tensor | MiMo-V2.6-Pro | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x87-nvl72-hybrid | MiMo-V2.6-Pro | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x87-expert | MiMo-V2.6-Pro | 87 | expert | nvlink5 | infiniband_ndr | 280 | 623.87 us | 160.3 tok/s | 1,602.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.50 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.36 us |
| MiMo-V2.6-Pro/b200_sxm-x87-nvl72-expert | MiMo-V2.6-Pro | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 629.02 us | 159.0 tok/s | 1,589.8 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.36 us |
| MiMo-V2.6-Pro/b200_sxm-x93-pipeline | MiMo-V2.6-Pro | 93 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x93-tensor | MiMo-V2.6-Pro | 93 | tensor | nvlink5 | infiniband_ndr | 280 | 1,004.04 us | 99.6 tok/s | 996.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 663.02 us |
| MiMo-V2.6-Pro/b200_sxm-x93-hybrid | MiMo-V2.6-Pro | 93 | hybrid | nvlink5 | infiniband_ndr | 151 | 366.05 us | 273.2 tok/s | 2,731.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.03 us |
| MiMo-V2.6-Pro/b200_sxm-x93-nvl72-tensor | MiMo-V2.6-Pro | 93 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x93-nvl72-hybrid | MiMo-V2.6-Pro | 93 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x93-expert | MiMo-V2.6-Pro | 93 | expert | nvlink5 | infiniband_ndr | 280 | 623.62 us | 160.4 tok/s | 1,603.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.46 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.16 us |
| MiMo-V2.6-Pro/b200_sxm-x93-nvl72-expert | MiMo-V2.6-Pro | 93 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.81 us | 159.0 tok/s | 1,590.3 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 287.16 us |
| MiMo-V2.6-Pro/b200_sxm-x100-pipeline | MiMo-V2.6-Pro | 100 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x100-tensor | MiMo-V2.6-Pro | 100 | tensor | nvlink5 | infiniband_ndr | 280 | 1,004.70 us | 99.5 tok/s | 995.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 663.68 us |
| MiMo-V2.6-Pro/b200_sxm-x100-hybrid | MiMo-V2.6-Pro | 100 | hybrid | nvlink5 | infiniband_ndr | 152 | 368.33 us | 271.5 tok/s | 2,715.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 27.31 us |
| MiMo-V2.6-Pro/b200_sxm-x100-nvl72-tensor | MiMo-V2.6-Pro | 100 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x100-nvl72-hybrid | MiMo-V2.6-Pro | 100 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x100-expert | MiMo-V2.6-Pro | 100 | expert | nvlink5 | infiniband_ndr | 280 | 623.37 us | 160.4 tok/s | 1,604.2 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.42 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.95 us |
| MiMo-V2.6-Pro/b200_sxm-x100-nvl72-expert | MiMo-V2.6-Pro | 100 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.61 us | 159.1 tok/s | 1,590.8 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.95 us |
| MiMo-V2.6-Pro/b200_sxm-x116-pipeline | MiMo-V2.6-Pro | 116 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x116-tensor | MiMo-V2.6-Pro | 116 | tensor | nvlink5 | infiniband_ndr | 280 | 1,005.76 us | 99.4 tok/s | 994.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 664.74 us |
| MiMo-V2.6-Pro/b200_sxm-x116-hybrid | MiMo-V2.6-Pro | 116 | hybrid | nvlink5 | infiniband_ndr | 154 | 372.88 us | 268.2 tok/s | 2,681.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 31.86 us |
| MiMo-V2.6-Pro/b200_sxm-x116-nvl72-tensor | MiMo-V2.6-Pro | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x116-nvl72-hybrid | MiMo-V2.6-Pro | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x116-expert | MiMo-V2.6-Pro | 116 | expert | nvlink5 | infiniband_ndr | 280 | 622.93 us | 160.5 tok/s | 1,605.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.36 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.57 us |
| MiMo-V2.6-Pro/b200_sxm-x116-nvl72-expert | MiMo-V2.6-Pro | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 628.23 us | 159.2 tok/s | 1,591.8 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.57 us |
| MiMo-V2.6-Pro/b200_sxm-x139-pipeline | MiMo-V2.6-Pro | 139 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x139-tensor | MiMo-V2.6-Pro | 139 | tensor | nvlink5 | infiniband_ndr | 280 | 1,006.90 us | 99.3 tok/s | 993.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 18 on infiniband_ndr (traversals 2.0) = 665.88 us |
| MiMo-V2.6-Pro/b200_sxm-x139-hybrid | MiMo-V2.6-Pro | 139 | hybrid | nvlink5 | infiniband_ndr | 157 | 379.71 us | 263.4 tok/s | 2,633.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 38.69 us |
| MiMo-V2.6-Pro/b200_sxm-x139-nvl72-tensor | MiMo-V2.6-Pro | 139 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 961.66 us | 104.0 tok/s | 1,039.9 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 620.01 us |
| MiMo-V2.6-Pro/b200_sxm-x139-nvl72-hybrid | MiMo-V2.6-Pro | 139 | hybrid | nvlink5_nvl72 | infiniband_ndr | 141 | 343.93 us | 290.8 tok/s | 2,907.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.28 us |
| MiMo-V2.6-Pro/b200_sxm-x139-expert | MiMo-V2.6-Pro | 139 | expert | nvlink5 | infiniband_ndr | 280 | 622.48 us | 160.6 tok/s | 1,606.5 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.30 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.18 us |
| MiMo-V2.6-Pro/b200_sxm-x139-nvl72-expert | MiMo-V2.6-Pro | 139 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 627.83 us | 159.3 tok/s | 1,592.8 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.18 us |
| MiMo-V2.6-Pro/b200_sxm-x150-pipeline | MiMo-V2.6-Pro | 150 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x150-tensor | MiMo-V2.6-Pro | 150 | tensor | nvlink5 | infiniband_ndr | 280 | 1,007.20 us | 99.3 tok/s | 992.8 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 666.19 us |
| MiMo-V2.6-Pro/b200_sxm-x150-hybrid | MiMo-V2.6-Pro | 150 | hybrid | nvlink5 | infiniband_ndr | 158 | 381.98 us | 261.8 tok/s | 2,617.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 40.96 us |
| MiMo-V2.6-Pro/b200_sxm-x150-nvl72-tensor | MiMo-V2.6-Pro | 150 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 978.87 us | 102.2 tok/s | 1,021.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 637.21 us |
| MiMo-V2.6-Pro/b200_sxm-x150-nvl72-hybrid | MiMo-V2.6-Pro | 150 | hybrid | nvlink5_nvl72 | infiniband_ndr | 142 | 346.21 us | 288.8 tok/s | 2,888.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x150-expert | MiMo-V2.6-Pro | 150 | expert | nvlink5 | infiniband_ndr | 280 | 622.31 us | 160.7 tok/s | 1,606.9 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.28 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.04 us |
| MiMo-V2.6-Pro/b200_sxm-x150-nvl72-expert | MiMo-V2.6-Pro | 150 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 624.86 us | 160.0 tok/s | 1,600.4 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 338.83 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 286.04 us |
| MiMo-V2.6-Pro/b200_sxm-x173-pipeline | MiMo-V2.6-Pro | 173 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x173-tensor | MiMo-V2.6-Pro | 173 | tensor | nvlink5 | infiniband_ndr | 280 | 1,007.95 us | 99.2 tok/s | 992.1 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 666.93 us |
| MiMo-V2.6-Pro/b200_sxm-x173-hybrid | MiMo-V2.6-Pro | 173 | hybrid | nvlink5 | infiniband_ndr | 161 | 388.81 us | 257.2 tok/s | 2,572.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 47.79 us |
| MiMo-V2.6-Pro/b200_sxm-x173-nvl72-tensor | MiMo-V2.6-Pro | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 978.87 us | 102.2 tok/s | 1,021.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 637.21 us |
| MiMo-V2.6-Pro/b200_sxm-x173-nvl72-hybrid | MiMo-V2.6-Pro | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 142 | 346.21 us | 288.8 tok/s | 2,888.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x173-expert | MiMo-V2.6-Pro | 173 | expert | nvlink5 | infiniband_ndr | 280 | 622.03 us | 160.8 tok/s | 1,607.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.24 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.79 us |
| MiMo-V2.6-Pro/b200_sxm-x173-nvl72-expert | MiMo-V2.6-Pro | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 624.62 us | 160.1 tok/s | 1,601.0 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 338.83 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.79 us |
| MiMo-V2.6-Pro/b200_sxm-x185-pipeline | MiMo-V2.6-Pro | 185 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x185-tensor | MiMo-V2.6-Pro | 185 | tensor | nvlink5 | infiniband_ndr | 280 | 1,008.34 us | 99.2 tok/s | 991.7 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 667.32 us |
| MiMo-V2.6-Pro/b200_sxm-x185-hybrid | MiMo-V2.6-Pro | 185 | hybrid | nvlink5 | infiniband_ndr | 163 | 393.36 us | 254.2 tok/s | 2,542.2 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 52.34 us |
| MiMo-V2.6-Pro/b200_sxm-x185-nvl72-tensor | MiMo-V2.6-Pro | 185 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 978.87 us | 102.2 tok/s | 1,021.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 637.21 us |
| MiMo-V2.6-Pro/b200_sxm-x185-nvl72-hybrid | MiMo-V2.6-Pro | 185 | hybrid | nvlink5_nvl72 | infiniband_ndr | 142 | 346.21 us | 288.8 tok/s | 2,888.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x185-expert | MiMo-V2.6-Pro | 185 | expert | nvlink5 | infiniband_ndr | 280 | 621.91 us | 160.8 tok/s | 1,608.0 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.22 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.69 us |
| MiMo-V2.6-Pro/b200_sxm-x185-nvl72-expert | MiMo-V2.6-Pro | 185 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 624.52 us | 160.1 tok/s | 1,601.2 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 338.83 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.69 us |
| MiMo-V2.6-Pro/b200_sxm-x200-pipeline | MiMo-V2.6-Pro | 200 | pipeline | nvlink5 | infiniband_ndr | 69 | 92.24 us | 1,084.1 tok/s | 10,841.4 tok/s | 61 x point_to_point span 2 on nvlink5 (traversals 1.0) = 74.03 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.21 us |
| MiMo-V2.6-Pro/b200_sxm-x200-tensor | MiMo-V2.6-Pro | 200 | tensor | nvlink5 | infiniband_ndr | 280 | 1,008.51 us | 99.2 tok/s | 991.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 140 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 667.49 us |
| MiMo-V2.6-Pro/b200_sxm-x200-hybrid | MiMo-V2.6-Pro | 200 | hybrid | nvlink5 | infiniband_ndr | 164 | 395.64 us | 252.8 tok/s | 2,527.6 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 341.02 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 54.62 us |
| MiMo-V2.6-Pro/b200_sxm-x200-nvl72-tensor | MiMo-V2.6-Pro | 200 | tensor | nvlink5_nvl72 | infiniband_ndr | 280 | 978.87 us | 102.2 tok/s | 1,021.6 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 140 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 637.21 us |
| MiMo-V2.6-Pro/b200_sxm-x200-nvl72-hybrid | MiMo-V2.6-Pro | 200 | hybrid | nvlink5_nvl72 | infiniband_ndr | 142 | 346.21 us | 288.8 tok/s | 2,888.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 341.65 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.55 us |
| MiMo-V2.6-Pro/b200_sxm-x200-expert | MiMo-V2.6-Pro | 200 | expert | nvlink5 | infiniband_ndr | 280 | 621.78 us | 160.8 tok/s | 1,608.3 tok/s | 140 x all_reduce span 8 on nvlink5 (traversals 2.0) = 336.20 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.58 us |
| MiMo-V2.6-Pro/b200_sxm-x200-nvl72-expert | MiMo-V2.6-Pro | 200 | expert | nvlink5_nvl72 | infiniband_ndr | 280 | 624.40 us | 160.2 tok/s | 1,601.5 tok/s | 140 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 338.83 us; 140 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 285.58 us |
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

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Pro | 1 | wafer | wafer | MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 4,763.9 | 0.052 | 4,135.5 (114,100) | 4,763.9 (92,450) | 1.15x | layer_fixed_latency |
| MiMo-V2.6-Pro | 2 | wafer | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 4,947.3 | 0.036 | 4,135.5 (114,100) | 4,947.3 (138,675) | 1.20x | layer_fixed_latency |
| MiMo-V2.6-Pro | 4 | wafer | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 4,917.9 | 0.035 | 4,135.5 (114,100) | 4,917.9 (138,675) | 1.19x | layer_fixed_latency |
| MiMo-V2.6-Pro | 8 | wafer | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 4,713.1 | 0.034 | 4,135.5 (114,100) | 4,713.1 (138,675) | 1.14x | layer_fixed_latency |
| MiMo-V2.6-Pro | 16 | wafer | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 4,688.0 | 0.017 | 4,067.6 (119,805) | 4,688.0 (277,350) | 1.15x | layer_fixed_latency |
| MiMo-V2.6-Pro | 32 | wafer | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,678.8 | 0.008 | 4,007.7 (185,005) | 4,678.8 (554,700) | 1.17x | layer_fixed_latency |
| MiMo-V2.6-Pro | 64 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 3,772.7 | 0.014 | 3,772.7 (277,100) | 3,970.0 (554,700) | 1.05x | layer_fixed_latency |
| MiMo-V2.6-Pro | 256 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392-romfill | 319,480 | 2,400.0 | 0.008 | 2,400.0 (319,480) | 2,311.8 (554,700) | 0.96x | weight_read |
| MiMo-V2.6-Pro | 1024 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x294 | 239,610 | 843.0 | 0.004 | 843.0 (239,610) | 792.6 (554,700) | 0.94x | weight_read |
| MiMo-V2.6-Pro | 4096 | array | array | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392 | 319,480 | 345.6 | 0.001 | 345.6 (319,480) | 215.4 (554,700) | 0.62x | weight_read |

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
| MiMo-V2.6-Pro | 1 | sram | 350,377.4 | 25,599.0 | 25,599.0 | 13.69x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 2 | sram | 350,377.4 | 25,599.0 | 25,599.0 | 13.69x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 4 | sram | 350,377.4 | 25,599.0 | 25,599.0 | 13.69x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 8 | sram | 350,377.4 | 25,599.0 | 25,599.0 | 13.69x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 16 | sram | 350,377.4 | 25,599.0 | 36,716.3 | 13.69x | 1.43x | weight_read | weight_read | layer_fixed_latency |
| MiMo-V2.6-Pro | 32 | sram | 350,377.4 | 25,599.0 | 56,339.4 | 13.69x | 2.20x | weight_read | weight_read | layer_fixed_latency |
| MiMo-V2.6-Pro | 64 | sram | 350,377.4 | 25,599.0 | 80,210.3 | 13.69x | 3.13x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 256 | sram | 519,133.5 | 25,765.0 | 143,077.6 | 20.15x | 5.55x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 1024 | sram | 903,087.4 | 26,019.9 | 206,802.1 | 34.71x | 7.95x | weight_read | weight_read | kv_read |
| MiMo-V2.6-Pro | 4096 | sram | 1,415,485.7 | 26,085.0 | 248,518.5 | 54.26x | 9.53x | weight_read | weight_read | layer_fixed_latency |
| MiMo-V2.6-Pro | 1 | rom | 773,213.3 | 88,197.0 | 88,197.0 | 8.77x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 2 | rom | 773,213.3 | 88,197.0 | 88,197.0 | 8.77x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 4 | rom | 773,213.3 | 88,197.0 | 88,197.0 | 8.77x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 8 | rom | 773,213.3 | 88,197.0 | 88,197.0 | 8.77x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 16 | rom | 773,213.3 | 88,197.0 | 88,197.0 | 8.77x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 32 | rom | 773,213.3 | 88,197.0 | 94,474.7 | 8.77x | 1.07x | kv_read | weight_read | layer_fixed_latency |
| MiMo-V2.6-Pro | 64 | rom | 773,213.3 | 88,197.0 | 131,557.0 | 8.77x | 1.49x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 256 | rom | 773,213.3 | 90,199.5 | 197,611.5 | 8.57x | 2.19x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Pro | 1024 | rom | 870,608.2 | 93,402.7 | 220,463.8 | 9.32x | 2.36x | compute | weight_read | kv_read |
| MiMo-V2.6-Pro | 4096 | rom | 948,361.1 | 94,246.4 | 273,525.7 | 10.06x | 2.90x | compute | weight_read | layer_fixed_latency |

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
| MiMo-V2.6-Pro | 1 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 350,377.4 | 0.632 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 1 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 773,213.3 | 1.394 | kv_read | 2.21x |
| MiMo-V2.6-Pro | 1 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 25,599.0 | 0.185 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 1 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 88,197.0 | 0.636 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 1 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 25,599.0 | 0.185 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 1 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.62 | 1.00 | 88,197.0 | 0.636 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 2 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 350,377.4 | 0.632 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 2 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 773,213.3 | 1.394 | kv_read | 2.21x |
| MiMo-V2.6-Pro | 2 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 25,599.0 | 0.185 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 2 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 88,197.0 | 0.636 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 2 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 25,599.0 | 0.185 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 2 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.62 | 1.00 | 88,197.0 | 0.636 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 4 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 350,377.4 | 0.632 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 4 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 773,213.3 | 1.394 | kv_read | 2.21x |
| MiMo-V2.6-Pro | 4 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 25,599.0 | 0.185 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 4 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 88,197.0 | 0.636 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 4 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 25,599.0 | 0.185 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 4 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.62 | 1.00 | 88,197.0 | 0.636 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 8 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 350,377.4 | 0.632 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 8 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 773,213.3 | 1.394 | kv_read | 2.21x |
| MiMo-V2.6-Pro | 8 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 25,599.0 | 0.185 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 8 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 88,197.0 | 0.636 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 8 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 25,599.0 | 0.185 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 8 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.62 | 1.00 | 88,197.0 | 0.636 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 16 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 350,377.4 | 0.632 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 16 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 773,213.3 | 1.394 | kv_read | 2.21x |
| MiMo-V2.6-Pro | 16 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 25,599.0 | 0.185 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 16 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 88,197.0 | 0.636 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 16 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 1.88 | 36,716.3 | 0.265 | layer_fixed_latency | 0.10x |
| MiMo-V2.6-Pro | 16 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.62 | 1.00 | 88,197.0 | 0.636 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 32 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 350,377.4 | 0.632 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 32 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 773,213.3 | 1.394 | kv_read | 2.21x |
| MiMo-V2.6-Pro | 32 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 25,599.0 | 0.185 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 32 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 88,197.0 | 0.636 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 32 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 2.39 | 56,339.4 | 0.406 | layer_fixed_latency | 0.16x |
| MiMo-V2.6-Pro | 32 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 3.62 | 1.37 | 94,474.7 | 0.681 | layer_fixed_latency | 0.27x |
| MiMo-V2.6-Pro | 64 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 350,377.4 | 0.632 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 64 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 773,213.3 | 1.394 | kv_read | 2.21x |
| MiMo-V2.6-Pro | 64 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 25,599.0 | 0.185 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 64 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.00 | 88,197.0 | 0.636 | weight_read | 0.25x |
| MiMo-V2.6-Pro | 64 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 2.39 | 80,210.3 | 0.578 | weight_read | 0.23x |
| MiMo-V2.6-Pro | 64 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 3.62 | 1.37 | 131,557.0 | 0.949 | weight_read | 0.38x |
| MiMo-V2.6-Pro | 256 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 519,133.5 | 0.936 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 256 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.31 | 1.00 | 773,213.3 | 1.394 | kv_read | 1.49x |
| MiMo-V2.6-Pro | 256 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.50 | 25,765.0 | 0.186 | weight_read | 0.05x |
| MiMo-V2.6-Pro | 256 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 1.50 | 90,199.5 | 0.650 | weight_read | 0.17x |
| MiMo-V2.6-Pro | 256 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 3.42 | 143,077.6 | 1.032 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 256 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 3.62 | 1.97 | 197,611.5 | 1.425 | kv_read | 0.38x |
| MiMo-V2.6-Pro | 1024 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 903,087.4 | 3.259 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x392-romfill | 319,480 | 2.32 | 1.00 | 870,608.2 | 2.725 | compute | 0.96x |
| MiMo-V2.6-Pro | 1024 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 5.99 | 26,019.9 | 0.188 | weight_read | 0.03x |
| MiMo-V2.6-Pro | 1024 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 5.99 | 93,402.7 | 0.674 | weight_read | 0.10x |
| MiMo-V2.6-Pro | 1024 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 4.82 | 206,802.1 | 1.491 | kv_read | 0.23x |
| MiMo-V2.6-Pro | 1024 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.62 | 1.97 | 220,463.8 | 1.590 | kv_read | 0.24x |
| MiMo-V2.6-Pro | 4096 | batched | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x392 | 319,480 | 1.00 | 1.00 | 1,415,485.7 | 4.431 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | batched | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x392-romfill | 319,480 | 2.32 | 1.00 | 948,361.1 | 2.968 | compute | 0.67x |
| MiMo-V2.6-Pro | 4096 | per_stream | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 23.95 | 26,085.0 | 0.188 | weight_read | 0.02x |
| MiMo-V2.6-Pro | 4096 | per_stream | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.62 | 23.95 | 94,246.4 | 0.680 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 4096 | per_region | sram | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x52-perregion | 42,380 | 1.00 | 9.65 | 248,518.5 | 5.864 | layer_fixed_latency | 0.18x |
| MiMo-V2.6-Pro | 4096 | per_region | rom | MiMo-V2.6-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x58-perregion-romfill | 47,270 | 1.13 | 9.02 | 273,525.7 | 5.786 | layer_fixed_latency | 0.19x |

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
| MiMo-V2.6-Pro | 1 | 47 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 2 | 47 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 64 | 52 | 1.23 | 1.002 | 1.035 | 1.03x |
| MiMo-V2.6-Pro | 256 | 52 | 4.92 | 1.042 | 1.817 | 1.74x |
| MiMo-V2.6-Pro | 1024 | 52 | 19.69 | 1.209 | 3.186 | 2.64x |
| MiMo-V2.6-Pro | 4096 | 52 | 78.77 | 2.027 | 6.408 | 3.16x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Pro | 1 | 16 | 6.45 | 4.14 | 1.56x |
| MiMo-V2.6-Pro | 2 | 16 | 10.24 | 5.39 | 1.90x |
| MiMo-V2.6-Pro | 4 | 16 | 13.84 | 6.75 | 2.05x |
| MiMo-V2.6-Pro | 8 | 16 | 15.66 | 8.14 | 1.92x |
| MiMo-V2.6-Pro | 16 | 16 | 15.99 | 9.43 | 1.70x |
| MiMo-V2.6-Pro | 32 | 16 | 16.00 | 10.49 | 1.53x |
| MiMo-V2.6-Pro | 64 | 16 | 16.00 | 11.24 | 1.42x |
| MiMo-V2.6-Pro | 256 | 16 | 16.00 | 11.74 | 1.36x |
| MiMo-V2.6-Pro | 1024 | 16 | 16.00 | 11.74 | 1.36x |
| MiMo-V2.6-Pro | 4096 | 16 | 16.00 | 11.74 | 1.36x |
| MiMo-V2.6-Pro | 1 | 24 | 6.93 | 4.65 | 1.49x |
| MiMo-V2.6-Pro | 2 | 24 | 11.77 | 6.25 | 1.88x |
| MiMo-V2.6-Pro | 4 | 24 | 17.59 | 8.13 | 2.16x |
| MiMo-V2.6-Pro | 8 | 24 | 22.09 | 10.15 | 2.18x |
| MiMo-V2.6-Pro | 16 | 24 | 23.78 | 12.13 | 1.96x |
| MiMo-V2.6-Pro | 32 | 24 | 23.99 | 13.85 | 1.73x |
| MiMo-V2.6-Pro | 64 | 24 | 24.00 | 15.10 | 1.59x |
| MiMo-V2.6-Pro | 256 | 24 | 24.00 | 15.95 | 1.50x |
| MiMo-V2.6-Pro | 1024 | 24 | 24.00 | 15.96 | 1.50x |
| MiMo-V2.6-Pro | 4096 | 24 | 24.00 | 15.96 | 1.50x |
| MiMo-V2.6-Pro | 1 | 26 | 7.00 | 4.76 | 1.47x |
| MiMo-V2.6-Pro | 2 | 26 | 12.03 | 6.42 | 1.87x |
| MiMo-V2.6-Pro | 4 | 26 | 18.30 | 8.41 | 2.18x |
| MiMo-V2.6-Pro | 8 | 26 | 23.48 | 10.58 | 2.22x |
| MiMo-V2.6-Pro | 16 | 26 | 25.65 | 12.72 | 2.02x |
| MiMo-V2.6-Pro | 32 | 26 | 25.98 | 14.59 | 1.78x |
| MiMo-V2.6-Pro | 64 | 26 | 26.00 | 15.97 | 1.63x |
| MiMo-V2.6-Pro | 256 | 26 | 26.00 | 16.91 | 1.54x |
| MiMo-V2.6-Pro | 1024 | 26 | 26.00 | 16.93 | 1.54x |
| MiMo-V2.6-Pro | 4096 | 26 | 26.00 | 16.93 | 1.54x |
| MiMo-V2.6-Pro | 1 | 27 | 7.04 | 4.81 | 1.46x |
| MiMo-V2.6-Pro | 2 | 27 | 12.15 | 6.50 | 1.87x |
| MiMo-V2.6-Pro | 4 | 27 | 18.62 | 8.54 | 2.18x |
| MiMo-V2.6-Pro | 8 | 27 | 24.14 | 10.78 | 2.24x |
| MiMo-V2.6-Pro | 16 | 27 | 26.57 | 13.00 | 2.04x |
| MiMo-V2.6-Pro | 32 | 27 | 26.98 | 14.95 | 1.80x |
| MiMo-V2.6-Pro | 64 | 27 | 27.00 | 16.39 | 1.65x |
| MiMo-V2.6-Pro | 256 | 27 | 27.00 | 17.38 | 1.55x |
| MiMo-V2.6-Pro | 1024 | 27 | 27.00 | 17.40 | 1.55x |
| MiMo-V2.6-Pro | 4096 | 27 | 27.00 | 17.40 | 1.55x |
| MiMo-V2.6-Pro | 1 | 29 | 7.10 | 4.90 | 1.45x |
| MiMo-V2.6-Pro | 2 | 29 | 12.36 | 6.65 | 1.86x |
| MiMo-V2.6-Pro | 4 | 29 | 19.23 | 8.80 | 2.19x |
| MiMo-V2.6-Pro | 8 | 29 | 25.41 | 11.17 | 2.27x |
| MiMo-V2.6-Pro | 16 | 29 | 28.39 | 13.54 | 2.10x |
| MiMo-V2.6-Pro | 32 | 29 | 28.96 | 15.65 | 1.85x |
| MiMo-V2.6-Pro | 64 | 29 | 29.00 | 17.22 | 1.68x |
| MiMo-V2.6-Pro | 256 | 29 | 29.00 | 18.30 | 1.59x |
| MiMo-V2.6-Pro | 1024 | 29 | 29.00 | 18.31 | 1.58x |
| MiMo-V2.6-Pro | 4096 | 29 | 29.00 | 18.31 | 1.58x |
| MiMo-V2.6-Pro | 1 | 30 | 7.13 | 4.94 | 1.44x |
| MiMo-V2.6-Pro | 2 | 30 | 12.46 | 6.72 | 1.86x |
| MiMo-V2.6-Pro | 4 | 30 | 19.52 | 8.92 | 2.19x |
| MiMo-V2.6-Pro | 8 | 30 | 26.01 | 11.36 | 2.29x |
| MiMo-V2.6-Pro | 16 | 30 | 29.28 | 13.81 | 2.12x |
| MiMo-V2.6-Pro | 32 | 30 | 29.95 | 15.99 | 1.87x |
| MiMo-V2.6-Pro | 64 | 30 | 30.00 | 17.62 | 1.70x |
| MiMo-V2.6-Pro | 256 | 30 | 30.00 | 18.74 | 1.60x |
| MiMo-V2.6-Pro | 1024 | 30 | 30.00 | 18.76 | 1.60x |
| MiMo-V2.6-Pro | 4096 | 30 | 30.00 | 18.76 | 1.60x |
| MiMo-V2.6-Pro | 1 | 48 | 7.44 | 5.56 | 1.34x |
| MiMo-V2.6-Pro | 2 | 48 | 13.61 | 7.68 | 1.77x |
| MiMo-V2.6-Pro | 4 | 48 | 23.02 | 10.66 | 2.16x |
| MiMo-V2.6-Pro | 8 | 48 | 34.29 | 14.08 | 2.44x |
| MiMo-V2.6-Pro | 16 | 48 | 43.25 | 17.75 | 2.44x |
| MiMo-V2.6-Pro | 32 | 48 | 47.09 | 21.21 | 2.22x |
| MiMo-V2.6-Pro | 64 | 48 | 47.88 | 23.90 | 2.00x |
| MiMo-V2.6-Pro | 256 | 48 | 47.98 | 25.83 | 1.86x |
| MiMo-V2.6-Pro | 1024 | 48 | 47.99 | 25.86 | 1.86x |
| MiMo-V2.6-Pro | 4096 | 48 | 47.99 | 25.86 | 1.86x |
| MiMo-V2.6-Pro | 1 | 50 | 7.46 | 5.61 | 1.33x |
| MiMo-V2.6-Pro | 2 | 50 | 13.69 | 7.76 | 1.76x |
| MiMo-V2.6-Pro | 4 | 50 | 23.28 | 10.81 | 2.15x |
| MiMo-V2.6-Pro | 8 | 50 | 34.98 | 14.33 | 2.44x |
| MiMo-V2.6-Pro | 16 | 50 | 44.56 | 18.12 | 2.46x |
| MiMo-V2.6-Pro | 32 | 50 | 48.88 | 21.71 | 2.25x |
| MiMo-V2.6-Pro | 64 | 50 | 49.84 | 24.51 | 2.03x |
| MiMo-V2.6-Pro | 256 | 50 | 49.98 | 26.52 | 1.88x |
| MiMo-V2.6-Pro | 1024 | 50 | 49.98 | 26.55 | 1.88x |
| MiMo-V2.6-Pro | 4096 | 50 | 49.98 | 26.55 | 1.88x |
| MiMo-V2.6-Pro | 1 | 52 | 7.48 | 5.66 | 1.32x |
| MiMo-V2.6-Pro | 2 | 52 | 13.76 | 7.84 | 1.75x |
| MiMo-V2.6-Pro | 4 | 52 | 23.53 | 10.96 | 2.15x |
| MiMo-V2.6-Pro | 8 | 52 | 35.63 | 14.57 | 2.45x |
| MiMo-V2.6-Pro | 16 | 52 | 45.84 | 18.48 | 2.48x |
| MiMo-V2.6-Pro | 32 | 52 | 50.66 | 22.19 | 2.28x |
| MiMo-V2.6-Pro | 64 | 52 | 51.79 | 25.11 | 2.06x |
| MiMo-V2.6-Pro | 256 | 52 | 51.97 | 27.20 | 1.91x |
| MiMo-V2.6-Pro | 1024 | 52 | 51.97 | 27.24 | 1.91x |
| MiMo-V2.6-Pro | 4096 | 52 | 51.97 | 27.24 | 1.91x |
| MiMo-V2.6-Pro | 1 | 53 | 7.49 | 5.69 | 1.32x |
| MiMo-V2.6-Pro | 2 | 53 | 13.80 | 7.88 | 1.75x |
| MiMo-V2.6-Pro | 4 | 53 | 23.64 | 11.04 | 2.14x |
| MiMo-V2.6-Pro | 8 | 53 | 35.94 | 14.69 | 2.45x |
| MiMo-V2.6-Pro | 16 | 53 | 46.46 | 18.65 | 2.49x |
| MiMo-V2.6-Pro | 32 | 53 | 51.53 | 22.43 | 2.30x |
| MiMo-V2.6-Pro | 64 | 53 | 52.76 | 25.40 | 2.08x |
| MiMo-V2.6-Pro | 256 | 53 | 52.96 | 27.54 | 1.92x |
| MiMo-V2.6-Pro | 1024 | 53 | 52.96 | 27.57 | 1.92x |
| MiMo-V2.6-Pro | 4096 | 53 | 52.96 | 27.57 | 1.92x |
| MiMo-V2.6-Pro | 1 | 56 | 7.52 | 5.76 | 1.31x |
| MiMo-V2.6-Pro | 2 | 56 | 13.90 | 8.00 | 1.74x |
| MiMo-V2.6-Pro | 4 | 56 | 23.97 | 11.25 | 2.13x |
| MiMo-V2.6-Pro | 8 | 56 | 36.84 | 15.03 | 2.45x |
| MiMo-V2.6-Pro | 16 | 56 | 48.26 | 19.16 | 2.52x |
| MiMo-V2.6-Pro | 32 | 56 | 54.12 | 23.13 | 2.34x |
| MiMo-V2.6-Pro | 64 | 56 | 55.67 | 26.26 | 2.12x |
| MiMo-V2.6-Pro | 256 | 56 | 55.94 | 28.52 | 1.96x |
| MiMo-V2.6-Pro | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| MiMo-V2.6-Pro | 4096 | 56 | 55.94 | 28.56 | 1.96x |
| MiMo-V2.6-Pro | 1 | 57 | 7.53 | 5.78 | 1.30x |
| MiMo-V2.6-Pro | 2 | 57 | 13.93 | 8.03 | 1.73x |
| MiMo-V2.6-Pro | 4 | 57 | 24.08 | 11.32 | 2.13x |
| MiMo-V2.6-Pro | 8 | 57 | 37.12 | 15.14 | 2.45x |
| MiMo-V2.6-Pro | 16 | 57 | 48.84 | 19.32 | 2.53x |
| MiMo-V2.6-Pro | 32 | 57 | 54.96 | 23.35 | 2.35x |
| MiMo-V2.6-Pro | 64 | 57 | 56.63 | 26.54 | 2.13x |
| MiMo-V2.6-Pro | 256 | 57 | 56.93 | 28.85 | 1.97x |
| MiMo-V2.6-Pro | 1024 | 57 | 56.94 | 28.88 | 1.97x |
| MiMo-V2.6-Pro | 4096 | 57 | 56.94 | 28.88 | 1.97x |
| MiMo-V2.6-Pro | 1 | 58 | 7.53 | 5.80 | 1.30x |
| MiMo-V2.6-Pro | 2 | 58 | 13.96 | 8.07 | 1.73x |
| MiMo-V2.6-Pro | 4 | 58 | 24.18 | 11.39 | 2.12x |
| MiMo-V2.6-Pro | 8 | 58 | 37.40 | 15.25 | 2.45x |
| MiMo-V2.6-Pro | 16 | 58 | 49.41 | 19.49 | 2.54x |
| MiMo-V2.6-Pro | 32 | 58 | 55.80 | 23.57 | 2.37x |
| MiMo-V2.6-Pro | 64 | 58 | 57.59 | 26.82 | 2.15x |
| MiMo-V2.6-Pro | 256 | 58 | 57.92 | 29.16 | 1.99x |
| MiMo-V2.6-Pro | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| MiMo-V2.6-Pro | 4096 | 58 | 57.93 | 29.20 | 1.98x |
| MiMo-V2.6-Pro | 1 | 63 | 7.57 | 5.90 | 1.28x |
| MiMo-V2.6-Pro | 2 | 63 | 14.10 | 8.24 | 1.71x |
| MiMo-V2.6-Pro | 4 | 63 | 24.64 | 11.70 | 2.11x |
| MiMo-V2.6-Pro | 8 | 63 | 38.69 | 15.76 | 2.45x |
| MiMo-V2.6-Pro | 16 | 63 | 52.13 | 20.27 | 2.57x |
| MiMo-V2.6-Pro | 32 | 63 | 59.90 | 24.65 | 2.43x |
| MiMo-V2.6-Pro | 64 | 63 | 62.33 | 28.16 | 2.21x |
| MiMo-V2.6-Pro | 256 | 63 | 62.86 | 30.71 | 2.05x |
| MiMo-V2.6-Pro | 1024 | 63 | 62.86 | 30.75 | 2.04x |
| MiMo-V2.6-Pro | 4096 | 63 | 62.86 | 30.75 | 2.04x |
| MiMo-V2.6-Pro | 1 | 70 | 7.61 | 6.03 | 1.26x |
| MiMo-V2.6-Pro | 2 | 70 | 14.26 | 8.47 | 1.68x |
| MiMo-V2.6-Pro | 4 | 70 | 25.20 | 12.11 | 2.08x |
| MiMo-V2.6-Pro | 8 | 70 | 40.27 | 16.42 | 2.45x |
| MiMo-V2.6-Pro | 16 | 70 | 55.58 | 21.29 | 2.61x |
| MiMo-V2.6-Pro | 32 | 70 | 65.34 | 26.07 | 2.51x |
| MiMo-V2.6-Pro | 64 | 70 | 68.83 | 29.93 | 2.30x |
| MiMo-V2.6-Pro | 256 | 70 | 69.71 | 32.76 | 2.13x |
| MiMo-V2.6-Pro | 1024 | 70 | 69.72 | 32.80 | 2.13x |
| MiMo-V2.6-Pro | 4096 | 70 | 69.72 | 32.80 | 2.13x |
| MiMo-V2.6-Pro | 1 | 71 | 7.62 | 6.05 | 1.26x |
| MiMo-V2.6-Pro | 2 | 71 | 14.28 | 8.50 | 1.68x |
| MiMo-V2.6-Pro | 4 | 71 | 25.27 | 12.16 | 2.08x |
| MiMo-V2.6-Pro | 8 | 71 | 40.48 | 16.51 | 2.45x |
| MiMo-V2.6-Pro | 16 | 71 | 56.05 | 21.42 | 2.62x |
| MiMo-V2.6-Pro | 32 | 71 | 66.08 | 26.26 | 2.52x |
| MiMo-V2.6-Pro | 64 | 71 | 69.74 | 30.17 | 2.31x |
| MiMo-V2.6-Pro | 256 | 71 | 70.69 | 33.04 | 2.14x |
| MiMo-V2.6-Pro | 1024 | 71 | 70.69 | 33.09 | 2.14x |
| MiMo-V2.6-Pro | 4096 | 71 | 70.69 | 33.09 | 2.14x |
| MiMo-V2.6-Pro | 1 | 75 | 7.64 | 6.12 | 1.25x |
| MiMo-V2.6-Pro | 2 | 75 | 14.36 | 8.62 | 1.67x |
| MiMo-V2.6-Pro | 4 | 75 | 25.54 | 12.37 | 2.06x |
| MiMo-V2.6-Pro | 8 | 75 | 41.27 | 16.85 | 2.45x |
| MiMo-V2.6-Pro | 16 | 75 | 57.83 | 21.96 | 2.63x |
| MiMo-V2.6-Pro | 32 | 75 | 69.01 | 27.01 | 2.55x |
| MiMo-V2.6-Pro | 64 | 75 | 73.35 | 31.12 | 2.36x |
| MiMo-V2.6-Pro | 256 | 75 | 74.56 | 34.15 | 2.18x |
| MiMo-V2.6-Pro | 1024 | 75 | 74.57 | 34.20 | 2.18x |
| MiMo-V2.6-Pro | 4096 | 75 | 74.57 | 34.20 | 2.18x |
| MiMo-V2.6-Pro | 1 | 77 | 7.65 | 6.15 | 1.24x |
| MiMo-V2.6-Pro | 2 | 77 | 14.40 | 8.67 | 1.66x |
| MiMo-V2.6-Pro | 4 | 77 | 25.66 | 12.47 | 2.06x |
| MiMo-V2.6-Pro | 8 | 77 | 41.64 | 17.02 | 2.45x |
| MiMo-V2.6-Pro | 16 | 77 | 58.68 | 22.22 | 2.64x |
| MiMo-V2.6-Pro | 32 | 77 | 70.43 | 27.38 | 2.57x |
| MiMo-V2.6-Pro | 64 | 77 | 75.12 | 31.59 | 2.38x |
| MiMo-V2.6-Pro | 256 | 77 | 76.48 | 34.69 | 2.20x |
| MiMo-V2.6-Pro | 1024 | 77 | 76.49 | 34.74 | 2.20x |
| MiMo-V2.6-Pro | 4096 | 77 | 76.49 | 34.74 | 2.20x |
| MiMo-V2.6-Pro | 1 | 78 | 7.65 | 6.16 | 1.24x |
| MiMo-V2.6-Pro | 2 | 78 | 14.41 | 8.70 | 1.66x |
| MiMo-V2.6-Pro | 4 | 78 | 25.72 | 12.52 | 2.06x |
| MiMo-V2.6-Pro | 8 | 78 | 41.81 | 17.10 | 2.45x |
| MiMo-V2.6-Pro | 16 | 78 | 59.09 | 22.35 | 2.64x |
| MiMo-V2.6-Pro | 32 | 78 | 71.13 | 27.56 | 2.58x |
| MiMo-V2.6-Pro | 64 | 78 | 76.01 | 31.82 | 2.39x |
| MiMo-V2.6-Pro | 256 | 78 | 77.44 | 34.96 | 2.22x |
| MiMo-V2.6-Pro | 1024 | 78 | 77.45 | 35.01 | 2.21x |
| MiMo-V2.6-Pro | 4096 | 78 | 77.45 | 35.01 | 2.21x |
| MiMo-V2.6-Pro | 1 | 87 | 7.69 | 6.29 | 1.22x |
| MiMo-V2.6-Pro | 2 | 87 | 14.55 | 8.95 | 1.63x |
| MiMo-V2.6-Pro | 4 | 87 | 26.21 | 12.92 | 2.03x |
| MiMo-V2.6-Pro | 8 | 87 | 43.28 | 17.78 | 2.43x |
| MiMo-V2.6-Pro | 16 | 87 | 62.56 | 23.44 | 2.67x |
| MiMo-V2.6-Pro | 32 | 87 | 77.13 | 29.11 | 2.65x |
| MiMo-V2.6-Pro | 64 | 87 | 83.74 | 33.79 | 2.48x |
| MiMo-V2.6-Pro | 256 | 87 | 85.95 | 37.27 | 2.31x |
| MiMo-V2.6-Pro | 1024 | 87 | 85.97 | 37.32 | 2.30x |
| MiMo-V2.6-Pro | 4096 | 87 | 85.97 | 37.32 | 2.30x |
| MiMo-V2.6-Pro | 1 | 93 | 7.71 | 6.37 | 1.21x |
| MiMo-V2.6-Pro | 2 | 93 | 14.63 | 9.10 | 1.61x |
| MiMo-V2.6-Pro | 4 | 93 | 26.49 | 13.16 | 2.01x |
| MiMo-V2.6-Pro | 8 | 93 | 44.13 | 18.20 | 2.42x |
| MiMo-V2.6-Pro | 16 | 93 | 64.63 | 24.11 | 2.68x |
| MiMo-V2.6-Pro | 32 | 93 | 80.85 | 30.08 | 2.69x |
| MiMo-V2.6-Pro | 64 | 93 | 88.69 | 35.03 | 2.53x |
| MiMo-V2.6-Pro | 256 | 93 | 91.51 | 38.72 | 2.36x |
| MiMo-V2.6-Pro | 1024 | 93 | 91.54 | 38.78 | 2.36x |
| MiMo-V2.6-Pro | 4096 | 93 | 91.54 | 38.78 | 2.36x |
| MiMo-V2.6-Pro | 1 | 100 | 7.73 | 6.45 | 1.20x |
| MiMo-V2.6-Pro | 2 | 100 | 14.71 | 9.27 | 1.59x |
| MiMo-V2.6-Pro | 4 | 100 | 26.78 | 13.41 | 2.00x |
| MiMo-V2.6-Pro | 8 | 100 | 45.02 | 18.66 | 2.41x |
| MiMo-V2.6-Pro | 16 | 100 | 66.84 | 24.85 | 2.69x |
| MiMo-V2.6-Pro | 32 | 100 | 84.92 | 31.16 | 2.73x |
| MiMo-V2.6-Pro | 64 | 100 | 94.25 | 36.40 | 2.59x |
| MiMo-V2.6-Pro | 256 | 100 | 97.85 | 40.35 | 2.43x |
| MiMo-V2.6-Pro | 1024 | 100 | 97.89 | 40.41 | 2.42x |
| MiMo-V2.6-Pro | 4096 | 100 | 97.89 | 40.41 | 2.42x |
| MiMo-V2.6-Pro | 1 | 116 | 7.76 | 6.60 | 1.18x |
| MiMo-V2.6-Pro | 2 | 116 | 14.86 | 9.62 | 1.55x |
| MiMo-V2.6-Pro | 4 | 116 | 27.32 | 13.91 | 1.96x |
| MiMo-V2.6-Pro | 8 | 116 | 46.71 | 19.63 | 2.38x |
| MiMo-V2.6-Pro | 16 | 116 | 71.17 | 26.40 | 2.70x |
| MiMo-V2.6-Pro | 32 | 116 | 93.27 | 33.39 | 2.79x |
| MiMo-V2.6-Pro | 64 | 116 | 106.10 | 39.31 | 2.70x |
| MiMo-V2.6-Pro | 256 | 116 | 111.76 | 43.79 | 2.55x |
| MiMo-V2.6-Pro | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| MiMo-V2.6-Pro | 4096 | 116 | 111.83 | 43.86 | 2.55x |
| MiMo-V2.6-Pro | 1 | 139 | 7.80 | 6.78 | 1.15x |
| MiMo-V2.6-Pro | 2 | 139 | 15.02 | 10.06 | 1.49x |
| MiMo-V2.6-Pro | 4 | 139 | 27.89 | 14.50 | 1.92x |
| MiMo-V2.6-Pro | 8 | 139 | 48.56 | 20.86 | 2.33x |
| MiMo-V2.6-Pro | 16 | 139 | 76.10 | 28.36 | 2.68x |
| MiMo-V2.6-Pro | 32 | 139 | 103.29 | 36.22 | 2.85x |
| MiMo-V2.6-Pro | 64 | 139 | 121.14 | 43.00 | 2.82x |
| MiMo-V2.6-Pro | 256 | 139 | 130.20 | 48.21 | 2.70x |
| MiMo-V2.6-Pro | 1024 | 139 | 130.31 | 48.29 | 2.70x |
| MiMo-V2.6-Pro | 4096 | 139 | 130.31 | 48.29 | 2.70x |
| MiMo-V2.6-Pro | 1 | 150 | 7.82 | 6.85 | 1.14x |
| MiMo-V2.6-Pro | 2 | 150 | 15.07 | 10.25 | 1.47x |
| MiMo-V2.6-Pro | 4 | 150 | 28.10 | 14.74 | 1.91x |
| MiMo-V2.6-Pro | 8 | 150 | 49.27 | 21.39 | 2.30x |
| MiMo-V2.6-Pro | 16 | 150 | 78.04 | 29.19 | 2.67x |
| MiMo-V2.6-Pro | 32 | 150 | 107.41 | 37.45 | 2.87x |
| MiMo-V2.6-Pro | 64 | 150 | 127.59 | 44.61 | 2.86x |
| MiMo-V2.6-Pro | 256 | 150 | 138.37 | 50.14 | 2.76x |
| MiMo-V2.6-Pro | 1024 | 150 | 138.50 | 50.23 | 2.76x |
| MiMo-V2.6-Pro | 4096 | 150 | 138.50 | 50.23 | 2.76x |
| MiMo-V2.6-Pro | 1 | 173 | 7.84 | 6.97 | 1.12x |
| MiMo-V2.6-Pro | 2 | 173 | 15.17 | 10.61 | 1.43x |
| MiMo-V2.6-Pro | 4 | 173 | 28.47 | 15.19 | 1.87x |
| MiMo-V2.6-Pro | 8 | 173 | 50.49 | 22.41 | 2.25x |
| MiMo-V2.6-Pro | 16 | 173 | 81.47 | 30.74 | 2.65x |
| MiMo-V2.6-Pro | 32 | 173 | 114.90 | 39.77 | 2.89x |
| MiMo-V2.6-Pro | 64 | 173 | 139.69 | 47.69 | 2.93x |
| MiMo-V2.6-Pro | 256 | 173 | 154.13 | 53.87 | 2.86x |
| MiMo-V2.6-Pro | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| MiMo-V2.6-Pro | 4096 | 173 | 154.32 | 53.96 | 2.86x |
| MiMo-V2.6-Pro | 1 | 185 | 7.85 | 7.02 | 1.12x |
| MiMo-V2.6-Pro | 2 | 185 | 15.21 | 10.78 | 1.41x |
| MiMo-V2.6-Pro | 4 | 185 | 28.62 | 15.41 | 1.86x |
| MiMo-V2.6-Pro | 8 | 185 | 51.01 | 22.88 | 2.23x |
| MiMo-V2.6-Pro | 16 | 185 | 82.98 | 31.46 | 2.64x |
| MiMo-V2.6-Pro | 32 | 185 | 118.31 | 40.86 | 2.90x |
| MiMo-V2.6-Pro | 64 | 185 | 145.35 | 49.16 | 2.96x |
| MiMo-V2.6-Pro | 256 | 185 | 161.70 | 55.66 | 2.91x |
| MiMo-V2.6-Pro | 1024 | 185 | 161.92 | 55.76 | 2.90x |
| MiMo-V2.6-Pro | 4096 | 185 | 161.92 | 55.76 | 2.90x |
| MiMo-V2.6-Pro | 1 | 200 | 7.86 | 7.08 | 1.11x |
| MiMo-V2.6-Pro | 2 | 200 | 15.26 | 10.97 | 1.39x |
| MiMo-V2.6-Pro | 4 | 200 | 28.80 | 15.66 | 1.84x |
| MiMo-V2.6-Pro | 8 | 200 | 51.59 | 23.43 | 2.20x |
| MiMo-V2.6-Pro | 16 | 200 | 84.66 | 32.28 | 2.62x |
| MiMo-V2.6-Pro | 32 | 200 | 122.15 | 42.14 | 2.90x |
| MiMo-V2.6-Pro | 64 | 200 | 151.88 | 50.89 | 2.98x |
| MiMo-V2.6-Pro | 256 | 200 | 170.56 | 57.78 | 2.95x |
| MiMo-V2.6-Pro | 1024 | 200 | 170.82 | 57.89 | 2.95x |
| MiMo-V2.6-Pro | 4096 | 200 | 170.82 | 57.89 | 2.95x |
| MiMo-V2.6-Pro | 1 | 231 | 7.88 | 7.19 | 1.10x |
| MiMo-V2.6-Pro | 2 | 231 | 15.33 | 11.34 | 1.35x |
| MiMo-V2.6-Pro | 4 | 231 | 29.08 | 16.14 | 1.80x |
| MiMo-V2.6-Pro | 8 | 231 | 52.57 | 24.42 | 2.15x |
| MiMo-V2.6-Pro | 16 | 231 | 87.55 | 33.78 | 2.59x |
| MiMo-V2.6-Pro | 32 | 231 | 128.92 | 44.54 | 2.89x |
| MiMo-V2.6-Pro | 64 | 231 | 163.68 | 54.17 | 3.02x |
| MiMo-V2.6-Pro | 256 | 231 | 187.01 | 61.81 | 3.03x |
| MiMo-V2.6-Pro | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| MiMo-V2.6-Pro | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| MiMo-V2.6-Pro | 1 | 347 | 7.92 | 7.43 | 1.07x |
| MiMo-V2.6-Pro | 2 | 347 | 15.50 | 12.32 | 1.26x |
| MiMo-V2.6-Pro | 4 | 347 | 29.71 | 17.67 | 1.68x |
| MiMo-V2.6-Pro | 8 | 347 | 54.77 | 26.85 | 2.04x |
| MiMo-V2.6-Pro | 16 | 347 | 94.25 | 38.30 | 2.46x |
| MiMo-V2.6-Pro | 32 | 347 | 145.44 | 51.79 | 2.81x |
| MiMo-V2.6-Pro | 64 | 347 | 194.20 | 63.82 | 3.04x |
| MiMo-V2.6-Pro | 256 | 347 | 231.86 | 73.74 | 3.14x |
| MiMo-V2.6-Pro | 1024 | 347 | 232.44 | 73.90 | 3.15x |
| MiMo-V2.6-Pro | 4096 | 347 | 232.44 | 73.90 | 3.15x |

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
| gpu | MiMo-V2.6-Pro | 1 | 1,366.30 | 69.6% |
| rom | MiMo-V2.6-Pro | 1 | 162.97 | 80.9% |

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
| MiMo-V2.6-Pro | 1 | 47 | 31.51% | 137.45 | 9.28 |
| MiMo-V2.6-Pro | 2 | 47 | 31.51% | 137.45 | 9.28 |
| MiMo-V2.6-Pro | 4 | 1 | 2.18% | 11.52 | 9.28 |
| MiMo-V2.6-Pro | 8 | 1 | 2.18% | 11.52 | 9.28 |
| MiMo-V2.6-Pro | 16 | 1 | 2.18% | 11.52 | 9.28 |
| MiMo-V2.6-Pro | 32 | 1 | 2.18% | 11.52 | 9.28 |

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
| MiMo-V2.6-Pro | 1 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 301.0 | 31,006.8 |
| MiMo-V2.6-Pro | 2 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 301.0 | 31,006.8 |
| MiMo-V2.6-Pro | 4 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 301.0 | 31,006.8 |
| MiMo-V2.6-Pro | 8 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 301.0 | 31,006.8 |
| MiMo-V2.6-Pro | 16 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 301.0 | 31,006.8 |
| MiMo-V2.6-Pro | 32 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 301.0 | 31,006.8 |
| MiMo-V2.6-Pro | 64 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 301.0 | 31,006.8 |
| MiMo-V2.6-Pro | 256 | 5.10% | 55.4 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 123.9 | 31,723.3 |
| MiMo-V2.6-Pro | 1024 | 18.89% | 128.6 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 31.3 | 32,099.1 |
| MiMo-V2.6-Pro | 4096 | 56.71% | 329.6 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 7.9 | 32,194.5 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | kv_read | 2 |
| gpu | layer_fixed_latency | 499 |
| gpu | link_latency | 942 |
| gpu | thermal | 44 |
| gpu | weight_read | 453 |
| rom | compute | 600 |
| rom | infeasible | 2092 |
| rom | kv_read | 172 |
| rom | layer_fixed_latency | 729 |
| rom | link_latency | 886 |
| rom | weight_read | 581 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2092 |

## Mechanical consistency audit

**FAIL** over 152,123 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x95', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x99', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x103', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x105', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x109', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x114', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x137', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x182', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x273', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x364', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x95', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x99', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x103', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x105', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x109', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x114', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x137', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x182', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x273', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x364', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x95', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x99', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x103', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x105', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x109', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x114', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x137', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x182', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x273', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x364', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x95', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x99', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x103', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x105', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x109', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x113', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x114', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-pipeline-x137', 'MiMo-V2.6-Pro', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 75 |
| derived | 50 |
| assumed | 85 |

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
- `links.rom_wafer_express.hop_latency_s`
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

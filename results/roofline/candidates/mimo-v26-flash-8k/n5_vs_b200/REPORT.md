# Area-constrained roofline: n5_vs_b200-mimo-v26-flash-8k

> CANDIDATE MODEL under n5_vs_b200: MiMo-V2.6-Flash at 8,192 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 261x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 48 devices. On the GPU side the correction reaches 26x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 43 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Flash takes 32 x 815 mm2 (26,080 mm2, array, KV in SRAM) at 14,568 tok/s per user and 559 tok/s per 1,000 mm2, holding 1 session, against 16 copies of one unified HBM die at the same silicon: 5.4x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Flash on 40,750 mm2 of ROM silicon at 19,635 tok/s per user against 40,000 mm2 of b200_sxm-x25-nvl72-tensor at 3,093 tok/s: **6.3x**, ROM binding on `weight_read` and the GPU on `link_latency`. It holds 23,623 resident sessions against the GPU cluster's 18,091. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 7.56x to it.** At 97,800 mm2 on MiMo-V2.6-Flash the pipeline-only GPU delivers 478.72 tok/s and the same silicon running tensor delivers 3,618 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.03x (MiMo-V2.6-Flash, ROM binding on `link_latency`) to 3.28x (MiMo-V2.6-Flash, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Flash engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 1,674 to 56,357 tok/s, and its rate with every slot occupied from 55,245 to 56,357. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 33 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 669 us over NVLink, capping per-user decode at 1,496 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 206.1 us and cap it at 4,852 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 0 of 10 operating points and an array 10; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 272 of 4414 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 79.1x of aggregate throughput (MiMo-V2.6-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 12.24x, on MiMo-V2.6-Flash at batch 4096, where the busiest region carries 2.99x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 258 of 4,414 feasible points (5.8%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x16-perregion-romfill` at batch 4096 on 13,040 mm2, throttled 1.36x from 74 to 54 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 93% kv read against 0.3% weight read. The ROM sweep is not what melts it.


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

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x32`** -- 32 x 815 mm2 reticle dies, 26,080 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **14,568.1 tok/s per user** (0.07 ms/token), binding on `link_latency`
- **558.6 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 14,568 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 1,685 W at 0.065 W/mm2, 115.7 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 16 copies of one unified HBM die -- `b200_sxm-x16-nvl72-tensor`, 25,600 mm2, area ratio 1.0188 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 26,080 | 25,600 | 1.0188 |
| user tok/s | 14,568.1 | 2,717.6 | 5.36x |
| aggregate tok/s | 14,568 | 2,718 | 1.90x |
| resident sessions | 1 | 11,288 | -- |
| J/token | 0.1157 | 3.4201 | 29.6x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 11,288 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x61-nvl72-tensor` at 97,600 mm2 and 3,617.8 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 39,120 | 19,379.3 | 495.4 | 22,678 | 6.33x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 19,684.5 | 402.5 | 28,347 | 6.06x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x30` | 24,450 | 12,659.1 | 517.8 | 1 | 4.76x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | 26,080 | 14,568.1 | 558.6 | 1 | 5.36x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | 26,080 | 14,568.1 | 558.6 | -- | 558.6 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x33` | 26,895 | 14,944.2 | 555.7 | 461.6 | 558.6 | stop |
| `ROM-N5-native-HBMKV-array-hw-tensor-x36` | 29,340 | 15,213.4 | 518.5 | 197.9 | 558.6 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 39,120 | 19,379.3 | 495.4 | 369.0 | 558.6 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x50` | 40,750 | 19,634.5 | 481.8 | 345.4 | 558.6 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 19,684.5 | 402.5 | 224.2 | 558.6 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x32` **<-- recommended** | 26,080 | 32 | 14,568.1 | 14,568 | 558.6 | 1 | `link_latency` | 1,685 | 115.7 | `b200_sxm-x16-nvl72-tensor` | 5.36x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x33` | 26,895 | 33 | 14,944.2 | 14,944 | 555.7 | 1 | `link_latency` | 1,737 | 116.2 | `b200_sxm-x17-nvl72-tensor` | 5.39x |
| `ROM-N5-native-HBMKV-array-hw-tensor-x36` | 29,340 | 36 | 15,213.4 | 15,213 | 518.5 | 17,008 | `link_latency` | 2,866 | 188.4 | `b200_sxm-x18-nvl72-tensor` | 5.39x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 39,120 | 48 | 19,379.3 | 232,552 | 495.4 | 22,678 | `compute` | 10,488 | 235.7 | `b200_sxm-x24-nvl72-tensor` | 6.33x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x50` | 40,750 | 50 | 19,634.5 | 255,249 | 481.8 | 23,623 | `weight_read` | 11,383 | 246.5 | `b200_sxm-x25-nvl72-tensor` | 6.35x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 60 | 19,684.5 | 295,267 | 402.5 | 28,347 | `weight_read` | 13,435 | 293.7 | `b200_sxm-x31-nvl72-tensor` | 6.06x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 348 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | 26,080 | 14,568.1 | 558.6 | 1 |
| array | 348 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 19,684.5 | 402.5 | 28,347 |
| array | 348 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x30` | 24,450 | 12,659.1 | 517.8 | 1 |
| wafer | 76 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,880.0 | 105.6 | 1 |
| wafer | 76 | fastest | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,953.1 | 53.6 | 8,126 |
| wafer | 76 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,880.0 | 105.6 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 19,684.5 | 295,267 | 28,347 | 13,435 | 293.7 | `weight_read` | `b200_sxm-x31-nvl72-tensor` | 3,247.6 | 22,627 | 4,702.0 | 0.986 | 6.06x | 16.0x |
| 1 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,953.1 | 9,906 | 8,126 | 11,606 | 2,315.5 | `link_latency` | `b200_sxm-x58-nvl72-tensor` | 3,595.9 | 43,037 | 7,009.3 | 0.996 | 1.38x | 3.0x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 92,095 | 18,788.3 | 544,859 | 53,388 | 24,991 | 552.5 | `weight_read` | `b200_sxm-x58-nvl72-tensor` | 3,595.9 | 43,037 | 7,009.3 | 0.992 | 5.22x | 12.7x |
| 1 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,953.1 | -- | 8,126 | -- | 2,315.5 | -- | -- | -- | -- | -- | 0.996 | 0.26x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 19,684.5 | 295,267 | 28,347 | 13,435 | 160.7 | `weight_read` | `b200_sxm-x31-nvl72-tensor` | 2,978.3 | 22,627 | 2,770.6 | 0.986 | 6.61x | 17.2x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,953.1 | 9,906 | 8,126 | 11,606 | 1,171.6 | `link_latency` | `b200_sxm-x58-nvl72-tensor` | 3,399.1 | 43,037 | 3,936.7 | 0.996 | 1.46x | 3.4x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 92,095 | 18,788.3 | 544,859 | 53,388 | 24,991 | 290.1 | `weight_read` | `b200_sxm-x58-nvl72-tensor` | 3,399.1 | 43,037 | 3,936.7 | 0.992 | 5.53x | 13.6x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,953.1 | -- | 8,126 | -- | 1,171.6 | -- | -- | -- | -- | -- | 0.996 | 0.26x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 19,684.5 | 295,267 | 28,347 | 13,435 | 94.3 | `weight_read` | `b200_sxm-x31-nvl72-tensor` | 2,569.3 | 22,627 | 1,787.0 | 0.986 | 7.66x | 19.0x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,948.1 | 19,793 | 16,252 | 16,949 | 856.3 | `link_latency` | `b200_sxm-x116-nvl72-hybrid` | 3,371.8 | 86,882 | 3,960.9 | 0.996 | 1.47x | 4.6x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 18,378.7 | 1,047,584 | 107,248 | 48,899 | 297.2 | `weight_read` | `b200_sxm-x116-nvl72-hybrid` | 3,371.8 | 86,882 | 3,960.9 | 0.997 | 5.45x | 13.3x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,948.1 | -- | 16,252 | -- | 856.3 | -- | -- | -- | -- | -- | 1.001 | 0.27x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 19,684.5 | 295,267 | 28,347 | 13,435 | 61.0 | `weight_read` | `b200_sxm-x31-nvl72-tensor` | 2,050.3 | 22,627 | 1,261.8 | 0.986 | 9.60x | 20.7x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 4,938.2 | 39,506 | 32,505 | 33,896 | 858.0 | `link_latency` | `b200_sxm-x231-nvl72-hybrid` | 3,316.8 | 173,815 | 3,997.7 | 1.001 | 1.49x | 4.7x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 19,314.3 | 309,029 | 28,347 | 13,771 | 44.6 | `weight_read` | `b200_sxm-x31-nvl72-tensor` | 1,524.6 | 22,627 | 941.4 | 0.986 | 12.67x | 21.1x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,878.9 | 78,062 | 48,758 | 51,320 | 657.4 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 3,196.9 | 261,504 | 3,163.8 | 0.999 | 1.53x | 4.8x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill` | 97,800 | 18,744.9 | 599,837 | 56,695 | 27,039 | 45.1 | `weight_read` | `b200_sxm-x61-nvl72-tensor` | 1,612.7 | 45,305 | 801.4 | 1.002 | 11.62x | 17.8x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,690.5 | 150,095 | 48,758 | 53,139 | 354.0 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 2,809.7 | 261,504 | 1,988.8 | 0.999 | 1.67x | 5.6x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 18,432.6 | 1,566,771 | 160,637 | 73,177 | 52.9 | `weight_read` | `b200_sxm-x173-nvl72-hybrid` | 1,811.8 | 129,970 | 975.4 | 1.001 | 10.17x | 18.4x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,354.2 | 278,669 | 48,758 | 56,373 | 202.3 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 2,307.4 | 261,504 | 1,352.3 | 0.999 | 1.89x | 6.7x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 8,310.1 | 2,127,379 | 160,637 | 85,276 | 40.1 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 1,036.2 | 129,970 | 447.9 | 1.001 | 8.02x | 10.5x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,044.6 | 779,413 | 48,758 | 68,766 | 88.2 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 1,344.1 | 261,504 | 659.3 | 0.999 | 2.27x | 7.1x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 2,402.2 | 2,459,822 | 160,637 | 93,966 | 38.2 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 530.1 | 129,970 | 188.5 | 1.001 | 4.53x | 4.5x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,844.0 | 1,888,273 | 48,758 | 100,119 | 53.0 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 722.1 | 261,504 | 275.8 | 0.999 | 2.55x | 4.2x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 614.1 | 2,515,536 | 160,637 | 93,449 | 37.1 | `compute` | `b200_sxm-x173-expert` | 187.5 | 129,257 | 108.2 | 1.001 | 3.28x | 2.9x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 471.9 | 1,932,938 | 48,758 | 98,836 | 51.1 | `kv_read` | `b200_sxm-x347-expert` | 323.9 | 260,006 | 120.9 | 0.999 | 1.46x | 2.4x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x32` | 26,080 | array | SRAM | 1 |
| 2-8 | `ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 39,120 | array | HBM | 22,678 |
| 16 | `ROM-N5-native-HBMKV-array-hw-hybrid-x50` | 40,750 | array | HBM | 23,623 |
| 32-64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 48,900 | array | HBM | 28,347 |
| 256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x90` | 73,350 | array | HBM | 42,521 |
| 1024-4096 | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 92,095 | array | HBM | 53,388 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Flash | HBM | rom | 33, 36, 38, 44, 45, 48, 49, 50, 57, 60, 90, 113, 120, 170, 227, 340 |
| MiMo-V2.6-Flash | HBM | sram | 33, 36, 38, 44, 45, 48, 49, 50, 57, 60, 90, 113, 120, 170, 227, 340 |
| MiMo-V2.6-Flash | SRAM | rom | 30, 32, 33, 35, 42, 56, 57, 84, 112, 113, 170, 227, 340 |
| MiMo-V2.6-Flash | SRAM | sram | 30, 32, 33, 35, 42, 56, 57, 84, 112, 113, 170, 227, 340 |

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

- **258 of 4,414 feasible points (5.8%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 240, rom 18.
- By area class: large array (5,000-40,000 mm2) 124, wafer (>=40,000 mm2) 134.
- By KV store: hbm 258.
- By batch: B=1 24, B=2 24, B=4 24, B=8 24, B=16 24, B=32 24, B=64 24, B=256 26, B=1024 30, B=4096 34.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 45% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 640 | 110 | 71.2% | 100.0% | 0.625 | 49% |
| gpu | wafer (>=40,000 mm2) | 830 | 130 | 52.0% | 100.0% | 0.625 | 67% |
| rom | large array (5,000-40,000 mm2) | 1,212 | 14 | 28.9% | 100.0% | 0.500 | 61% |
| rom | wafer (>=40,000 mm2) | 1,732 | 4 | 32.4% | 100.0% | 0.500 | 74% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x16-perregion-romfill` | MiMo-V2.6-Flash | 4096 | 13,040 | hbm | 1.358x | 6,520.0 / 6,520.0 W | 18% | 54.2 | 73.6 |
| `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x16-perregion` | MiMo-V2.6-Flash | 4096 | 13,040 | hbm | 1.358x | 6,520.0 / 6,520.0 W | 18% | 54.2 | 73.6 |
| `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-pipeline-x16-perregion-romfill` | MiMo-V2.6-Flash | 4096 | 13,040 | hbm | 1.350x | 6,520.0 / 6,520.0 W | 18% | 54.2 | 73.2 |
| `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-pipeline-x16-perregion` | MiMo-V2.6-Flash | 4096 | 13,040 | hbm | 1.350x | 6,520.0 / 6,520.0 W | 18% | 54.2 | 73.2 |
| `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x16-perregion-romfill` | MiMo-V2.6-Flash | 1024 | 13,040 | hbm | 1.310x | 6,520.0 / 6,520.0 W | 18% | 216.9 | 284.1 |
| `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x16-perregion` | MiMo-V2.6-Flash | 1024 | 13,040 | hbm | 1.310x | 6,520.0 / 6,520.0 W | 18% | 216.9 | 284.1 |
| `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x16-perregion-romfill` | MiMo-V2.6-Flash | 4096 | 13,040 | hbm | 1.310x | 6,520.0 / 6,520.0 W | 18% | 54.4 | 71.2 |
| `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x16-perregion` | MiMo-V2.6-Flash | 4096 | 13,040 | hbm | 1.310x | 6,520.0 / 6,520.0 W | 18% | 54.4 | 71.2 |
| `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170` | MiMo-V2.6-Flash | 4096 | 138,550 | hbm | 1.177x | 69,275.0 / 69,275.0 W | 29% | 492.1 | 579.1 |
| `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x16-perregion-romfill` | MiMo-V2.6-Flash | 1024 | 13,040 | hbm | 1.129x | 6,520.0 / 6,520.0 W | 18% | 215.4 | 243.1 |
| `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-pipeline-x16-perregion-romfill` | MiMo-V2.6-Flash | 1024 | 13,040 | hbm | 1.119x | 6,520.0 / 6,520.0 W | 18% | 215.4 | 241.1 |
| `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x16-perregion` | MiMo-V2.6-Flash | 1024 | 13,040 | hbm | 1.103x | 6,520.0 / 6,520.0 W | 18% | 215.4 | 237.6 |

The worst point's dynamic energy is kv read 93.3%, arithmetic 5.4%, operand delivery 1.0%, weight read 0.3%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| MiMo-V2.6-Flash | 1 | 39,120 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 0.235712 | 10,488.3 | compute | `MiMo-V2.6-Flash/b200_sxm-x24-nvl72-tensor` | 4.103772 | 12,565.0 | link_latency | 17.41x |
| MiMo-V2.6-Flash | 2 | 39,120 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 0.131742 | 10,488.3 | compute | `MiMo-V2.6-Flash/b200_sxm-x24-nvl72-tensor` | 2.468337 | 13,644.5 | link_latency | 18.74x |
| MiMo-V2.6-Flash | 4 | 39,120 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 0.079758 | 10,488.3 | compute | `MiMo-V2.6-Flash/b200_sxm-x24-nvl72-tensor` | 1.632639 | 15,211.7 | link_latency | 20.47x |
| MiMo-V2.6-Flash | 8 | 39,120 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x48` | 0.053765 | 10,488.3 | compute | `MiMo-V2.6-Flash/b200_sxm-x24-nvl72-tensor` | 1.181378 | 17,074.3 | weight_read | 21.97x |
| MiMo-V2.6-Flash | 16 | 46,455 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x57-romfill` | 0.044322 | 13,199.2 | weight_read | `MiMo-V2.6-Flash/b200_sxm-x29-nvl72-tensor` | 0.929003 | 21,807.2 | weight_read | 20.96x |
| MiMo-V2.6-Flash | 32 | 92,095 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 0.044425 | 25,951.1 | weight_read | `MiMo-V2.6-Flash/b200_sxm-x58-nvl72-tensor` | 0.790670 | 39,824.7 | link_latency | 17.80x |
| MiMo-V2.6-Flash | 64 | 185,005 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 0.044910 | 51,117.3 | weight_read | `MiMo-V2.6-Flash/b200_sxm-x116-nvl72-hybrid` | 0.795468 | 79,191.2 | link_latency | 17.71x |
| MiMo-V2.6-Flash | 256 | 277,100 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.040085 | 85,275.8 | compute | `MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid` | 0.447867 | 118,800.0 | link_latency | 10.54x |
| MiMo-V2.6-Flash | 1024 | 277,100 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.038200 | 93,966.2 | compute | `MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid` | 0.188520 | 102,336.0 | link_latency | 4.48x |
| MiMo-V2.6-Flash | 4096 | 277,100 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.037149 | 93,449.5 | compute | `MiMo-V2.6-Flash/b200_sxm-x173-expert` | 0.108226 | 83,103.6 | link_latency | 2.91x |

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
| MiMo-V2.6-Flash | 1 | 46,225 | 38,474.2 | wafer-pipeline | 4,880.0 | wafer-tensor | 7.88x | 8,387.9 | pipeline | 3,201.7 | tensor | 2.62x | 4.59x | 1.52x | 0.33x |
| MiMo-V2.6-Flash | 2 | 92,450 | 50,535.9 | wafer-pipeline | 4,953.1 | wafer-hybrid | 10.20x | 9,233.0 | pipeline | 3,595.9 | tensor | 2.57x | 5.47x | 1.38x | 0.25x |
| MiMo-V2.6-Flash | 3 | 138,675 | 53,301.0 | wafer-pipeline | 4,950.6 | wafer-hybrid | 10.77x | 10,338.6 | pipeline | 3,427.9 | hybrid | 3.02x | 5.16x | 1.44x | 0.28x |
| MiMo-V2.6-Flash | 4 | 184,900 | 54,800.2 | wafer-pipeline | 4,948.1 | wafer-hybrid | 11.07x | 10,997.0 | pipeline | 3,567.6 | hybrid | 3.08x | 4.98x | 1.39x | 0.28x |
| MiMo-V2.6-Flash | 6 | 277,350 | 56,386.2 | wafer-pipeline | 4,943.2 | wafer-hybrid | 11.41x | 11,735.8 | pipeline | 3,537.4 | hybrid | 3.32x | 4.80x | 1.40x | 0.29x |
| MiMo-V2.6-Flash | 8 | 369,800 | 57,214.1 | wafer-pipeline | 4,938.2 | wafer-hybrid | 11.59x | 12,152.9 | pipeline | 3,510.8 | hybrid | 3.46x | 4.71x | 1.41x | 0.30x |
| MiMo-V2.6-Flash | 12 | 554,700 | 58,066.7 | wafer-pipeline | 4,928.4 | wafer-hybrid | 11.78x | 12,599.5 | pipeline | 3,555.6 | hybrid | 3.54x | 4.61x | 1.39x | 0.30x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.25x to 0.33x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Flash | 1 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill | 48,900 | 19,684.5 | 295,266.8 | weight_read | MiMo-V2.6-Flash/b200_sxm-x31-nvl72-tensor | 49,600 | 0.99x | tensor | 232.94 | 3,247.6 | 3,247.6 | link_latency | 6.06x | 19.90x | 41.12x | 6.06x |
| MiMo-V2.6-Flash | 1 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x30 | 24,450 | 12,659.1 | 12,659.1 | link_latency | MiMo-V2.6-Flash/b200_sxm-x15-nvl72-tensor | 24,000 | 1.02x | tensor | 232.85 | 2,657.8 | 2,657.8 | link_latency | 4.76x | 1.76x | 26.44x | 4.76x |
| MiMo-V2.6-Flash | 2 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill | 48,900 | 19,684.5 | 295,266.8 | weight_read | MiMo-V2.6-Flash/b200_sxm-x31-nvl72-tensor | 49,600 | 0.99x | tensor | 235.47 | 2,978.3 | 5,956.5 | link_latency | 6.61x | 19.90x | 41.12x | 6.61x |
| MiMo-V2.6-Flash | 2 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x33 | 26,895 | 10,674.0 | 21,348.0 | link_latency | MiMo-V2.6-Flash/b200_sxm-x17-nvl72-tensor | 27,200 | 0.99x | tensor | 235.33 | 2,443.2 | 4,886.4 | link_latency | 4.37x | 2.62x | 22.30x | 4.37x |
| MiMo-V2.6-Flash | 4 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill | 48,900 | 19,684.5 | 295,266.8 | weight_read | MiMo-V2.6-Flash/b200_sxm-x31-nvl72-tensor | 49,600 | 0.99x | tensor | 240.55 | 2,569.3 | 10,277.2 | link_latency | 7.66x | 19.90x | 41.12x | 7.66x |
| MiMo-V2.6-Flash | 4 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x33 | 26,895 | 7,554.1 | 30,216.6 | compute | MiMo-V2.6-Flash/b200_sxm-x17-nvl72-tensor | 27,200 | 0.99x | tensor | 240.27 | 1,990.3 | 7,961.2 | link_latency | 3.80x | 3.71x | 15.78x | 3.80x |
| MiMo-V2.6-Flash | 8 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill | 48,900 | 19,684.5 | 295,266.8 | weight_read | MiMo-V2.6-Flash/b200_sxm-x31-nvl72-tensor | 49,600 | 0.99x | tensor | 250.70 | 2,050.3 | 16,402.1 | link_latency | 9.60x | 18.00x | 41.12x | 9.60x |
| MiMo-V2.6-Flash | 8 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x33 | 26,895 | 5,757.7 | 51,819.4 | compute | MiMo-V2.6-Flash/b200_sxm-x17-nvl72-tensor | 27,200 | 0.99x | tensor | 250.14 | 1,484.8 | 11,878.6 | weight_read | 3.88x | 4.36x | 12.03x | 3.88x |
| MiMo-V2.6-Flash | 16 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill | 48,900 | 19,314.3 | 309,029.4 | weight_read | MiMo-V2.6-Flash/b200_sxm-x31-nvl72-tensor | 49,600 | 0.99x | tensor | 270.99 | 1,524.6 | 24,393.7 | weight_read | 12.67x | 12.67x | 40.35x | 12.67x |
| MiMo-V2.6-Flash | 16 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x33 | 26,895 | 3,353.2 | 53,651.1 | compute | MiMo-V2.6-Flash/b200_sxm-x17-nvl72-tensor | 27,200 | 0.99x | tensor | 269.88 | 1,038.6 | 16,617.1 | weight_read | 3.23x | 3.23x | 7.00x | 3.23x |
| MiMo-V2.6-Flash | 32 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x120-romfill | 97,800 | 18,744.9 | 599,837.0 | weight_read | MiMo-V2.6-Flash/b200_sxm-x61-nvl72-tensor | 97,600 | 1.00x | tensor | 312.91 | 1,612.7 | 51,607.6 | link_latency | 11.62x | 11.62x | 39.16x | 11.62x |
| MiMo-V2.6-Flash | 32 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x33 | 26,895 | 1,715.6 | 54,898.6 | compute | MiMo-V2.6-Flash/b200_sxm-x17-nvl72-tensor | 27,200 | 0.99x | tensor | 309.35 | 722.8 | 23,130.6 | weight_read | 2.37x | 2.37x | 4.84x | 2.37x |
| MiMo-V2.6-Flash | 64 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 18,432.6 | 1,566,771.4 | weight_read | MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 296.60 | 1,811.8 | 115,955.3 | link_latency | 10.17x | 13.51x | 38.50x | 10.17x |
| MiMo-V2.6-Flash | 64 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x33 | 26,895 | 871.6 | 55,782.5 | compute | MiMo-V2.6-Flash/b200_sxm-x17-nvl72-tensor | 27,200 | 0.99x | tensor | 388.30 | 537.1 | 34,371.8 | weight_read | 1.62x | 1.62x | 3.76x | 1.62x |
| MiMo-V2.6-Flash | 256 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 8,310.1 | 2,127,379.4 | compute | MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 483.01 | 1,036.2 | 265,257.0 | link_latency | 8.02x | 8.02x | 20.68x | 8.02x |
| MiMo-V2.6-Flash | 256 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x33 | 26,895 | 219.6 | 56,218.8 | compute | MiMo-V2.6-Flash/b200_sxm-x17-nvl72-tensor | 27,200 | 0.99x | tensor | 862.01 | 344.8 | 88,258.1 | weight_read | 0.64x | 0.64x | 2.57x | 0.64x |
| MiMo-V2.6-Flash | 1024 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2,402.2 | 2,459,822.3 | compute | MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 1,228.67 | 530.1 | 542,839.0 | link_latency | 4.53x | 4.53x | 14.23x | 4.53x |
| MiMo-V2.6-Flash | 1024 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x33 | 26,895 | 55.0 | 56,329.0 | compute | MiMo-V2.6-Flash/b200_sxm-x17-nvl72-tensor | 27,200 | 0.99x | tensor | 2,756.85 | 158.9 | 162,760.4 | link_latency | 0.35x | 0.35x | 1.42x | 0.35x |
| MiMo-V2.6-Flash | 4096 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 614.1 | 2,515,536.2 | compute | MiMo-V2.6-Flash/b200_sxm-x173-expert | 276,800 | 1.00x | expert | 3,851.84 | 187.5 | 767,872.5 | link_latency | 3.28x | 3.28x | 9.77x | 3.28x |
| MiMo-V2.6-Flash | 4096 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x33 | 26,895 | 13.8 | 56,356.6 | compute | MiMo-V2.6-Flash/b200_sxm-x17-hybrid | 27,200 | 0.99x | hybrid | 3,813.60 | 61.0 | 249,910.3 | kv_read | 0.23x | 0.23x | 0.50x | 0.23x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| MiMo-V2.6-Flash | 7 | 11,200 | 232.65 | 232.65 | 1,895.5 | 1,895.5 |
| MiMo-V2.6-Flash | 8 | 12,800 | 232.69 | 232.69 | 2,032.1 | 2,032.1 |
| MiMo-V2.6-Flash | 15 | 24,000 | 232.85 | 232.85 | 2,657.8 | 2,657.8 |
| MiMo-V2.6-Flash | 16 | 25,600 | 232.86 | 232.86 | 2,717.6 | 2,717.6 |
| MiMo-V2.6-Flash | 17 | 27,200 | 232.87 | 232.87 | 2,772.6 | 2,772.6 |
| MiMo-V2.6-Flash | 18 | 28,800 | 232.88 | 232.88 | 2,823.4 | 2,823.4 |
| MiMo-V2.6-Flash | 19 | 30,400 | 232.88 | 232.88 | 2,870.4 | 2,870.4 |
| MiMo-V2.6-Flash | 21 | 33,600 | 232.90 | 232.90 | 2,954.9 | 2,954.9 |
| MiMo-V2.6-Flash | 22 | 35,200 | 232.90 | 232.90 | 2,992.9 | 2,992.9 |
| MiMo-V2.6-Flash | 23 | 36,800 | 232.91 | 232.91 | 3,028.5 | 3,028.5 |
| MiMo-V2.6-Flash | 24 | 38,400 | 232.91 | 232.91 | 3,061.8 | 3,061.8 |
| MiMo-V2.6-Flash | 25 | 40,000 | 232.92 | 232.92 | 3,093.2 | 3,093.2 |
| MiMo-V2.6-Flash | 29 | 46,400 | 232.93 | 232.93 | 3,201.7 | 3,201.7 |
| MiMo-V2.6-Flash | 31 | 49,600 | 232.94 | 232.94 | 3,247.6 | 3,247.6 |
| MiMo-V2.6-Flash | 43 | 68,800 | 232.96 | 232.96 | 3,447.8 | 3,447.8 |
| MiMo-V2.6-Flash | 46 | 73,600 | 232.96 | 232.96 | 3,484.0 | 3,484.0 |
| MiMo-V2.6-Flash | 57 | 91,200 | 232.98 | 232.98 | 3,588.1 | 3,588.1 |
| MiMo-V2.6-Flash | 58 | 92,800 | 232.98 | 232.98 | 3,595.9 | 3,595.9 |
| MiMo-V2.6-Flash | 61 | 97,600 | 232.98 | 232.98 | 3,617.8 | 3,617.8 |
| MiMo-V2.6-Flash | 87 | 139,200 | 235.18 | 235.18 | 3,427.9 | 3,427.9 |
| MiMo-V2.6-Flash | 116 | 185,600 | 235.18 | 235.18 | 3,567.6 | 3,567.6 |
| MiMo-V2.6-Flash | 173 | 276,800 | 237.37 | 237.37 | 3,537.4 | 3,537.4 |
| MiMo-V2.6-Flash | 231 | 369,600 | 239.57 | 239.57 | 3,510.8 | 3,510.8 |
| MiMo-V2.6-Flash | 347 | 555,200 | 241.76 | 241.76 | 3,555.6 | 3,555.6 |

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
| MiMo-V2.6-Flash | 7 | 11,200 | 478.7 | 1,895.5 | — | tensor | 232.65 | 44.1% | weight_read |
| MiMo-V2.6-Flash | 8 | 12,800 | 478.7 | 2,032.1 | — | tensor | 232.69 | 47.3% | link_latency |
| MiMo-V2.6-Flash | 15 | 24,000 | 478.7 | 2,657.8 | 1,957.5 | tensor | 232.85 | 61.9% | link_latency |
| MiMo-V2.6-Flash | 16 | 25,600 | 478.7 | 2,717.6 | 2,023.1 | tensor | 232.86 | 63.3% | link_latency |
| MiMo-V2.6-Flash | 17 | 27,200 | 478.7 | 2,772.6 | 1,669.9 | tensor | 232.87 | 64.6% | link_latency |
| MiMo-V2.6-Flash | 18 | 28,800 | 478.7 | 2,823.4 | 1,726.1 | tensor | 232.88 | 65.7% | link_latency |
| MiMo-V2.6-Flash | 19 | 30,400 | 478.7 | 2,870.4 | 1,779.7 | tensor | 232.88 | 66.8% | link_latency |
| MiMo-V2.6-Flash | 21 | 33,600 | 478.7 | 2,954.9 | 1,879.7 | tensor | 232.90 | 68.8% | link_latency |
| MiMo-V2.6-Flash | 22 | 35,200 | 478.7 | 2,992.9 | 1,926.5 | tensor | 232.90 | 69.7% | link_latency |
| MiMo-V2.6-Flash | 23 | 36,800 | 478.7 | 3,028.5 | 1,971.2 | tensor | 232.91 | 70.5% | link_latency |
| MiMo-V2.6-Flash | 24 | 38,400 | 478.7 | 3,061.8 | 2,014.1 | tensor | 232.91 | 71.3% | link_latency |
| MiMo-V2.6-Flash | 25 | 40,000 | 478.7 | 3,093.2 | 1,759.7 | tensor | 232.92 | 72.0% | link_latency |
| MiMo-V2.6-Flash | 29 | 46,400 | 478.7 | 3,201.7 | 1,907.0 | tensor | 232.93 | 74.6% | link_latency |
| MiMo-V2.6-Flash | 31 | 49,600 | 478.7 | 3,247.6 | 1,973.6 | tensor | 232.94 | 75.6% | link_latency |
| MiMo-V2.6-Flash | 43 | 68,800 | 478.7 | 3,447.8 | 1,879.8 | tensor | 232.96 | 80.3% | link_latency |
| MiMo-V2.6-Flash | 46 | 73,600 | 478.7 | 3,484.0 | 1,946.0 | tensor | 232.96 | 81.2% | link_latency |
| MiMo-V2.6-Flash | 57 | 91,200 | 478.7 | 3,588.1 | 1,858.8 | tensor | 232.98 | 83.6% | link_latency |
| MiMo-V2.6-Flash | 58 | 92,800 | 478.7 | 3,595.9 | 1,875.6 | tensor | 232.98 | 83.8% | link_latency |
| MiMo-V2.6-Flash | 61 | 97,600 | 478.7 | 3,617.8 | 1,924.3 | tensor | 232.98 | 84.3% | link_latency |
| MiMo-V2.6-Flash | 87 | 139,200 | 478.7 | 1,470.5 | 3,427.9 | hybrid | 235.18 | 80.6% | link_latency |
| MiMo-V2.6-Flash | 116 | 185,600 | 478.7 | 1,483.0 | 3,567.6 | hybrid | 235.18 | 83.9% | link_latency |
| MiMo-V2.6-Flash | 173 | 276,800 | 478.7 | 1,478.1 | 3,537.4 | hybrid | 237.37 | 84.0% | link_latency |
| MiMo-V2.6-Flash | 231 | 369,600 | 478.7 | 1,475.8 | 3,510.8 | hybrid | 239.57 | 84.1% | link_latency |
| MiMo-V2.6-Flash | 347 | 555,200 | 478.7 | 1,477.0 | 3,555.6 | hybrid | 241.76 | 86.0% | link_latency |

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
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x33 | MiMo-V2.6-Flash | 33 | pipeline | rom_package_ucie | rom_board_serdes | 32 | 1.13 us | 88,844.6 tok/s | 888,445.9 tok/s | 24 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.29 us; 8 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.84 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x33 | MiMo-V2.6-Flash | 33 | tensor | rom_package_ucie | rom_board_serdes | 192 | 45.77 us | 2,185.0 tok/s | 21,849.6 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 96 x all_reduce span 9 on rom_board_serdes (traversals 4.4) = 43.41 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x33 | MiMo-V2.6-Flash | 33 | hybrid | rom_package_ucie | rom_board_serdes | 104 | 3.20 us | 31,261.9 tok/s | 312,619.5 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 8 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.84 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x33 | MiMo-V2.6-Flash | 33 | pipeline | nvlink5 | infiniband_ndr | 32 | 42.63 us | 2,345.8 tok/s | 23,457.5 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.85 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | MiMo-V2.6-Flash | 1 | pipeline | on_wafer_n5 | rom_wafer_serdes | 47 | 5.88 us | 17,021.2 tok/s | 170,212.3 tok/s | 47 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.88 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-tensor-x30 | MiMo-V2.6-Flash | 30 | tensor | nvlink5 | infiniband_ndr | 192 | 657.84 us | 152.0 tok/s | 1,520.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | MiMo-V2.6-Flash | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 96 | 184.80 us | 541.1 tok/s | 5,411.3 tok/s | 96 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 184.80 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hybrid-x32 | MiMo-V2.6-Flash | 32 | hybrid | nvlink5 | infiniband_ndr | 99 | 239.28 us | 417.9 tok/s | 4,179.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x50 | MiMo-V2.6-Flash | 50 | pipeline | rom_package_ucie | rom_board_serdes | 47 | 1.58 us | 63,139.7 tok/s | 631,396.8 tok/s | 36 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.43 us; 11 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.15 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x36 | MiMo-V2.6-Flash | 36 | tensor | rom_package_ucie | rom_board_serdes | 192 | 45.77 us | 2,185.0 tok/s | 21,849.6 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 96 x all_reduce span 9 on rom_board_serdes (traversals 4.4) = 43.41 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x48 | MiMo-V2.6-Flash | 48 | hybrid | rom_package_ucie | rom_board_serdes | 107 | 3.51 us | 28,470.3 tok/s | 284,703.2 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 11 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.15 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-pipeline-x49 | MiMo-V2.6-Flash | 49 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2 | MiMo-V2.6-Flash | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 47 | 5.88 us | 17,021.2 tok/s | 170,212.3 tok/s | 47 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.88 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-tensor-x33 | MiMo-V2.6-Flash | 33 | tensor | nvlink5 | infiniband_ndr | 192 | 660.20 us | 151.5 tok/s | 1,514.7 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 427.51 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-tensor-x2 | MiMo-V2.6-Flash | 2 | tensor | on_wafer_n5 | rom_wafer_serdes | 192 | 206.12 us | 485.2 tok/s | 4,851.6 tok/s | 96 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 184.80 us; 96 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 21.32 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hybrid-x44 | MiMo-V2.6-Flash | 44 | hybrid | nvlink5 | infiniband_ndr | 101 | 243.66 us | 410.4 tok/s | 4,104.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | MiMo-V2.6-Flash | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 97 | 184.90 us | 540.8 tok/s | 5,408.3 tok/s | 96 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 184.80 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Flash/b200_sxm-x7-pipeline | MiMo-V2.6-Flash | 7 | pipeline | nvlink5 | infiniband_ndr | 6 | 7.25 us | 13,784.3 tok/s | 137,843.3 tok/s | 6 x point_to_point span 2 on nvlink5 (traversals 1.0) = 7.25 us |
| MiMo-V2.6-Flash/b200_sxm-x7-tensor | MiMo-V2.6-Flash | 7 | tensor | nvlink5 | infiniband_ndr | 96 | 232.65 us | 429.8 tok/s | 4,298.4 tok/s | 96 x all_reduce span 7 on nvlink5 (traversals 2.0) = 232.65 us |
| MiMo-V2.6-Flash/b200_sxm-x7-nvl72-tensor | MiMo-V2.6-Flash | 7 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.65 us | 429.8 tok/s | 4,298.4 tok/s | 96 x all_reduce span 7 on nvlink5_nvl72 (traversals 2.0) = 232.65 us |
| MiMo-V2.6-Flash/b200_sxm-x7-expert | MiMo-V2.6-Flash | 7 | expert | nvlink5 | infiniband_ndr | 192 | 348.85 us | 286.7 tok/s | 2,866.6 tok/s | 96 x all_reduce span 7 on nvlink5 (traversals 2.0) = 232.65 us; 96 x point_to_point span 2 on nvlink5 (traversals 1.0) = 116.20 us |
| MiMo-V2.6-Flash/b200_sxm-x7-nvl72-expert | MiMo-V2.6-Flash | 7 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.85 us | 286.7 tok/s | 2,866.6 tok/s | 96 x all_reduce span 7 on nvlink5_nvl72 (traversals 2.0) = 232.65 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 116.20 us |
| MiMo-V2.6-Flash/b200_sxm-x8-pipeline | MiMo-V2.6-Flash | 8 | pipeline | nvlink5 | infiniband_ndr | 7 | 8.46 us | 11,815.1 tok/s | 118,151.4 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.46 us |
| MiMo-V2.6-Flash/b200_sxm-x8-tensor | MiMo-V2.6-Flash | 8 | tensor | nvlink5 | infiniband_ndr | 96 | 232.69 us | 429.7 tok/s | 4,297.5 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us |
| MiMo-V2.6-Flash/b200_sxm-x8-nvl72-tensor | MiMo-V2.6-Flash | 8 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.69 us | 429.7 tok/s | 4,297.5 tok/s | 96 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 232.69 us |
| MiMo-V2.6-Flash/b200_sxm-x8-expert | MiMo-V2.6-Flash | 8 | expert | nvlink5 | infiniband_ndr | 192 | 348.77 us | 286.7 tok/s | 2,867.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x point_to_point span 2 on nvlink5 (traversals 1.0) = 116.07 us |
| MiMo-V2.6-Flash/b200_sxm-x8-nvl72-expert | MiMo-V2.6-Flash | 8 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.77 us | 286.7 tok/s | 2,867.2 tok/s | 96 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 232.69 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 116.07 us |
| MiMo-V2.6-Flash/b200_sxm-x15-pipeline | MiMo-V2.6-Flash | 15 | pipeline | nvlink5 | infiniband_ndr | 14 | 17.91 us | 5,582.8 tok/s | 55,828.0 tok/s | 13 x point_to_point span 2 on nvlink5 (traversals 1.0) = 15.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x15-tensor | MiMo-V2.6-Flash | 15 | tensor | nvlink5 | infiniband_ndr | 192 | 646.05 us | 154.8 tok/s | 1,547.9 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 413.35 us |
| MiMo-V2.6-Flash/b200_sxm-x15-hybrid | MiMo-V2.6-Flash | 15 | hybrid | nvlink5 | infiniband_ndr | 97 | 234.89 us | 425.7 tok/s | 4,257.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x15-nvl72-tensor | MiMo-V2.6-Flash | 15 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.85 us | 429.5 tok/s | 4,294.7 tok/s | 96 x all_reduce span 15 on nvlink5_nvl72 (traversals 2.0) = 232.85 us |
| MiMo-V2.6-Flash/b200_sxm-x15-expert | MiMo-V2.6-Flash | 15 | expert | nvlink5 | infiniband_ndr | 192 | 435.96 us | 229.4 tok/s | 2,293.8 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 203.27 us |
| MiMo-V2.6-Flash/b200_sxm-x15-nvl72-expert | MiMo-V2.6-Flash | 15 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.51 us | 286.9 tok/s | 2,869.3 tok/s | 96 x all_reduce span 15 on nvlink5_nvl72 (traversals 2.0) = 232.85 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.67 us |
| MiMo-V2.6-Flash/b200_sxm-x16-pipeline | MiMo-V2.6-Flash | 16 | pipeline | nvlink5 | infiniband_ndr | 15 | 19.12 us | 5,229.8 tok/s | 52,297.8 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x16-tensor | MiMo-V2.6-Flash | 16 | tensor | nvlink5 | infiniband_ndr | 192 | 646.05 us | 154.8 tok/s | 1,547.9 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 413.35 us |
| MiMo-V2.6-Flash/b200_sxm-x16-hybrid | MiMo-V2.6-Flash | 16 | hybrid | nvlink5 | infiniband_ndr | 97 | 234.89 us | 425.7 tok/s | 4,257.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x16-nvl72-tensor | MiMo-V2.6-Flash | 16 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.86 us | 429.4 tok/s | 4,294.5 tok/s | 96 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 232.86 us |
| MiMo-V2.6-Flash/b200_sxm-x16-expert | MiMo-V2.6-Flash | 16 | expert | nvlink5 | infiniband_ndr | 192 | 434.29 us | 230.3 tok/s | 2,302.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 202.74 us |
| MiMo-V2.6-Flash/b200_sxm-x16-nvl72-expert | MiMo-V2.6-Flash | 16 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.49 us | 286.9 tok/s | 2,869.5 tok/s | 96 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 232.86 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.64 us |
| MiMo-V2.6-Flash/b200_sxm-x17-pipeline | MiMo-V2.6-Flash | 17 | pipeline | nvlink5 | infiniband_ndr | 16 | 21.32 us | 4,691.5 tok/s | 46,915.1 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x17-tensor | MiMo-V2.6-Flash | 17 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x17-hybrid | MiMo-V2.6-Flash | 17 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x17-nvl72-tensor | MiMo-V2.6-Flash | 17 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.87 us | 429.4 tok/s | 4,294.3 tok/s | 96 x all_reduce span 17 on nvlink5_nvl72 (traversals 2.0) = 232.87 us |
| MiMo-V2.6-Flash/b200_sxm-x17-expert | MiMo-V2.6-Flash | 17 | expert | nvlink5 | infiniband_ndr | 192 | 433.83 us | 230.5 tok/s | 2,305.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 202.28 us |
| MiMo-V2.6-Flash/b200_sxm-x17-nvl72-expert | MiMo-V2.6-Flash | 17 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.48 us | 287.0 tok/s | 2,869.6 tok/s | 96 x all_reduce span 17 on nvlink5_nvl72 (traversals 2.0) = 232.87 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.61 us |
| MiMo-V2.6-Flash/b200_sxm-x18-pipeline | MiMo-V2.6-Flash | 18 | pipeline | nvlink5 | infiniband_ndr | 17 | 22.52 us | 4,439.7 tok/s | 44,396.7 tok/s | 15 x point_to_point span 2 on nvlink5 (traversals 1.0) = 18.14 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x18-tensor | MiMo-V2.6-Flash | 18 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x18-hybrid | MiMo-V2.6-Flash | 18 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x18-nvl72-tensor | MiMo-V2.6-Flash | 18 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.88 us | 429.4 tok/s | 4,294.1 tok/s | 96 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 232.88 us |
| MiMo-V2.6-Flash/b200_sxm-x18-expert | MiMo-V2.6-Flash | 18 | expert | nvlink5 | infiniband_ndr | 192 | 433.42 us | 230.7 tok/s | 2,307.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 201.87 us |
| MiMo-V2.6-Flash/b200_sxm-x18-nvl72-expert | MiMo-V2.6-Flash | 18 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.46 us | 287.0 tok/s | 2,869.7 tok/s | 96 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 232.88 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.59 us |
| MiMo-V2.6-Flash/b200_sxm-x19-pipeline | MiMo-V2.6-Flash | 19 | pipeline | nvlink5 | infiniband_ndr | 18 | 23.73 us | 4,213.5 tok/s | 42,134.9 tok/s | 16 x point_to_point span 2 on nvlink5 (traversals 1.0) = 19.35 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x19-tensor | MiMo-V2.6-Flash | 19 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x19-hybrid | MiMo-V2.6-Flash | 19 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x19-nvl72-tensor | MiMo-V2.6-Flash | 19 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.88 us | 429.4 tok/s | 4,294.0 tok/s | 96 x all_reduce span 19 on nvlink5_nvl72 (traversals 2.0) = 232.88 us |
| MiMo-V2.6-Flash/b200_sxm-x19-expert | MiMo-V2.6-Flash | 19 | expert | nvlink5 | infiniband_ndr | 192 | 433.05 us | 230.9 tok/s | 2,309.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 201.50 us |
| MiMo-V2.6-Flash/b200_sxm-x19-nvl72-expert | MiMo-V2.6-Flash | 19 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.45 us | 287.0 tok/s | 2,869.8 tok/s | 96 x all_reduce span 19 on nvlink5_nvl72 (traversals 2.0) = 232.88 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.57 us |
| MiMo-V2.6-Flash/b200_sxm-x21-pipeline | MiMo-V2.6-Flash | 21 | pipeline | nvlink5 | infiniband_ndr | 20 | 26.15 us | 3,823.9 tok/s | 38,238.7 tok/s | 18 x point_to_point span 2 on nvlink5 (traversals 1.0) = 21.76 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x21-tensor | MiMo-V2.6-Flash | 21 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x21-hybrid | MiMo-V2.6-Flash | 21 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x21-nvl72-tensor | MiMo-V2.6-Flash | 21 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.90 us | 429.4 tok/s | 4,293.8 tok/s | 96 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 232.90 us |
| MiMo-V2.6-Flash/b200_sxm-x21-expert | MiMo-V2.6-Flash | 21 | expert | nvlink5 | infiniband_ndr | 192 | 432.42 us | 231.3 tok/s | 2,312.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 200.87 us |
| MiMo-V2.6-Flash/b200_sxm-x21-nvl72-expert | MiMo-V2.6-Flash | 21 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.43 us | 287.0 tok/s | 2,870.0 tok/s | 96 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 232.90 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.53 us |
| MiMo-V2.6-Flash/b200_sxm-x22-pipeline | MiMo-V2.6-Flash | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 27.36 us | 3,654.9 tok/s | 36,548.9 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 22.97 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x22-tensor | MiMo-V2.6-Flash | 22 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x22-hybrid | MiMo-V2.6-Flash | 22 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x22-nvl72-tensor | MiMo-V2.6-Flash | 22 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.90 us | 429.4 tok/s | 4,293.6 tok/s | 96 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 232.90 us |
| MiMo-V2.6-Flash/b200_sxm-x22-expert | MiMo-V2.6-Flash | 22 | expert | nvlink5 | infiniband_ndr | 192 | 432.15 us | 231.4 tok/s | 2,314.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 200.60 us |
| MiMo-V2.6-Flash/b200_sxm-x22-nvl72-expert | MiMo-V2.6-Flash | 22 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.42 us | 287.0 tok/s | 2,870.1 tok/s | 96 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 232.90 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.52 us |
| MiMo-V2.6-Flash/b200_sxm-x23-pipeline | MiMo-V2.6-Flash | 23 | pipeline | nvlink5 | infiniband_ndr | 22 | 28.57 us | 3,500.2 tok/s | 35,002.1 tok/s | 20 x point_to_point span 2 on nvlink5 (traversals 1.0) = 24.18 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x23-tensor | MiMo-V2.6-Flash | 23 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x23-hybrid | MiMo-V2.6-Flash | 23 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x23-nvl72-tensor | MiMo-V2.6-Flash | 23 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.91 us | 429.4 tok/s | 4,293.6 tok/s | 96 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 232.91 us |
| MiMo-V2.6-Flash/b200_sxm-x23-expert | MiMo-V2.6-Flash | 23 | expert | nvlink5 | infiniband_ndr | 192 | 431.90 us | 231.5 tok/s | 2,315.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 200.35 us |
| MiMo-V2.6-Flash/b200_sxm-x23-nvl72-expert | MiMo-V2.6-Flash | 23 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.41 us | 287.0 tok/s | 2,870.2 tok/s | 96 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 232.91 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.50 us |
| MiMo-V2.6-Flash/b200_sxm-x24-pipeline | MiMo-V2.6-Flash | 24 | pipeline | nvlink5 | infiniband_ndr | 23 | 29.78 us | 3,358.1 tok/s | 33,580.9 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x24-tensor | MiMo-V2.6-Flash | 24 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x24-hybrid | MiMo-V2.6-Flash | 24 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x24-nvl72-tensor | MiMo-V2.6-Flash | 24 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.91 us | 429.3 tok/s | 4,293.5 tok/s | 96 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 232.91 us |
| MiMo-V2.6-Flash/b200_sxm-x24-expert | MiMo-V2.6-Flash | 24 | expert | nvlink5 | infiniband_ndr | 192 | 431.29 us | 231.9 tok/s | 2,318.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.16 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 200.12 us |
| MiMo-V2.6-Flash/b200_sxm-x24-nvl72-expert | MiMo-V2.6-Flash | 24 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.40 us | 287.0 tok/s | 2,870.2 tok/s | 96 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 232.91 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.49 us |
| MiMo-V2.6-Flash/b200_sxm-x25-pipeline | MiMo-V2.6-Flash | 25 | pipeline | nvlink5 | infiniband_ndr | 24 | 31.97 us | 3,127.7 tok/s | 31,276.7 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x25-tensor | MiMo-V2.6-Flash | 25 | tensor | nvlink5 | infiniband_ndr | 192 | 657.84 us | 152.0 tok/s | 1,520.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/b200_sxm-x25-hybrid | MiMo-V2.6-Flash | 25 | hybrid | nvlink5 | infiniband_ndr | 99 | 239.28 us | 417.9 tok/s | 4,179.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x25-nvl72-tensor | MiMo-V2.6-Flash | 25 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.92 us | 429.3 tok/s | 4,293.4 tok/s | 96 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 232.92 us |
| MiMo-V2.6-Flash/b200_sxm-x25-expert | MiMo-V2.6-Flash | 25 | expert | nvlink5 | infiniband_ndr | 192 | 431.08 us | 232.0 tok/s | 2,319.8 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.16 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 199.91 us |
| MiMo-V2.6-Flash/b200_sxm-x25-nvl72-expert | MiMo-V2.6-Flash | 25 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.40 us | 287.0 tok/s | 2,870.3 tok/s | 96 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 232.92 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.48 us |
| MiMo-V2.6-Flash/b200_sxm-x29-pipeline | MiMo-V2.6-Flash | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x29-tensor | MiMo-V2.6-Flash | 29 | tensor | nvlink5 | infiniband_ndr | 192 | 657.84 us | 152.0 tok/s | 1,520.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/b200_sxm-x29-hybrid | MiMo-V2.6-Flash | 29 | hybrid | nvlink5 | infiniband_ndr | 99 | 239.28 us | 417.9 tok/s | 4,179.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x29-nvl72-tensor | MiMo-V2.6-Flash | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.93 us | 429.3 tok/s | 4,293.1 tok/s | 96 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 232.93 us |
| MiMo-V2.6-Flash/b200_sxm-x29-expert | MiMo-V2.6-Flash | 29 | expert | nvlink5 | infiniband_ndr | 192 | 430.38 us | 232.4 tok/s | 2,323.5 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.16 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 199.22 us |
| MiMo-V2.6-Flash/b200_sxm-x29-nvl72-expert | MiMo-V2.6-Flash | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.37 us | 287.0 tok/s | 2,870.5 tok/s | 96 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 232.93 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.44 us |
| MiMo-V2.6-Flash/b200_sxm-x31-pipeline | MiMo-V2.6-Flash | 31 | pipeline | nvlink5 | infiniband_ndr | 30 | 39.23 us | 2,549.2 tok/s | 25,492.5 tok/s | 27 x point_to_point span 2 on nvlink5 (traversals 1.0) = 32.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x31-tensor | MiMo-V2.6-Flash | 31 | tensor | nvlink5 | infiniband_ndr | 192 | 657.84 us | 152.0 tok/s | 1,520.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/b200_sxm-x31-hybrid | MiMo-V2.6-Flash | 31 | hybrid | nvlink5 | infiniband_ndr | 99 | 239.28 us | 417.9 tok/s | 4,179.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x31-nvl72-tensor | MiMo-V2.6-Flash | 31 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.94 us | 429.3 tok/s | 4,293.0 tok/s | 96 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 232.94 us |
| MiMo-V2.6-Flash/b200_sxm-x31-expert | MiMo-V2.6-Flash | 31 | expert | nvlink5 | infiniband_ndr | 192 | 430.10 us | 232.5 tok/s | 2,325.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.16 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 198.94 us |
| MiMo-V2.6-Flash/b200_sxm-x31-nvl72-expert | MiMo-V2.6-Flash | 31 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.36 us | 287.1 tok/s | 2,870.6 tok/s | 96 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 232.94 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.43 us |
| MiMo-V2.6-Flash/b200_sxm-x43-pipeline | MiMo-V2.6-Flash | 43 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x43-tensor | MiMo-V2.6-Flash | 43 | tensor | nvlink5 | infiniband_ndr | 192 | 661.78 us | 151.1 tok/s | 1,511.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 429.08 us |
| MiMo-V2.6-Flash/b200_sxm-x43-hybrid | MiMo-V2.6-Flash | 43 | hybrid | nvlink5 | infiniband_ndr | 101 | 243.66 us | 410.4 tok/s | 4,104.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x43-nvl72-tensor | MiMo-V2.6-Flash | 43 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.96 us | 429.3 tok/s | 4,292.6 tok/s | 96 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 232.96 us |
| MiMo-V2.6-Flash/b200_sxm-x43-expert | MiMo-V2.6-Flash | 43 | expert | nvlink5 | infiniband_ndr | 192 | 428.67 us | 233.3 tok/s | 2,332.8 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.86 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 197.81 us |
| MiMo-V2.6-Flash/b200_sxm-x43-nvl72-expert | MiMo-V2.6-Flash | 43 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.32 us | 287.1 tok/s | 2,870.9 tok/s | 96 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 232.96 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.36 us |
| MiMo-V2.6-Flash/b200_sxm-x46-pipeline | MiMo-V2.6-Flash | 46 | pipeline | nvlink5 | infiniband_ndr | 45 | 59.33 us | 1,685.4 tok/s | 16,853.9 tok/s | 40 x point_to_point span 2 on nvlink5 (traversals 1.0) = 48.36 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x46-tensor | MiMo-V2.6-Flash | 46 | tensor | nvlink5 | infiniband_ndr | 192 | 661.78 us | 151.1 tok/s | 1,511.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 429.08 us |
| MiMo-V2.6-Flash/b200_sxm-x46-hybrid | MiMo-V2.6-Flash | 46 | hybrid | nvlink5 | infiniband_ndr | 101 | 243.66 us | 410.4 tok/s | 4,104.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x46-nvl72-tensor | MiMo-V2.6-Flash | 46 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.96 us | 429.3 tok/s | 4,292.5 tok/s | 96 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 232.96 us |
| MiMo-V2.6-Flash/b200_sxm-x46-expert | MiMo-V2.6-Flash | 46 | expert | nvlink5 | infiniband_ndr | 192 | 428.47 us | 233.4 tok/s | 2,333.9 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.86 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 197.62 us |
| MiMo-V2.6-Flash/b200_sxm-x46-nvl72-expert | MiMo-V2.6-Flash | 46 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.32 us | 287.1 tok/s | 2,871.0 tok/s | 96 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 232.96 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.35 us |
| MiMo-V2.6-Flash/b200_sxm-x57-pipeline | MiMo-V2.6-Flash | 57 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x57-tensor | MiMo-V2.6-Flash | 57 | tensor | nvlink5 | infiniband_ndr | 192 | 663.74 us | 150.7 tok/s | 1,506.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 431.05 us |
| MiMo-V2.6-Flash/b200_sxm-x57-hybrid | MiMo-V2.6-Flash | 57 | hybrid | nvlink5 | infiniband_ndr | 103 | 248.05 us | 403.1 tok/s | 4,031.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| MiMo-V2.6-Flash/b200_sxm-x57-nvl72-tensor | MiMo-V2.6-Flash | 57 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.98 us | 429.2 tok/s | 4,292.3 tok/s | 96 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 232.98 us |
| MiMo-V2.6-Flash/b200_sxm-x57-expert | MiMo-V2.6-Flash | 57 | expert | nvlink5 | infiniband_ndr | 192 | 427.82 us | 233.7 tok/s | 2,337.5 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.73 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 197.09 us |
| MiMo-V2.6-Flash/b200_sxm-x57-nvl72-expert | MiMo-V2.6-Flash | 57 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.30 us | 287.1 tok/s | 2,871.1 tok/s | 96 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 232.98 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.32 us |
| MiMo-V2.6-Flash/b200_sxm-x58-pipeline | MiMo-V2.6-Flash | 58 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x58-tensor | MiMo-V2.6-Flash | 58 | tensor | nvlink5 | infiniband_ndr | 192 | 663.74 us | 150.7 tok/s | 1,506.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 431.05 us |
| MiMo-V2.6-Flash/b200_sxm-x58-hybrid | MiMo-V2.6-Flash | 58 | hybrid | nvlink5 | infiniband_ndr | 103 | 248.05 us | 403.1 tok/s | 4,031.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| MiMo-V2.6-Flash/b200_sxm-x58-nvl72-tensor | MiMo-V2.6-Flash | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.98 us | 429.2 tok/s | 4,292.3 tok/s | 96 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 232.98 us |
| MiMo-V2.6-Flash/b200_sxm-x58-expert | MiMo-V2.6-Flash | 58 | expert | nvlink5 | infiniband_ndr | 192 | 427.78 us | 233.8 tok/s | 2,337.7 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.73 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 197.05 us |
| MiMo-V2.6-Flash/b200_sxm-x58-nvl72-expert | MiMo-V2.6-Flash | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.30 us | 287.1 tok/s | 2,871.1 tok/s | 96 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 232.98 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.32 us |
| MiMo-V2.6-Flash/b200_sxm-x61-pipeline | MiMo-V2.6-Flash | 61 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x61-tensor | MiMo-V2.6-Flash | 61 | tensor | nvlink5 | infiniband_ndr | 192 | 663.74 us | 150.7 tok/s | 1,506.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 431.05 us |
| MiMo-V2.6-Flash/b200_sxm-x61-hybrid | MiMo-V2.6-Flash | 61 | hybrid | nvlink5 | infiniband_ndr | 103 | 248.05 us | 403.1 tok/s | 4,031.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| MiMo-V2.6-Flash/b200_sxm-x61-nvl72-tensor | MiMo-V2.6-Flash | 61 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.98 us | 429.2 tok/s | 4,292.2 tok/s | 96 x all_reduce span 61 on nvlink5_nvl72 (traversals 2.0) = 232.98 us |
| MiMo-V2.6-Flash/b200_sxm-x61-expert | MiMo-V2.6-Flash | 61 | expert | nvlink5 | infiniband_ndr | 192 | 427.67 us | 233.8 tok/s | 2,338.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.73 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 196.94 us |
| MiMo-V2.6-Flash/b200_sxm-x61-nvl72-expert | MiMo-V2.6-Flash | 61 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.29 us | 287.1 tok/s | 2,871.1 tok/s | 96 x all_reduce span 61 on nvlink5_nvl72 (traversals 2.0) = 232.98 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.31 us |
| MiMo-V2.6-Flash/b200_sxm-x87-pipeline | MiMo-V2.6-Flash | 87 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x87-tensor | MiMo-V2.6-Flash | 87 | tensor | nvlink5 | infiniband_ndr | 192 | 665.35 us | 150.3 tok/s | 1,503.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 432.66 us |
| MiMo-V2.6-Flash/b200_sxm-x87-hybrid | MiMo-V2.6-Flash | 87 | hybrid | nvlink5 | infiniband_ndr | 106 | 254.63 us | 392.7 tok/s | 3,927.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| MiMo-V2.6-Flash/b200_sxm-x87-nvl72-tensor | MiMo-V2.6-Flash | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 646.34 us | 154.7 tok/s | 1,547.2 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 413.35 us |
| MiMo-V2.6-Flash/b200_sxm-x87-nvl72-hybrid | MiMo-V2.6-Flash | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 97 | 235.18 us | 425.2 tok/s | 4,252.1 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x87-expert | MiMo-V2.6-Flash | 87 | expert | nvlink5 | infiniband_ndr | 192 | 426.96 us | 234.2 tok/s | 2,342.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.63 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 196.33 us |
| MiMo-V2.6-Flash/b200_sxm-x87-nvl72-expert | MiMo-V2.6-Flash | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 429.31 us | 232.9 tok/s | 2,329.3 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 196.33 us |
| MiMo-V2.6-Flash/b200_sxm-x116-pipeline | MiMo-V2.6-Flash | 116 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x116-tensor | MiMo-V2.6-Flash | 116 | tensor | nvlink5 | infiniband_ndr | 192 | 666.49 us | 150.0 tok/s | 1,500.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 433.80 us |
| MiMo-V2.6-Flash/b200_sxm-x116-hybrid | MiMo-V2.6-Flash | 116 | hybrid | nvlink5 | infiniband_ndr | 110 | 263.41 us | 379.6 tok/s | 3,796.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| MiMo-V2.6-Flash/b200_sxm-x116-nvl72-tensor | MiMo-V2.6-Flash | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 646.34 us | 154.7 tok/s | 1,547.2 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 413.35 us |
| MiMo-V2.6-Flash/b200_sxm-x116-nvl72-hybrid | MiMo-V2.6-Flash | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 97 | 235.18 us | 425.2 tok/s | 4,252.1 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x116-expert | MiMo-V2.6-Flash | 116 | expert | nvlink5 | infiniband_ndr | 192 | 426.53 us | 234.5 tok/s | 2,344.5 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.56 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.96 us |
| MiMo-V2.6-Flash/b200_sxm-x116-nvl72-expert | MiMo-V2.6-Flash | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 428.95 us | 233.1 tok/s | 2,331.3 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.96 us |
| MiMo-V2.6-Flash/b200_sxm-x173-pipeline | MiMo-V2.6-Flash | 173 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x173-tensor | MiMo-V2.6-Flash | 173 | tensor | nvlink5 | infiniband_ndr | 192 | 667.49 us | 149.8 tok/s | 1,498.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 434.80 us |
| MiMo-V2.6-Flash/b200_sxm-x173-hybrid | MiMo-V2.6-Flash | 173 | hybrid | nvlink5 | infiniband_ndr | 117 | 278.76 us | 358.7 tok/s | 3,587.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| MiMo-V2.6-Flash/b200_sxm-x173-nvl72-tensor | MiMo-V2.6-Flash | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 654.20 us | 152.9 tok/s | 1,528.6 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid | MiMo-V2.6-Flash | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 98 | 237.37 us | 421.3 tok/s | 4,212.8 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x173-expert | MiMo-V2.6-Flash | 173 | expert | nvlink5 | infiniband_ndr | 192 | 426.12 us | 234.7 tok/s | 2,346.8 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.51 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.61 us |
| MiMo-V2.6-Flash/b200_sxm-x173-nvl72-expert | MiMo-V2.6-Flash | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 427.30 us | 234.0 tok/s | 2,340.3 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 231.69 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.61 us |
| MiMo-V2.6-Flash/b200_sxm-x231-pipeline | MiMo-V2.6-Flash | 231 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x231-tensor | MiMo-V2.6-Flash | 231 | tensor | nvlink5 | infiniband_ndr | 192 | 668.01 us | 149.7 tok/s | 1,497.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 435.32 us |
| MiMo-V2.6-Flash/b200_sxm-x231-hybrid | MiMo-V2.6-Flash | 231 | hybrid | nvlink5 | infiniband_ndr | 124 | 294.12 us | 340.0 tok/s | 3,400.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 61.43 us |
| MiMo-V2.6-Flash/b200_sxm-x231-nvl72-tensor | MiMo-V2.6-Flash | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 658.13 us | 151.9 tok/s | 1,519.4 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/b200_sxm-x231-nvl72-hybrid | MiMo-V2.6-Flash | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 99 | 239.57 us | 417.4 tok/s | 4,174.2 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x231-expert | MiMo-V2.6-Flash | 231 | expert | nvlink5 | infiniband_ndr | 192 | 425.91 us | 234.8 tok/s | 2,347.9 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.48 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.42 us |
| MiMo-V2.6-Flash/b200_sxm-x231-nvl72-expert | MiMo-V2.6-Flash | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 426.69 us | 234.4 tok/s | 2,343.6 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 231.26 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.42 us |
| MiMo-V2.6-Flash/b200_sxm-x347-pipeline | MiMo-V2.6-Flash | 347 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x347-tensor | MiMo-V2.6-Flash | 347 | tensor | nvlink5 | infiniband_ndr | 192 | 668.57 us | 149.6 tok/s | 1,495.7 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 435.87 us |
| MiMo-V2.6-Flash/b200_sxm-x347-hybrid | MiMo-V2.6-Flash | 347 | hybrid | nvlink5 | infiniband_ndr | 139 | 327.03 us | 305.8 tok/s | 3,057.8 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 94.34 us |
| MiMo-V2.6-Flash/b200_sxm-x347-nvl72-tensor | MiMo-V2.6-Flash | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 660.49 us | 151.4 tok/s | 1,514.0 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 427.51 us |
| MiMo-V2.6-Flash/b200_sxm-x347-nvl72-hybrid | MiMo-V2.6-Flash | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 100 | 241.76 us | 413.6 tok/s | 4,136.3 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| MiMo-V2.6-Flash/b200_sxm-x347-expert | MiMo-V2.6-Flash | 347 | expert | nvlink5 | infiniband_ndr | 192 | 425.70 us | 234.9 tok/s | 2,349.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.45 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.24 us |
| MiMo-V2.6-Flash/b200_sxm-x347-nvl72-expert | MiMo-V2.6-Flash | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 426.29 us | 234.6 tok/s | 2,345.8 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 231.05 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.24 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Flash | 1 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x48 | 39,120 | 19,379.3 | 0.495 | 19,379.3 (39,120) | 4,880.0 (46,225) | 0.25x | compute |
| MiMo-V2.6-Flash | 2 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x48 | 39,120 | 19,379.3 | 0.495 | 19,379.3 (39,120) | 4,953.1 (92,450) | 0.26x | compute |
| MiMo-V2.6-Flash | 4 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x48 | 39,120 | 19,379.3 | 0.495 | 19,379.3 (39,120) | 4,806.4 (92,450) | 0.25x | compute |
| MiMo-V2.6-Flash | 8 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x48 | 39,120 | 19,379.3 | 0.495 | 19,379.3 (39,120) | 4,711.1 (138,675) | 0.24x | compute |
| MiMo-V2.6-Flash | 16 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x57-romfill | 46,455 | 18,612.7 | 0.401 | 18,612.7 (46,455) | 4,704.2 (277,350) | 0.25x | weight_read |
| MiMo-V2.6-Flash | 32 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill | 92,095 | 18,254.9 | 0.198 | 18,254.9 (92,095) | 4,524.7 (369,800) | 0.25x | weight_read |
| MiMo-V2.6-Flash | 64 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill | 185,005 | 17,784.5 | 0.096 | 17,784.5 (185,005) | 4,354.2 (554,700) | 0.24x | weight_read |
| MiMo-V2.6-Flash | 256 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 8,310.1 | 0.030 | 8,310.1 (277,100) | 3,044.6 (554,700) | 0.37x | compute |
| MiMo-V2.6-Flash | 1024 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 2,402.2 | 0.009 | 2,402.2 (277,100) | 1,844.0 (554,700) | 0.77x | compute |
| MiMo-V2.6-Flash | 4096 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 614.1 | 0.002 | 614.1 (277,100) | 471.9 (554,700) | 0.77x | compute |

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
| MiMo-V2.6-Flash | 256 | 628.4 MB | 107.2 mm2 | 19.29 mm2 (18.0%) | 27,440 mm2 | 4,939 mm2 | 29,498 mm2 = 36.2 reticles |

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
| MiMo-V2.6-Flash | 1 | sram | 353,266.8 | 28,769.9 | 28,769.9 | 12.28x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 2 | sram | 353,266.8 | 28,769.9 | 28,769.9 | 12.28x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 4 | sram | 353,266.8 | 28,769.9 | 36,943.8 | 12.28x | 1.28x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 8 | sram | 353,266.8 | 28,769.9 | 59,375.2 | 12.28x | 2.06x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 16 | sram | 353,266.8 | 28,769.9 | 88,007.5 | 12.28x | 3.06x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 32 | sram | 423,164.6 | 28,769.9 | 124,506.2 | 14.71x | 4.33x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 64 | sram | 513,317.0 | 28,796.5 | 165,254.4 | 17.83x | 5.74x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 256 | sram | 842,560.0 | 28,959.8 | 329,493.2 | 29.09x | 11.38x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 1024 | sram | 1,415,129.7 | 26,104.0 | 305,672.1 | 54.21x | 11.71x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 4096 | sram | 2,064,253.4 | 26,110.4 | 319,680.9 | 79.06x | 12.24x | weight_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 1 | rom | 2,165,803.3 | 200,404.2 | 200,404.2 | 10.81x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 2 | rom | 2,165,803.3 | 200,404.2 | 200,404.2 | 10.81x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 4 | rom | 2,165,803.3 | 200,404.2 | 200,404.2 | 10.81x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 8 | rom | 2,165,803.3 | 200,404.2 | 200,404.2 | 10.81x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 16 | rom | 2,165,803.3 | 200,404.2 | 200,404.2 | 10.81x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 32 | rom | 2,165,803.3 | 200,404.2 | 200,404.2 | 10.81x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 64 | rom | 2,165,803.3 | 200,404.2 | 200,404.2 | 10.81x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 256 | rom | 2,165,803.3 | 203,723.3 | 317,977.8 | 10.63x | 1.56x | weight_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 1024 | rom | 2,459,822.3 | 205,775.3 | 323,005.3 | 11.95x | 1.57x | compute | weight_read | kv_read |
| MiMo-V2.6-Flash | 4096 | rom | 2,515,536.2 | 206,294.8 | 324,287.2 | 12.19x | 1.57x | compute | weight_read | kv_read |

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
| MiMo-V2.6-Flash | 1 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 353,266.8 | 0.637 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 1 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.60 | 1.00 | 2,165,803.3 | 7.816 | weight_read | 6.13x |
| MiMo-V2.6-Flash | 1 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 1 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.57x |
| MiMo-V2.6-Flash | 1 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 1 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.57x |
| MiMo-V2.6-Flash | 2 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 353,266.8 | 0.637 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 2 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.60 | 1.00 | 2,165,803.3 | 7.816 | weight_read | 6.13x |
| MiMo-V2.6-Flash | 2 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 2 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.57x |
| MiMo-V2.6-Flash | 2 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 2 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.57x |
| MiMo-V2.6-Flash | 4 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 353,266.8 | 0.637 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 4 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.60 | 1.00 | 2,165,803.3 | 7.816 | weight_read | 6.13x |
| MiMo-V2.6-Flash | 4 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 4 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.57x |
| MiMo-V2.6-Flash | 4 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x15-perregion | 12,225 | 1.00 | 1.79 | 36,943.8 | 3.022 | weight_read | 0.10x |
| MiMo-V2.6-Flash | 4 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.57x |
| MiMo-V2.6-Flash | 8 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 353,266.8 | 0.637 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 8 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.60 | 1.00 | 2,165,803.3 | 7.816 | weight_read | 6.13x |
| MiMo-V2.6-Flash | 8 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 8 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.57x |
| MiMo-V2.6-Flash | 8 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x15-perregion | 12,225 | 1.00 | 2.34 | 59,375.2 | 4.857 | weight_read | 0.17x |
| MiMo-V2.6-Flash | 8 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.57x |
| MiMo-V2.6-Flash | 16 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 353,266.8 | 0.637 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 16 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.60 | 1.00 | 2,165,803.3 | 7.816 | weight_read | 6.13x |
| MiMo-V2.6-Flash | 16 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 16 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.57x |
| MiMo-V2.6-Flash | 16 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x16-perregion | 13,040 | 1.00 | 3.27 | 88,007.5 | 6.749 | weight_read | 0.25x |
| MiMo-V2.6-Flash | 16 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.57x |
| MiMo-V2.6-Flash | 32 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x60 | 48,900 | 1.00 | 1.00 | 423,164.6 | 8.654 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 32 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.60 | 1.00 | 2,165,803.3 | 7.816 | weight_read | 5.12x |
| MiMo-V2.6-Flash | 32 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.07x |
| MiMo-V2.6-Flash | 32 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.47x |
| MiMo-V2.6-Flash | 32 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x16-perregion | 13,040 | 1.00 | 4.64 | 124,506.2 | 9.548 | weight_read | 0.29x |
| MiMo-V2.6-Flash | 32 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.47x |
| MiMo-V2.6-Flash | 64 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x90 | 73,350 | 1.00 | 1.00 | 513,317.0 | 6.998 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 64 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.60 | 1.00 | 2,165,803.3 | 7.816 | weight_read | 4.22x |
| MiMo-V2.6-Flash | 64 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,796.5 | 0.623 | weight_read | 0.06x |
| MiMo-V2.6-Flash | 64 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.39x |
| MiMo-V2.6-Flash | 64 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x16-perregion | 13,040 | 1.00 | 6.85 | 165,254.4 | 12.673 | weight_read | 0.32x |
| MiMo-V2.6-Flash | 64 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 200,404.2 | 2.168 | weight_read | 0.39x |
| MiMo-V2.6-Flash | 256 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x90 | 73,350 | 1.00 | 1.00 | 842,560.0 | 11.487 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 256 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.60 | 1.00 | 2,165,803.3 | 7.816 | weight_read | 2.57x |
| MiMo-V2.6-Flash | 256 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,959.8 | 0.626 | weight_read | 0.03x |
| MiMo-V2.6-Flash | 256 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 2.25 | 203,723.3 | 2.204 | weight_read | 0.24x |
| MiMo-V2.6-Flash | 256 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 16.87 | 329,493.2 | 7.128 | weight_read | 0.39x |
| MiMo-V2.6-Flash | 256 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.30 | 317,977.8 | 3.439 | kv_read | 0.38x |
| MiMo-V2.6-Flash | 1024 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 1,415,129.7 | 2.551 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1024 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.60 | 1.00 | 2,459,822.3 | 8.877 | compute | 1.74x |
| MiMo-V2.6-Flash | 1024 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x16-perstream | 13,040 | 1.00 | 64.00 | 26,104.0 | 2.002 | weight_read | 0.02x |
| MiMo-V2.6-Flash | 1024 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 8.98 | 205,775.3 | 2.226 | weight_read | 0.15x |
| MiMo-V2.6-Flash | 1024 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 28.16 | 305,672.1 | 3.306 | kv_read | 0.22x |
| MiMo-V2.6-Flash | 1024 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 2.46 | 323,005.3 | 3.494 | kv_read | 0.23x |
| MiMo-V2.6-Flash | 4096 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 1.00 | 1.00 | 2,064,253.4 | 11.158 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 4096 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.60 | 1.00 | 2,515,536.2 | 9.078 | compute | 1.22x |
| MiMo-V2.6-Flash | 4096 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 35.93 | 26,110.4 | 0.282 | weight_read | 0.01x |
| MiMo-V2.6-Flash | 4096 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 35.93 | 206,294.8 | 2.231 | weight_read | 0.10x |
| MiMo-V2.6-Flash | 4096 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 87.33 | 319,680.9 | 3.458 | kv_read | 0.15x |
| MiMo-V2.6-Flash | 4096 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 4.94 | 324,287.2 | 3.508 | kv_read | 0.16x |

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
| MiMo-V2.6-Flash | 1 | 15 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 2 | 15 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 4 | 15 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 8 | 15 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 64 | 57 | 1.12 | 1.002 | 1.027 | 1.02x |
| MiMo-V2.6-Flash | 256 | 57 | 4.49 | 1.056 | 1.885 | 1.78x |
| MiMo-V2.6-Flash | 1024 | 16 | 64.00 | 2.302 | 6.846 | 2.97x |
| MiMo-V2.6-Flash | 4096 | 16 | 256.00 | 8.002 | 16.866 | 2.11x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Flash | 1 | 7 | 4.96 | 3.12 | 1.59x |
| MiMo-V2.6-Flash | 2 | 7 | 6.38 | 3.73 | 1.71x |
| MiMo-V2.6-Flash | 4 | 7 | 6.94 | 4.31 | 1.61x |
| MiMo-V2.6-Flash | 8 | 7 | 7.00 | 4.82 | 1.45x |
| MiMo-V2.6-Flash | 16 | 7 | 7.00 | 5.24 | 1.34x |
| MiMo-V2.6-Flash | 32 | 7 | 7.00 | 5.53 | 1.26x |
| MiMo-V2.6-Flash | 64 | 7 | 7.00 | 5.71 | 1.23x |
| MiMo-V2.6-Flash | 256 | 7 | 7.00 | 5.78 | 1.21x |
| MiMo-V2.6-Flash | 1024 | 7 | 7.00 | 5.78 | 1.21x |
| MiMo-V2.6-Flash | 4096 | 7 | 7.00 | 5.78 | 1.21x |
| MiMo-V2.6-Flash | 1 | 8 | 5.25 | 3.28 | 1.60x |
| MiMo-V2.6-Flash | 2 | 8 | 7.02 | 3.98 | 1.77x |
| MiMo-V2.6-Flash | 4 | 8 | 7.86 | 4.66 | 1.69x |
| MiMo-V2.6-Flash | 8 | 8 | 8.00 | 5.27 | 1.52x |
| MiMo-V2.6-Flash | 16 | 8 | 8.00 | 5.78 | 1.38x |
| MiMo-V2.6-Flash | 32 | 8 | 8.00 | 6.14 | 1.30x |
| MiMo-V2.6-Flash | 64 | 8 | 8.00 | 6.36 | 1.26x |
| MiMo-V2.6-Flash | 256 | 8 | 8.00 | 6.45 | 1.24x |
| MiMo-V2.6-Flash | 1024 | 8 | 8.00 | 6.45 | 1.24x |
| MiMo-V2.6-Flash | 4096 | 8 | 8.00 | 6.45 | 1.24x |
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
| MiMo-V2.6-Flash | 1 | 16 | 6.45 | 4.14 | 1.56x |
| MiMo-V2.6-Flash | 2 | 16 | 10.21 | 5.38 | 1.90x |
| MiMo-V2.6-Flash | 4 | 16 | 13.77 | 6.72 | 2.05x |
| MiMo-V2.6-Flash | 8 | 16 | 15.61 | 8.07 | 1.93x |
| MiMo-V2.6-Flash | 16 | 16 | 15.98 | 9.28 | 1.72x |
| MiMo-V2.6-Flash | 32 | 16 | 16.00 | 10.22 | 1.57x |
| MiMo-V2.6-Flash | 64 | 16 | 16.00 | 10.80 | 1.48x |
| MiMo-V2.6-Flash | 256 | 16 | 16.00 | 11.05 | 1.45x |
| MiMo-V2.6-Flash | 1024 | 16 | 16.00 | 11.05 | 1.45x |
| MiMo-V2.6-Flash | 4096 | 16 | 16.00 | 11.05 | 1.45x |
| MiMo-V2.6-Flash | 1 | 17 | 6.53 | 4.22 | 1.55x |
| MiMo-V2.6-Flash | 2 | 17 | 10.46 | 5.50 | 1.90x |
| MiMo-V2.6-Flash | 4 | 17 | 14.33 | 6.92 | 2.07x |
| MiMo-V2.6-Flash | 8 | 17 | 16.48 | 8.35 | 1.97x |
| MiMo-V2.6-Flash | 16 | 17 | 16.96 | 9.64 | 1.76x |
| MiMo-V2.6-Flash | 32 | 17 | 17.00 | 10.65 | 1.60x |
| MiMo-V2.6-Flash | 64 | 17 | 17.00 | 11.28 | 1.51x |
| MiMo-V2.6-Flash | 256 | 17 | 17.00 | 11.56 | 1.47x |
| MiMo-V2.6-Flash | 1024 | 17 | 17.00 | 11.56 | 1.47x |
| MiMo-V2.6-Flash | 4096 | 17 | 17.00 | 11.56 | 1.47x |
| MiMo-V2.6-Flash | 1 | 18 | 6.61 | 4.29 | 1.54x |
| MiMo-V2.6-Flash | 2 | 18 | 10.68 | 5.62 | 1.90x |
| MiMo-V2.6-Flash | 4 | 18 | 14.86 | 7.11 | 2.09x |
| MiMo-V2.6-Flash | 8 | 18 | 17.32 | 8.62 | 2.01x |
| MiMo-V2.6-Flash | 16 | 18 | 17.95 | 9.99 | 1.80x |
| MiMo-V2.6-Flash | 32 | 18 | 18.00 | 11.08 | 1.62x |
| MiMo-V2.6-Flash | 64 | 18 | 18.00 | 11.76 | 1.53x |
| MiMo-V2.6-Flash | 256 | 18 | 18.00 | 12.05 | 1.49x |
| MiMo-V2.6-Flash | 1024 | 18 | 18.00 | 12.05 | 1.49x |
| MiMo-V2.6-Flash | 4096 | 18 | 18.00 | 12.05 | 1.49x |
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
| MiMo-V2.6-Flash | 1 | 23 | 6.88 | 4.60 | 1.50x |
| MiMo-V2.6-Flash | 2 | 23 | 11.58 | 6.14 | 1.88x |
| MiMo-V2.6-Flash | 4 | 23 | 17.08 | 7.94 | 2.15x |
| MiMo-V2.6-Flash | 8 | 23 | 21.21 | 9.82 | 2.16x |
| MiMo-V2.6-Flash | 16 | 23 | 22.75 | 11.60 | 1.96x |
| MiMo-V2.6-Flash | 32 | 23 | 22.98 | 13.04 | 1.76x |
| MiMo-V2.6-Flash | 64 | 23 | 23.00 | 13.95 | 1.65x |
| MiMo-V2.6-Flash | 256 | 23 | 23.00 | 14.35 | 1.60x |
| MiMo-V2.6-Flash | 1024 | 23 | 23.00 | 14.35 | 1.60x |
| MiMo-V2.6-Flash | 4096 | 23 | 23.00 | 14.35 | 1.60x |
| MiMo-V2.6-Flash | 1 | 24 | 6.93 | 4.65 | 1.49x |
| MiMo-V2.6-Flash | 2 | 24 | 11.72 | 6.23 | 1.88x |
| MiMo-V2.6-Flash | 4 | 24 | 17.46 | 8.08 | 2.16x |
| MiMo-V2.6-Flash | 8 | 24 | 21.92 | 10.04 | 2.18x |
| MiMo-V2.6-Flash | 16 | 24 | 23.69 | 11.89 | 1.99x |
| MiMo-V2.6-Flash | 32 | 24 | 23.98 | 13.40 | 1.79x |
| MiMo-V2.6-Flash | 64 | 24 | 24.00 | 14.36 | 1.67x |
| MiMo-V2.6-Flash | 256 | 24 | 24.00 | 14.79 | 1.62x |
| MiMo-V2.6-Flash | 1024 | 24 | 24.00 | 14.79 | 1.62x |
| MiMo-V2.6-Flash | 4096 | 24 | 24.00 | 14.79 | 1.62x |
| MiMo-V2.6-Flash | 1 | 25 | 6.97 | 4.71 | 1.48x |
| MiMo-V2.6-Flash | 2 | 25 | 11.86 | 6.32 | 1.88x |
| MiMo-V2.6-Flash | 4 | 25 | 17.81 | 8.22 | 2.17x |
| MiMo-V2.6-Flash | 8 | 25 | 22.60 | 10.25 | 2.21x |
| MiMo-V2.6-Flash | 16 | 25 | 24.61 | 12.18 | 2.02x |
| MiMo-V2.6-Flash | 32 | 25 | 24.97 | 13.75 | 1.82x |
| MiMo-V2.6-Flash | 64 | 25 | 25.00 | 14.76 | 1.69x |
| MiMo-V2.6-Flash | 256 | 25 | 25.00 | 15.21 | 1.64x |
| MiMo-V2.6-Flash | 1024 | 25 | 25.00 | 15.21 | 1.64x |
| MiMo-V2.6-Flash | 4096 | 25 | 25.00 | 15.21 | 1.64x |
| MiMo-V2.6-Flash | 1 | 29 | 7.10 | 4.90 | 1.45x |
| MiMo-V2.6-Flash | 2 | 29 | 12.31 | 6.63 | 1.86x |
| MiMo-V2.6-Flash | 4 | 29 | 19.07 | 8.74 | 2.18x |
| MiMo-V2.6-Flash | 8 | 29 | 25.13 | 11.03 | 2.28x |
| MiMo-V2.6-Flash | 16 | 29 | 28.19 | 13.25 | 2.13x |
| MiMo-V2.6-Flash | 32 | 29 | 28.91 | 15.10 | 1.91x |
| MiMo-V2.6-Flash | 64 | 29 | 28.99 | 16.29 | 1.78x |
| MiMo-V2.6-Flash | 256 | 29 | 29.00 | 16.82 | 1.72x |
| MiMo-V2.6-Flash | 1024 | 29 | 29.00 | 16.82 | 1.72x |
| MiMo-V2.6-Flash | 4096 | 29 | 29.00 | 16.82 | 1.72x |
| MiMo-V2.6-Flash | 1 | 31 | 7.15 | 4.99 | 1.43x |
| MiMo-V2.6-Flash | 2 | 31 | 12.50 | 6.77 | 1.85x |
| MiMo-V2.6-Flash | 4 | 31 | 19.61 | 8.98 | 2.18x |
| MiMo-V2.6-Flash | 8 | 31 | 26.28 | 11.39 | 2.31x |
| MiMo-V2.6-Flash | 16 | 31 | 29.91 | 13.75 | 2.17x |
| MiMo-V2.6-Flash | 32 | 31 | 30.85 | 15.73 | 1.96x |
| MiMo-V2.6-Flash | 64 | 31 | 30.98 | 17.01 | 1.82x |
| MiMo-V2.6-Flash | 256 | 31 | 30.99 | 17.59 | 1.76x |
| MiMo-V2.6-Flash | 1024 | 31 | 30.99 | 17.59 | 1.76x |
| MiMo-V2.6-Flash | 4096 | 31 | 30.99 | 17.59 | 1.76x |
| MiMo-V2.6-Flash | 1 | 43 | 7.38 | 5.41 | 1.36x |
| MiMo-V2.6-Flash | 2 | 43 | 13.32 | 7.44 | 1.79x |
| MiMo-V2.6-Flash | 4 | 43 | 22.04 | 10.17 | 2.17x |
| MiMo-V2.6-Flash | 8 | 43 | 31.87 | 13.24 | 2.41x |
| MiMo-V2.6-Flash | 16 | 43 | 39.10 | 16.36 | 2.39x |
| MiMo-V2.6-Flash | 32 | 43 | 42.08 | 19.07 | 2.21x |
| MiMo-V2.6-Flash | 64 | 43 | 42.77 | 20.88 | 2.05x |
| MiMo-V2.6-Flash | 256 | 43 | 42.90 | 21.70 | 1.98x |
| MiMo-V2.6-Flash | 1024 | 43 | 42.90 | 21.70 | 1.98x |
| MiMo-V2.6-Flash | 4096 | 43 | 42.90 | 21.70 | 1.98x |
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
| MiMo-V2.6-Flash | 1 | 57 | 7.53 | 5.78 | 1.30x |
| MiMo-V2.6-Flash | 2 | 57 | 13.87 | 8.01 | 1.73x |
| MiMo-V2.6-Flash | 4 | 57 | 23.80 | 11.24 | 2.12x |
| MiMo-V2.6-Flash | 8 | 57 | 36.37 | 14.91 | 2.44x |
| MiMo-V2.6-Flash | 16 | 57 | 47.62 | 18.79 | 2.53x |
| MiMo-V2.6-Flash | 32 | 57 | 53.83 | 22.27 | 2.42x |
| MiMo-V2.6-Flash | 64 | 57 | 55.89 | 24.64 | 2.27x |
| MiMo-V2.6-Flash | 256 | 57 | 56.39 | 25.73 | 2.19x |
| MiMo-V2.6-Flash | 1024 | 57 | 56.39 | 25.73 | 2.19x |
| MiMo-V2.6-Flash | 4096 | 57 | 56.39 | 25.73 | 2.19x |
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
| MiMo-V2.6-Flash | 1 | 61 | 7.56 | 5.86 | 1.29x |
| MiMo-V2.6-Flash | 2 | 61 | 13.98 | 8.15 | 1.71x |
| MiMo-V2.6-Flash | 4 | 61 | 24.17 | 11.49 | 2.10x |
| MiMo-V2.6-Flash | 8 | 61 | 37.39 | 15.32 | 2.44x |
| MiMo-V2.6-Flash | 16 | 61 | 49.69 | 19.40 | 2.56x |
| MiMo-V2.6-Flash | 32 | 61 | 56.90 | 23.08 | 2.47x |
| MiMo-V2.6-Flash | 64 | 61 | 59.46 | 25.60 | 2.32x |
| MiMo-V2.6-Flash | 256 | 61 | 60.11 | 26.76 | 2.25x |
| MiMo-V2.6-Flash | 1024 | 61 | 60.11 | 26.76 | 2.25x |
| MiMo-V2.6-Flash | 4096 | 61 | 60.11 | 26.76 | 2.25x |
| MiMo-V2.6-Flash | 1 | 87 | 7.69 | 6.29 | 1.22x |
| MiMo-V2.6-Flash | 2 | 87 | 14.48 | 8.92 | 1.62x |
| MiMo-V2.6-Flash | 4 | 87 | 25.87 | 12.81 | 2.02x |
| MiMo-V2.6-Flash | 8 | 87 | 42.21 | 17.47 | 2.42x |
| MiMo-V2.6-Flash | 16 | 87 | 60.23 | 22.70 | 2.65x |
| MiMo-V2.6-Flash | 32 | 87 | 73.83 | 27.56 | 2.68x |
| MiMo-V2.6-Flash | 64 | 87 | 80.35 | 30.98 | 2.59x |
| MiMo-V2.6-Flash | 256 | 87 | 82.49 | 32.58 | 2.53x |
| MiMo-V2.6-Flash | 1024 | 87 | 82.49 | 32.58 | 2.53x |
| MiMo-V2.6-Flash | 4096 | 87 | 82.49 | 32.58 | 2.53x |
| MiMo-V2.6-Flash | 1 | 116 | 7.76 | 6.60 | 1.18x |
| MiMo-V2.6-Flash | 2 | 116 | 14.79 | 9.59 | 1.54x |
| MiMo-V2.6-Flash | 4 | 116 | 26.95 | 13.78 | 1.96x |
| MiMo-V2.6-Flash | 8 | 116 | 45.44 | 19.29 | 2.36x |
| MiMo-V2.6-Flash | 16 | 116 | 68.02 | 25.53 | 2.66x |
| MiMo-V2.6-Flash | 32 | 116 | 87.79 | 31.47 | 2.79x |
| MiMo-V2.6-Flash | 64 | 116 | 99.09 | 35.74 | 2.77x |
| MiMo-V2.6-Flash | 256 | 116 | 103.35 | 37.76 | 2.74x |
| MiMo-V2.6-Flash | 1024 | 116 | 103.36 | 37.77 | 2.74x |
| MiMo-V2.6-Flash | 4096 | 116 | 103.36 | 37.77 | 2.74x |
| MiMo-V2.6-Flash | 1 | 173 | 7.84 | 6.97 | 1.12x |
| MiMo-V2.6-Flash | 2 | 173 | 15.10 | 10.58 | 1.43x |
| MiMo-V2.6-Flash | 4 | 173 | 28.06 | 15.05 | 1.87x |
| MiMo-V2.6-Flash | 8 | 173 | 48.98 | 22.00 | 2.23x |
| MiMo-V2.6-Flash | 16 | 173 | 77.21 | 29.58 | 2.61x |
| MiMo-V2.6-Flash | 32 | 173 | 105.88 | 37.19 | 2.85x |
| MiMo-V2.6-Flash | 64 | 173 | 125.36 | 42.87 | 2.92x |
| MiMo-V2.6-Flash | 256 | 173 | 133.76 | 45.58 | 2.93x |
| MiMo-V2.6-Flash | 1024 | 173 | 133.78 | 45.59 | 2.93x |
| MiMo-V2.6-Flash | 4096 | 173 | 133.78 | 45.59 | 2.93x |
| MiMo-V2.6-Flash | 1 | 231 | 7.88 | 7.19 | 1.10x |
| MiMo-V2.6-Flash | 2 | 231 | 15.26 | 11.30 | 1.35x |
| MiMo-V2.6-Flash | 4 | 231 | 28.66 | 16.00 | 1.79x |
| MiMo-V2.6-Flash | 8 | 231 | 50.94 | 23.91 | 2.13x |
| MiMo-V2.6-Flash | 16 | 231 | 82.58 | 32.43 | 2.55x |
| MiMo-V2.6-Flash | 32 | 231 | 117.26 | 41.58 | 2.82x |
| MiMo-V2.6-Flash | 64 | 231 | 143.00 | 48.35 | 2.96x |
| MiMo-V2.6-Flash | 256 | 231 | 154.89 | 51.66 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 231 | 154.92 | 51.66 | 3.00x |
| MiMo-V2.6-Flash | 4096 | 231 | 154.92 | 51.66 | 3.00x |
| MiMo-V2.6-Flash | 1 | 347 | 7.92 | 7.43 | 1.07x |
| MiMo-V2.6-Flash | 2 | 347 | 15.42 | 12.28 | 1.26x |
| MiMo-V2.6-Flash | 4 | 347 | 29.27 | 17.53 | 1.67x |
| MiMo-V2.6-Flash | 8 | 347 | 52.99 | 26.19 | 2.02x |
| MiMo-V2.6-Flash | 16 | 347 | 88.46 | 36.85 | 2.40x |
| MiMo-V2.6-Flash | 32 | 347 | 130.41 | 47.91 | 2.72x |
| MiMo-V2.6-Flash | 64 | 347 | 164.39 | 56.35 | 2.92x |
| MiMo-V2.6-Flash | 256 | 347 | 181.21 | 60.46 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 347 | 181.25 | 60.47 | 3.00x |
| MiMo-V2.6-Flash | 4096 | 347 | 181.25 | 60.47 | 3.00x |

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
| gpu | MiMo-V2.6-Flash | 1 | 10.83 | 3.9% |
| rom | MiMo-V2.6-Flash | 1 | 10.83 | 21.3% |

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
| MiMo-V2.6-Flash | 1 | 15 | 12.32% | 17.16 | 9.28 |
| MiMo-V2.6-Flash | 2 | 15 | 12.32% | 17.16 | 9.28 |
| MiMo-V2.6-Flash | 4 | 15 | 12.32% | 17.16 | 9.28 |
| MiMo-V2.6-Flash | 8 | 15 | 12.32% | 17.16 | 9.28 |
| MiMo-V2.6-Flash | 16 | 1 | 0.25% | 1.32 | 9.28 |
| MiMo-V2.6-Flash | 32 | 1 | 0.25% | 1.32 | 9.28 |
| MiMo-V2.6-Flash | 64 | 1 | 0.28% | 1.48 | 9.28 |
| MiMo-V2.6-Flash | 256 | 1 | 1.12% | 5.93 | 9.28 |

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
| MiMo-V2.6-Flash | 1 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 1,674.1 | 55,245.4 |
| MiMo-V2.6-Flash | 2 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 1,674.1 | 55,245.4 |
| MiMo-V2.6-Flash | 4 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 1,674.1 | 55,245.4 |
| MiMo-V2.6-Flash | 8 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 1,674.1 | 55,245.4 |
| MiMo-V2.6-Flash | 16 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 1,674.1 | 55,245.4 |
| MiMo-V2.6-Flash | 32 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 1,674.1 | 55,245.4 |
| MiMo-V2.6-Flash | 64 | 5.97% | 17.3 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 871.6 | 55,782.5 |
| MiMo-V2.6-Flash | 256 | 21.83% | 42.8 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 219.6 | 56,218.8 |
| MiMo-V2.6-Flash | 1024 | 62.66% | 108.4 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 55.0 | 56,329.0 |
| MiMo-V2.6-Flash | 4096 | 98.06% | 165.4 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 13.8 | 56,356.6 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | kv_read | 28 |
| gpu | link_latency | 753 |
| gpu | thermal | 240 |
| gpu | weight_read | 449 |
| rom | compute | 740 |
| rom | infeasible | 2096 |
| rom | kv_read | 244 |
| rom | link_latency | 1188 |
| rom | thermal | 18 |
| rom | weight_read | 754 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2096 |

## Mechanical consistency audit

**FAIL** over 139,513 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x30', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x32', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x33', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x35', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x42', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x56', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x84', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x112', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x30', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x32', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x33', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x35', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x42', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x56', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x84', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x112', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x30', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x32', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x33', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x35', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x42', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x56', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x84', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x112', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x30', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x32', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x33', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x35', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x42', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x56', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x84', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x112', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x170', 'MiMo-V2.6-Flash', 1)

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

# Area-constrained roofline: n5_vs_b200-flash-1m

> CONTEXT-LADDER RUNG of n5_vs_b200: DeepSeek-V4-Flash-0731 at 1,000,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 467x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 1 device. On the GPU side the correction reaches 204x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 58 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Flash-0731 takes 1 x 46,225 mm2 (46,225 mm2, wafer, KV in SRAM) at 4,825 tok/s per user and 104 tok/s per 1,000 mm2, holding 1 session, against 29 copies of one unified HBM die at the same silicon: 3.7x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Flash-0731 on 46,225 mm2 of ROM silicon at 4,825 tok/s per user against 46,400 mm2 of b200_sxm-x29-tensor at 1,290 tok/s: **3.7x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 658. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 47.35x to it.** At 554,700 mm2 on DeepSeek-V4-Flash-0731 the pipeline-only GPU delivers 29.84 tok/s and the same silicon running tensor delivers 1,413 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.44x (DeepSeek-V4-Flash-0731, ROM binding on `compute`) to 8.24x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 19.1% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 631 to 22,137 tok/s, and its rate with every slot occupied from 21,467 to 22,137. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 34 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 599 us over NVLink, capping per-user decode at 1,670 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 1,034.9 us and cap it at 966 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 7 of 8 operating points and an array 1; on tokens per second per square millimetre the same points go 7 to the array and 1 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 95 of 1810 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 8.4x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 4.73x, on DeepSeek-V4-Flash-0731 at batch 256, where the busiest region carries 2.99x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 14 of 16 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 8 of 1,810 feasible points (0.4%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x87` at batch 256 on 70,905 mm2, throttled 1.14x from 699 to 616 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 96% kv read against 0.1% weight read. The ROM sweep is not what melts it.


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

### DeepSeek-V4-Flash-0731 at 1,000,000 tokens

**Recommended: `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill`** -- 1 x 46,225 mm2 wafer, 46,225 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `rom`.

- **4,824.6 tok/s per user** (0.21 ms/token), binding on `link_latency`
- **104.4 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,825 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 3,914 W at 0.085 W/mm2, 811.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 29 copies of one unified HBM die -- `b200_sxm-x29-tensor`, 46,400 mm2, area ratio 0.9962 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 46,225 | 46,400 | 0.9962 |
| user tok/s | 4,824.6 | 1,290.0 | 3.74x |
| aggregate tok/s | 4,825 | 1,290 | 3.74x |
| resident sessions | 1 | 658 | -- |
| J/token | 0.8113 | 9.2229 | 11.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 658 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x347-tensor` at 555,200 mm2 and 1,413.1 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,824.6 | 104.4 | 1 | 3.74x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,824.6 | 104.4 | 1 | 3.74x |
| smallest feasible machine | `ROM-N5-native-HBMKV-array-hybrid-x34` | 27,710 | 2,201.3 | 79.4 | 499 | 1.81x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,824.6 | 104.4 | 1 | 3.74x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` **<-- recommended** | 46,225 | 1 | 4,824.6 | 4,825 | 104.4 | 1 | `link_latency` | 3,914 | 811.3 | `b200_sxm-x29-tensor` | 3.74x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 144 | densest | `ROM-N5-native-SRAMKV-array-hybrid-x35` | 28,525 | 2,374.7 | 83.3 | 1 |
| array | 144 | fastest | `ROM-N5-native-HBMKV-array-hybrid-x37` | 30,155 | 2,374.7 | 78.8 | 544 |
| array | 144 | smallest | `ROM-N5-native-HBMKV-array-hybrid-x34` | 27,710 | 2,201.3 | 79.4 | 499 |
| wafer | 70 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,824.6 | 104.4 | 1 |
| wafer | 70 | fastest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,824.6 | 104.4 | 1 |
| wafer | 70 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,824.6 | 104.4 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hybrid-x37` | 30,155 | 2,374.7 | 11,874 | 544 | 4,659 | 392.4 | `link_latency` | `b200_sxm-x19-tensor` | 1,232.8 | 422 | 6,745.7 | 0.992 | 1.93x | 17.2x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,824.6 | 4,825 | 1 | 3,914 | 811.3 | `link_latency` | `b200_sxm-x29-tensor` | 1,290.0 | 658 | 9,222.9 | 0.996 | 3.74x | 11.4x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hybrid-x57-romfill` | 46,455 | 2,018.0 | 2,018 | 1 | 3,897 | 1,931.2 | `weight_read` | `b200_sxm-x29-tensor` | 1,290.0 | 658 | 9,222.9 | 1.001 | 1.56x | 4.8x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,824.6 | -- | 1 | -- | 811.3 | -- | -- | -- | -- | -- | 1.005 | 2.39x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hybrid-x37` | 30,155 | 2,374.7 | 11,874 | 544 | 4,659 | 392.4 | `link_latency` | `b200_sxm-x19-hybrid` | 1,157.2 | 422 | 3,262.7 | 0.992 | 2.05x | 8.3x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 4,315.7 | 12,947 | 379 | 14,483 | 1,118.7 | `link_latency` | `b200_sxm-x87-tensor` | 1,244.9 | 2,022 | 13,177.9 | 0.996 | 3.47x | 11.8x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 138,550 | 1,948.2 | 42,859 | 2,499 | 22,060 | 514.7 | `link_latency` | `b200_sxm-x87-tensor` | 1,244.9 | 2,022 | 13,177.9 | 0.995 | 1.56x | 25.6x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 4,315.7 | -- | 379 | -- | 1,118.7 | -- | -- | -- | -- | -- | 0.999 | 2.22x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hybrid-x37` | 30,155 | 2,374.7 | 11,874 | 544 | 4,659 | 392.4 | `link_latency` | `b200_sxm-x19-hybrid` | 1,050.1 | 422 | 2,724.4 | 0.992 | 2.26x | 6.9x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,223.6 | 16,894 | 505 | 19,249 | 1,139.4 | `link_latency` | `b200_sxm-x116-tensor` | 1,077.7 | 2,704 | 10,150.1 | 0.996 | 3.92x | 8.9x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 1,902.9 | 55,185 | 3,337 | 29,112 | 527.5 | `link_latency` | `b200_sxm-x116-tensor` | 1,077.7 | 2,704 | 10,150.1 | 0.997 | 1.77x | 19.2x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,223.6 | -- | 505 | -- | 1,139.4 | -- | -- | -- | -- | -- | 1.001 | 2.22x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hybrid-x37` | 30,155 | 2,175.9 | 17,407 | 544 | 5,577 | 320.4 | `link_latency` | `b200_sxm-x19-hybrid` | 802.6 | 422 | 1,864.3 | 0.992 | 2.71x | 5.8x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 3,891.3 | 31,130 | 1,011 | 38,050 | 1,222.3 | `link_latency` | `b200_sxm-x231-tensor` | 894.5 | 5,410 | 11,914.1 | 1.001 | 4.35x | 9.7x |
| 16 | array | `ROM-N5-native-HBMKV-array-hybrid-x44` | 35,860 | 2,069.1 | 33,106 | 646 | 9,115 | 275.3 | `link_latency` | `b200_sxm-x22-hybrid` | 620.6 | 493 | 1,439.7 | 1.019 | 3.33x | 5.2x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,425.1 | 54,802 | 1,517 | 58,408 | 1,065.8 | `link_latency` | `b200_sxm-x347-tensor` | 668.3 | 8,139 | 11,894.4 | 0.999 | 5.13x | 11.2x |
| 32 | array | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 70,905 | 2,038.5 | 65,232 | 1,279 | 18,488 | 283.4 | `link_latency` | `b200_sxm-x44-hybrid` | 463.0 | 1,010 | 1,704.0 | 1.007 | 4.40x | 6.0x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,849.2 | 91,175 | 1,517 | 64,437 | 706.7 | `link_latency` | `b200_sxm-x347-tensor` | 442.3 | 8,139 | 9,039.9 | 0.999 | 6.44x | 12.8x |
| 64 | array | `ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 138,550 | 1,909.1 | 122,185 | 2,499 | 35,244 | 288.4 | `link_latency` | `b200_sxm-x87-hybrid` | 333.8 | 2,022 | 2,075.8 | 0.995 | 5.72x | 7.2x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,132.2 | 136,459 | 1,517 | 71,940 | 527.2 | `link_latency` | `b200_sxm-x347-tensor` | 268.7 | 8,139 | 7,439.1 | 0.999 | 7.94x | 14.1x |
| 256 | array | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 277,100 | 1,287.2 | 329,530 | 4,999 | 84,562 | 256.6 | `compute` | `b200_sxm-x173-hybrid` | 163.8 | 4,045 | 2,002.0 | 1.001 | 7.86x | 7.8x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 849.5 | 217,467 | 1,517 | 115,774 | 532.4 | `kv_read` | `b200_sxm-x347-hybrid` | 129.4 | 8,139 | 4,318.6 | 0.999 | 6.56x | 8.1x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | wafer | SRAM | 1 |
| 2-4 | `ROM-N5-native-HBMKV-array-hybrid-x35` | 28,525 | array | HBM | 514 |
| 8 | `ROM-N5-native-HBMKV-array-hybrid-x37` | 30,155 | array | HBM | 544 |
| 16 | `ROM-N5-native-HBMKV-array-hybrid-x44` | 35,860 | array | HBM | 646 |
| 32 | `ROM-N5-native-HBMKV-array-hybrid-x57` | 46,455 | array | HBM | 838 |
| 64 | `ROM-N5-native-HBMKV-array-hybrid-x58` | 47,270 | array | HBM | 852 |
| 256 | `ROM-N5-native-HBMKV-array-pipeline-x57` | 46,455 | array | HBM | 838 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 34, 35, 37, 44, 57, 58, 87, 113, 116, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 34, 35, 37, 44, 57, 58, 87, 113, 116, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 34, 35, 38, 45, 57, 60, 90, 113, 120, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 34, 35, 38, 45, 57, 60, 90, 113, 120, 170, 227, 340 |

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
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 0.0 tok/s | 0.00x | within 2x | FAIL |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |
| A100 80GB at its published TDP, saturating load | 400.0 W | 461.7 W | 1.15x | within 2x | PASS |
| Taalas HC1 card power at its published operating point | 200.0-250.0 W | 87.6 W | 0.35x | within 2x | FAIL |

HC1 binds on `capacity_or_format`. Its component times are weight_read 61.42 us, kv_read 9.28 us, compute 61.42 us, link_latency 0.00 us, layer_fixed_latency 6.06 us.

**THE ANCHOR IS INFEASIBLE, AND THAT IS THE RESULT.** The model does not
under-predict the shipping part here -- it cannot place it. Taalas ships
this die; this model says the die cannot hold its own weights. At least one
of the constants below is therefore wrong, and the gate exists to say so
rather than to be closed:

- AREA: the array needs 770.5 mm2 to hold 3,513,239,296 B but only 432.4 mm2 of 815 mm2 is left after SRAM, HBM PHY, overhead and interconnect

The candidates, in the order they should be attacked: `rom.cell_to_sram_cell_area_ratio` and `rom.array_efficiency`, whose
product is now set by one sentence in one paper about a foundry memory
compiler and which together cut ROM capacity density by 2.243x;
`rom.cim_precompute_area_fraction`, taken from a different fabricated part
with a different architecture; `rom.cim_cell_area_multiplier`, for which no
published compute-in-ROM cell exists at any node; and
`reference_parts.taalas_hc1.weight_bits_per_parameter`, whose 3.0-6.0 sweep
the vendor's own 3-bit base type sits at the bottom of. **Nothing here is
tuned to make this gate pass.** The back-derivation below is still printed,
because what each input would have to be is exactly the question a failing
gate asks:

| Derived input | This model | Required by the shipping part | Shortfall |
|---|---:|---:|---:|
| ROM read bandwidth density (B/s/mm2) | 1.764e+11 | 1.837e+11 | 1.04x |
| Compute density (ops/s/mm2) | 1.261e+12 | 3.155e+12 | 2.50x |

The gate fails before either rate density can bind: the corrected
ROM capacity density and compute-in-ROM floorplan cannot fit the
published model in 815 mm2. The rate diagnostics remain useful --
ROM read density is 1.04x and
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
| range low | 70.0 ns/layer | 2.24 us | 0.0 | 0.00x | capacity_or_format |
| range stated | 189.4 ns/layer | 6.06 us | 0.0 | 0.00x | capacity_or_format |
| range high | 894.8 ns/layer | 28.63 us | 0.0 | 0.00x | capacity_or_format |

The per-layer cost that would land the model exactly on the
published figure is **-76.7 ns/layer**. It is negative, which means no positive latency term could close the gate. The current result is decided earlier by the reported capacity failure.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 0.0 | 0.00x | capacity_or_format |
| 3.5 | 0.0 | 0.00x | capacity_or_format |
| 4.0 | 0.0 | 0.00x | capacity_or_format |
| 5.0 | 0.0 | 0.00x | capacity_or_format |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 0.0 | 0.00x | capacity_or_format |
| 1,536 | 0.0 | 0.00x | capacity_or_format |
| 2,048 | 0.0 | 0.00x | capacity_or_format |

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
| Taalas HC1 card power | 200.0-250.0 W | 87.6 W | 0.35x | FAIL |

**Where the watts come from.**

| Term | A100 at TDP | Taalas HC1 |
|---|---:|---:|
| memory / array traffic (weights) | 213.9 W | 3.9 W |
| KV traffic | n/a: one saturating HBM stream | 10.3 W |
| operand delivery | 0.5 W | 12.1 W |
| arithmetic | 103.0 W | 8.7 W |
| static: leakage | 31.4 W | 20.9 W |
| static: clock distribution | 99.0 W | 31.6 W |
| static: memory-interface idle | 14.0 W | 0.0 W |
| **static charged** (max of the enumeration and the measured clocked-idle floor) | 144.4 W | 52.5 W |
| **total** | 461.7 W | 87.6 W |

On HC1 the enumerated static power is 52.5 W and the measured clocked-idle floor is 50.0 W, so the enumeration binds and the floor is inert.

**The band.** Every term in the power block bar one is `assumed`, and
two of them -- the fabric clock and the array clock multiplier --
multiply, so the gates are reported at both ends of the whole band
with every term moved together. Moving one at a time would report a
sensitivity that is really a bias.

| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 338.9 W | 0.85x | 63.3 W | 0.25x | 0.32x |
| stated | 461.7 W | 1.15x | 87.6 W | 0.35x | 0.44x |
| high | 698.3 W | 1.75x | 374.6 W | 1.50x | 1.87x |

**The outcome, stated as an outcome.** The A100 gate lands at 1.15x of its published TDP. The HC1 gate lands at 0.35x of the top of its published band, **2.86x low**, against 2.28x low at the bottom of it. The asymmetry is the finding and it should not be smoothed over.

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
| Taalas HC1 (modelled reconstruction) | n/a (0.005908 J/attempt) | 87.6 | 0.0 |
| A100 80GB, weight-bound gate, same model and batch | 1.465768 J/token | 359.6 | 245.3 |

No tokens-per-joule ratio is admissible for this pair: the HC1 throughput reconstruction is capacity-infeasible and delivers zero modelled tokens. Its energy cell above is the attempted-step energy inside the diagnostic power calculation, not the energy of a feasible machine. The power gate remains useful as a disclosed component check, and it is 2.3-2.9x below the shipping card's published band, but it cannot support an efficiency advantage.

**Where the remaining HC1 shortfall could live, none of it fitted.**
The ROM array is charged its stated leakage density: 2.9 W at the point
and 11.2 W at the
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

- **8 of 1,810 feasible points (0.4%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: rom 8.
- By area class: wafer (>=40,000 mm2) 8.
- By KV store: hbm 8.
- By batch: B=256 8.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 43% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 256 throttles too, and the worst point here is at batch 256.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 144 | 0 | 65.0% | 92.8% | 0.580 | 54% |
| gpu | wafer (>=40,000 mm2) | 384 | 0 | 49.1% | 80.7% | 0.505 | 72% |
| rom | large array (5,000-40,000 mm2) | 216 | 0 | 34.1% | 79.1% | 0.396 | 54% |
| rom | wafer (>=40,000 mm2) | 1,066 | 8 | 30.3% | 100.0% | 0.500 | 78% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x87` | DeepSeek-V4-Flash-0731 | 256 | 70,905 | hbm | 1.136x | 35,452.5 / 35,452.5 W | 26% | 615.8 | 699.3 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x113` | DeepSeek-V4-Flash-0731 | 256 | 92,095 | hbm | 1.089x | 46,047.5 / 46,047.5 W | 28% | 783.7 | 853.2 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x61-perregion-romfill` | DeepSeek-V4-Flash-0731 | 256 | 49,715 | hbm | 1.087x | 24,857.5 / 24,857.5 W | 18% | 481.3 | 523.2 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x61-perregion` | DeepSeek-V4-Flash-0731 | 256 | 49,715 | hbm | 1.087x | 24,857.5 / 24,857.5 W | 18% | 481.3 | 523.2 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x62-perregion-romfill` | DeepSeek-V4-Flash-0731 | 256 | 50,530 | hbm | 1.084x | 25,265.0 / 25,265.0 W | 18% | 489.2 | 530.3 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x116` | DeepSeek-V4-Flash-0731 | 256 | 94,540 | hbm | 1.083x | 47,270.0 / 47,270.0 W | 28% | 803.1 | 869.5 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x57` | DeepSeek-V4-Flash-0731 | 256 | 46,455 | hbm | 1.056x | 23,227.5 / 23,227.5 W | 23% | 420.0 | 443.5 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x58` | DeepSeek-V4-Flash-0731 | 256 | 47,270 | hbm | 1.023x | 23,635.0 / 23,635.0 W | 23% | 426.4 | 436.1 |

The worst point's dynamic energy is kv read 96.0%, arithmetic 3.2%, operand delivery 0.6%, weight read 0.1%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | `DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 0.811344 | 3,914.4 | link_latency | `DSV4-Flash/b200_sxm-x29-tensor` | 9.222941 | 11,897.4 | link_latency | 11.37x |
| DeepSeek-V4-Flash-0731 | 2 | 138,675 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 1.118659 | 14,483.3 | link_latency | `DSV4-Flash/b200_sxm-x87-tensor` | 13.177914 | 32,809.1 | link_latency | 11.78x |
| DeepSeek-V4-Flash-0731 | 4 | 138,675 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 0.925416 | 15,028.9 | link_latency | `DSV4-Flash/b200_sxm-x87-tensor` | 7.901343 | 33,543.9 | link_latency | 8.54x |
| DeepSeek-V4-Flash-0731 | 8 | 277,350 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 0.972212 | 29,740.2 | link_latency | `DSV4-Flash/b200_sxm-x173-tensor` | 9.177135 | 64,881.1 | link_latency | 9.44x |
| DeepSeek-V4-Flash-0731 | 16 | 369,800 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 0.784538 | 41,699.0 | link_latency | `DSV4-Flash/b200_sxm-x231-tensor` | 8.237886 | 86,427.6 | link_latency | 10.50x |
| DeepSeek-V4-Flash-0731 | 32 | 554,700 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.706743 | 64,437.2 | link_latency | `DSV4-Flash/b200_sxm-x347-tensor` | 9.039943 | 127,946.6 | link_latency | 12.79x |
| DeepSeek-V4-Flash-0731 | 64 | 554,700 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.527190 | 71,939.8 | link_latency | `DSV4-Flash/b200_sxm-x347-tensor` | 7.439067 | 127,915.0 | link_latency | 14.11x |
| DeepSeek-V4-Flash-0731 | 256 | 277,100 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 0.256615 | 84,562.4 | compute | `DSV4-Flash/b200_sxm-x173-hybrid` | 2.002042 | 83,959.2 | weight_read | 7.80x |

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
| DeepSeek-V4-Flash-0731 | 1,000,000 | 284 B | 166.9 GB | 4.70 | 1.521 GB | 6.886 GB | 7.4 |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 21,289.9 | wafer-pipeline | 4,824.6 | wafer-tensor | 4.41x | 4,490.4 | pipeline | 1,290.0 | tensor | 3.48x | 4.74x | 3.74x | 0.79x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 29,811.2 | wafer-pipeline | 4,655.5 | wafer-hybrid | 6.40x | 4,968.1 | pipeline | 1,351.0 | tensor | 3.68x | 6.00x | 3.45x | 0.57x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 35,511.9 | wafer-pipeline | 4,553.7 | wafer-hybrid | 7.80x | 5,348.1 | pipeline | 1,374.9 | tensor | 3.89x | 6.64x | 3.31x | 0.50x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 39,216.9 | wafer-pipeline | 4,453.7 | wafer-hybrid | 8.81x | 5,567.1 | pipeline | 1,387.0 | tensor | 4.01x | 7.04x | 3.21x | 0.46x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 43,745.0 | wafer-pipeline | 4,264.1 | wafer-hybrid | 10.26x | 5,807.0 | pipeline | 1,399.7 | tensor | 4.15x | 7.53x | 3.05x | 0.40x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 46,408.4 | wafer-pipeline | 4,088.9 | wafer-hybrid | 11.35x | 5,939.9 | pipeline | 1,406.3 | tensor | 4.22x | 7.81x | 2.91x | 0.37x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 49,404.6 | wafer-pipeline | 3,777.5 | wafer-hybrid | 13.08x | 6,080.2 | pipeline | 1,413.1 | tensor | 4.30x | 8.13x | 2.67x | 0.33x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.33x to 0.79x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 4,824.6 | 4,824.6 | link_latency | DSV4-Flash/b200_sxm-x29-tensor | 46,400 | 1.00x | tensor | 589.32 | 1,290.0 | 1,290.0 | link_latency | 3.74x | 3.74x | 24.51x | 3.74x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x34 | 27,710 | 2,201.3 | 11,006.6 | link_latency | DSV4-Flash/b200_sxm-x17-tensor | 27,200 | 1.02x | tensor | 585.80 | 1,213.4 | 1,213.4 | link_latency | 1.81x | 9.07x | 8.53x | 1.81x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,315.7 | 12,947.1 | link_latency | DSV4-Flash/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 636.53 | 1,244.9 | 2,489.7 | link_latency | 3.47x | 5.20x | 44.93x | 3.47x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x34 | 27,710 | 2,201.3 | 11,006.6 | link_latency | DSV4-Flash/b200_sxm-x17-hybrid | 27,200 | 1.02x | hybrid | 212.84 | 1,107.3 | 3,321.8 | weight_read | 1.99x | 3.31x | 8.53x | 1.99x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,223.6 | 16,894.2 | link_latency | DSV4-Flash/b200_sxm-x116-tensor | 185,600 | 1.00x | tensor | 721.59 | 1,077.7 | 4,310.7 | link_latency | 3.92x | 3.92x | 54.93x | 3.92x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x34 | 27,710 | 2,201.3 | 11,006.6 | link_latency | DSV4-Flash/b200_sxm-x17-hybrid | 27,200 | 1.02x | hybrid | 213.64 | 1,003.5 | 4,013.8 | weight_read | 2.19x | 2.74x | 8.53x | 2.19x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,891.3 | 31,130.1 | link_latency | DSV4-Flash/b200_sxm-x231-tensor | 369,600 | 1.00x | tensor | 898.50 | 894.5 | 7,156.1 | link_latency | 4.35x | 4.35x | 90.38x | 4.35x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x34 | 27,710 | 1,692.9 | 13,543.6 | compute | DSV4-Flash/b200_sxm-x17-hybrid | 27,200 | 1.02x | hybrid | 216.81 | 762.8 | 6,102.6 | weight_read | 2.22x | 2.22x | 6.56x | 2.22x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,425.1 | 54,802.3 | link_latency | DSV4-Flash/b200_sxm-x347-tensor | 555,200 | 1.00x | tensor | 1,249.40 | 668.3 | 10,692.8 | link_latency | 5.13x | 5.13x | 114.77x | 5.13x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x34 | 27,710 | 1,047.7 | 16,763.4 | compute | DSV4-Flash/b200_sxm-x17-hybrid | 27,200 | 1.02x | hybrid | 223.17 | 543.6 | 8,698.4 | weight_read | 1.93x | 1.93x | 4.06x | 1.93x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,849.2 | 91,174.9 | link_latency | DSV4-Flash/b200_sxm-x347-tensor | 555,200 | 1.00x | tensor | 1,943.24 | 442.3 | 14,153.5 | link_latency | 6.44x | 6.44x | 95.47x | 6.44x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x34 | 27,710 | 631.4 | 21,466.8 | compute | DSV4-Flash/b200_sxm-x17-hybrid | 27,200 | 1.02x | hybrid | 235.87 | 366.6 | 11,730.9 | weight_read | 1.72x | 1.83x | 3.27x | 1.72x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,132.2 | 136,459.1 | link_latency | DSV4-Flash/b200_sxm-x347-tensor | 555,200 | 1.00x | tensor | 3,330.91 | 268.7 | 17,195.0 | link_latency | 7.94x | 7.94x | 71.45x | 7.94x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x34 | 27,710 | 341.0 | 21,824.0 | compute | DSV4-Flash/b200_sxm-x17-hybrid | 27,200 | 1.02x | hybrid | 261.29 | 239.4 | 15,321.3 | weight_read | 1.42x | 1.42x | 2.54x | 1.42x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x340-romfill | 277,100 | 1,287.2 | 329,530.4 | compute | DSV4-Flash/b200_sxm-x173-hybrid | 276,800 | 1.00x | hybrid | 312.98 | 163.8 | 41,936.8 | weight_read | 7.86x | 7.86x | 25.38x | 7.86x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x34 | 27,710 | 86.5 | 22,137.2 | compute | DSV4-Flash/b200_sxm-x17-hybrid | 27,200 | 1.02x | hybrid | 413.77 | 106.2 | 27,197.0 | weight_read | 0.81x | 0.81x | 1.53x | 0.81x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 8 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 8 | Link us at domain 72 | tok/s at 8 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 12 | 19,200 | 210.65 | 208.55 | 1,291.1 | 1,294.6 |
| DeepSeek-V4-Flash-0731 | 17 | 27,200 | 585.80 | 208.61 | 1,213.4 | 2,237.3 |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 585.80 | 208.62 | 1,223.5 | 2,272.0 |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 585.80 | 208.62 | 1,232.8 | 2,304.2 |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 585.80 | 208.64 | 1,256.5 | 2,388.5 |
| DeepSeek-V4-Flash-0731 | 23 | 36,800 | 585.80 | 208.65 | 1,263.3 | 2,413.1 |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 589.32 | 208.67 | 1,290.0 | 2,534.5 |
| DeepSeek-V4-Flash-0731 | 30 | 48,000 | 589.32 | 208.67 | 1,294.3 | 2,551.2 |
| DeepSeek-V4-Flash-0731 | 31 | 49,600 | 589.32 | 208.67 | 1,298.4 | 2,567.1 |
| DeepSeek-V4-Flash-0731 | 32 | 51,200 | 589.32 | 208.67 | 1,302.3 | 2,582.3 |
| DeepSeek-V4-Flash-0731 | 44 | 70,400 | 592.84 | 208.70 | 1,330.5 | 2,721.2 |
| DeepSeek-V4-Flash-0731 | 46 | 73,600 | 592.84 | 208.70 | 1,334.6 | 2,738.7 |
| DeepSeek-V4-Flash-0731 | 47 | 75,200 | 592.84 | 208.70 | 1,336.6 | 2,747.0 |
| DeepSeek-V4-Flash-0731 | 50 | 80,000 | 593.85 | 208.70 | 1,340.3 | 2,770.3 |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 594.60 | 208.71 | 1,351.0 | 2,822.6 |
| DeepSeek-V4-Flash-0731 | 59 | 94,400 | 594.60 | 208.71 | 1,352.3 | 2,828.3 |
| DeepSeek-V4-Flash-0731 | 61 | 97,600 | 594.60 | 208.71 | 1,354.8 | 2,839.2 |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 596.04 | 579.01 | 1,374.9 | 1,407.9 |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 597.07 | 579.01 | 1,387.0 | 1,422.6 |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 597.96 | 586.06 | 1,399.7 | 1,423.4 |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 598.43 | 589.58 | 1,406.3 | 1,424.0 |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 598.92 | 591.69 | 1,413.1 | 1,427.6 |

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
| DeepSeek-V4-Flash-0731 | 12 | 19,200 | 299.8 | 1,153.6 | 1,291.1 | hybrid | 210.65 | 27.2% | weight_read |
| DeepSeek-V4-Flash-0731 | 17 | 27,200 | 258.1 | 1,213.4 | 1,107.3 | tensor | 585.80 | 71.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 251.3 | 1,223.5 | 1,133.0 | tensor | 585.80 | 71.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 244.9 | 1,232.8 | 1,157.2 | tensor | 585.80 | 72.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 227.9 | 1,256.5 | 1,222.2 | tensor | 585.80 | 73.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 23 | 36,800 | 222.8 | 1,263.3 | 1,241.7 | tensor | 585.80 | 74.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 196.8 | 1,290.0 | 1,085.3 | tensor | 589.32 | 76.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 30 | 48,000 | 193.1 | 1,294.3 | 1,097.6 | tensor | 589.32 | 76.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 31 | 49,600 | 189.6 | 1,298.4 | 1,109.5 | tensor | 589.32 | 76.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | 51,200 | 186.2 | 1,302.3 | 1,120.9 | tensor | 589.32 | 76.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 44 | 70,400 | 153.6 | 1,330.5 | 900.8 | tensor | 592.84 | 78.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 46 | 73,600 | 149.4 | 1,334.6 | 912.3 | tensor | 592.84 | 79.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 47 | 75,200 | 147.4 | 1,336.6 | 917.9 | tensor | 592.84 | 79.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 50 | 80,000 | 141.6 | 1,340.3 | 824.3 | tensor | 593.85 | 79.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 128.3 | 1,351.0 | 768.2 | tensor | 594.60 | 80.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 59 | 94,400 | 126.8 | 1,352.3 | 771.6 | tensor | 594.60 | 80.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 61 | 97,600 | 124.0 | 1,354.8 | 778.2 | tensor | 594.60 | 80.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 96.1 | 1,374.9 | 645.0 | tensor | 596.04 | 82.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 76.9 | 1,387.0 | 519.6 | tensor | 597.07 | 82.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 55.3 | 1,399.7 | 391.0 | tensor | 597.96 | 83.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 43.1 | 1,406.3 | 313.5 | tensor | 598.43 | 84.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 29.8 | 1,413.1 | 219.6 | tensor | 598.92 | 84.6% | link_latency |

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
| DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x35 | DeepSeek-V4-Flash-0731 | 35 | pipeline | nvlink5 | infiniband_ndr | 34 | 45.05 us | 2,219.8 tok/s | 22,198.3 tok/s | 30 x point_to_point span 2 on nvlink5 (traversals 1.0) = 36.27 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer_n5 | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x34 | DeepSeek-V4-Flash-0731 | 34 | tensor | nvlink5 | infiniband_ndr | 172 | 591.43 us | 169.1 tok/s | 1,690.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 382.98 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x35 | DeepSeek-V4-Flash-0731 | 35 | hybrid | nvlink5 | infiniband_ndr | 90 | 217.23 us | 460.3 tok/s | 4,603.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x35 | DeepSeek-V4-Flash-0731 | 35 | pipeline | nvlink5 | infiniband_ndr | 34 | 45.05 us | 2,219.8 tok/s | 22,198.3 tok/s | 30 x point_to_point span 2 on nvlink5 (traversals 1.0) = 36.27 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3 | DeepSeek-V4-Flash-0731 | 3 | pipeline | on_wafer_n5 | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-tensor-x34 | DeepSeek-V4-Flash-0731 | 34 | tensor | nvlink5 | infiniband_ndr | 172 | 591.43 us | 169.1 tok/s | 1,690.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 382.98 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x3 | DeepSeek-V4-Flash-0731 | 3 | tensor | on_wafer_n5 | inter_wafer | 172 | 1,034.94 us | 96.6 tok/s | 966.2 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us; 86 x all_reduce span 3 on inter_wafer (traversals 2.0) = 869.39 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x35 | DeepSeek-V4-Flash-0731 | 35 | hybrid | nvlink5 | infiniband_ndr | 90 | 217.23 us | 460.3 tok/s | 4,603.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3 | DeepSeek-V4-Flash-0731 | 3 | hybrid | on_wafer_n5 | inter_wafer | 88 | 175.66 us | 569.3 tok/s | 5,692.8 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us; 2 x point_to_point span 2 on inter_wafer (traversals 1.0) = 10.11 us |
| DSV4-Flash/b200_sxm-x12-pipeline | DeepSeek-V4-Flash-0731 | 12 | pipeline | nvlink5 | infiniband_ndr | 11 | 14.28 us | 7,000.4 tok/s | 70,004.2 tok/s | 10 x point_to_point span 2 on nvlink5 (traversals 1.0) = 12.09 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x12-tensor | DeepSeek-V4-Flash-0731 | 12 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x12-hybrid | DeepSeek-V4-Flash-0731 | 12 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x17-pipeline | DeepSeek-V4-Flash-0731 | 17 | pipeline | nvlink5 | infiniband_ndr | 16 | 21.32 us | 4,691.5 tok/s | 46,915.1 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x17-tensor | DeepSeek-V4-Flash-0731 | 17 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x17-hybrid | DeepSeek-V4-Flash-0731 | 17 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x18-pipeline | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink5 | infiniband_ndr | 17 | 22.52 us | 4,439.7 tok/s | 44,396.7 tok/s | 15 x point_to_point span 2 on nvlink5 (traversals 1.0) = 18.14 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x18-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x18-hybrid | DeepSeek-V4-Flash-0731 | 18 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink5 | infiniband_ndr | 18 | 23.73 us | 4,213.5 tok/s | 42,134.9 tok/s | 16 x point_to_point span 2 on nvlink5 (traversals 1.0) = 19.35 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x22-pipeline | DeepSeek-V4-Flash-0731 | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 27.36 us | 3,654.9 tok/s | 36,548.9 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 22.97 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x22-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x22-hybrid | DeepSeek-V4-Flash-0731 | 22 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x23-pipeline | DeepSeek-V4-Flash-0731 | 23 | pipeline | nvlink5 | infiniband_ndr | 22 | 28.57 us | 3,500.2 tok/s | 35,002.1 tok/s | 20 x point_to_point span 2 on nvlink5 (traversals 1.0) = 24.18 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x23-tensor | DeepSeek-V4-Flash-0731 | 23 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x23-hybrid | DeepSeek-V4-Flash-0731 | 23 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x29-pipeline | DeepSeek-V4-Flash-0731 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x29-tensor | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x29-hybrid | DeepSeek-V4-Flash-0731 | 29 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x30-pipeline | DeepSeek-V4-Flash-0731 | 30 | pipeline | nvlink5 | infiniband_ndr | 29 | 38.02 us | 2,630.3 tok/s | 26,303.2 tok/s | 26 x point_to_point span 2 on nvlink5 (traversals 1.0) = 31.44 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x30-tensor | DeepSeek-V4-Flash-0731 | 30 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x30-hybrid | DeepSeek-V4-Flash-0731 | 30 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x31-pipeline | DeepSeek-V4-Flash-0731 | 31 | pipeline | nvlink5 | infiniband_ndr | 30 | 39.23 us | 2,549.2 tok/s | 25,492.5 tok/s | 27 x point_to_point span 2 on nvlink5 (traversals 1.0) = 32.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x31-tensor | DeepSeek-V4-Flash-0731 | 31 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x31-hybrid | DeepSeek-V4-Flash-0731 | 31 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x32-pipeline | DeepSeek-V4-Flash-0731 | 32 | pipeline | nvlink5 | infiniband_ndr | 31 | 40.44 us | 2,473.0 tok/s | 24,730.2 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.85 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x32-tensor | DeepSeek-V4-Flash-0731 | 32 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x32-hybrid | DeepSeek-V4-Flash-0731 | 32 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x44-pipeline | DeepSeek-V4-Flash-0731 | 44 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x44-tensor | DeepSeek-V4-Flash-0731 | 44 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x44-hybrid | DeepSeek-V4-Flash-0731 | 44 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x46-pipeline | DeepSeek-V4-Flash-0731 | 46 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x46-tensor | DeepSeek-V4-Flash-0731 | 46 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x46-hybrid | DeepSeek-V4-Flash-0731 | 46 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x47-pipeline | DeepSeek-V4-Flash-0731 | 47 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x47-tensor | DeepSeek-V4-Flash-0731 | 47 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x47-hybrid | DeepSeek-V4-Flash-0731 | 47 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x50-pipeline | DeepSeek-V4-Flash-0731 | 50 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x50-tensor | DeepSeek-V4-Flash-0731 | 50 | tensor | nvlink5 | infiniband_ndr | 172 | 593.85 us | 168.4 tok/s | 1,683.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 385.39 us |
| DSV4-Flash/b200_sxm-x50-hybrid | DeepSeek-V4-Flash-0731 | 50 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.62 us | 451.2 tok/s | 4,512.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| DSV4-Flash/b200_sxm-x58-pipeline | DeepSeek-V4-Flash-0731 | 58 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x58-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x58-hybrid | DeepSeek-V4-Flash-0731 | 58 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x59-pipeline | DeepSeek-V4-Flash-0731 | 59 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x59-tensor | DeepSeek-V4-Flash-0731 | 59 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x59-hybrid | DeepSeek-V4-Flash-0731 | 59 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x61-pipeline | DeepSeek-V4-Flash-0731 | 61 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x61-tensor | DeepSeek-V4-Flash-0731 | 61 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x61-hybrid | DeepSeek-V4-Flash-0731 | 61 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x87-pipeline | DeepSeek-V4-Flash-0731 | 87 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x87-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink5 | infiniband_ndr | 172 | 596.04 us | 167.8 tok/s | 1,677.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 387.59 us |
| DSV4-Flash/b200_sxm-x87-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink5 | infiniband_ndr | 96 | 230.39 us | 434.0 tok/s | 4,340.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| DSV4-Flash/b200_sxm-x116-pipeline | DeepSeek-V4-Flash-0731 | 116 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x116-tensor | DeepSeek-V4-Flash-0731 | 116 | tensor | nvlink5 | infiniband_ndr | 172 | 597.07 us | 167.5 tok/s | 1,674.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 388.61 us |
| DSV4-Flash/b200_sxm-x116-hybrid | DeepSeek-V4-Flash-0731 | 116 | hybrid | nvlink5 | infiniband_ndr | 100 | 239.17 us | 418.1 tok/s | 4,181.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| DSV4-Flash/b200_sxm-x173-pipeline | DeepSeek-V4-Flash-0731 | 173 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x173-tensor | DeepSeek-V4-Flash-0731 | 173 | tensor | nvlink5 | infiniband_ndr | 172 | 597.96 us | 167.2 tok/s | 1,672.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 389.51 us |
| DSV4-Flash/b200_sxm-x173-hybrid | DeepSeek-V4-Flash-0731 | 173 | hybrid | nvlink5 | infiniband_ndr | 107 | 254.53 us | 392.9 tok/s | 3,928.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| DSV4-Flash/b200_sxm-x231-pipeline | DeepSeek-V4-Flash-0731 | 231 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x231-tensor | DeepSeek-V4-Flash-0731 | 231 | tensor | nvlink5 | infiniband_ndr | 172 | 598.43 us | 167.1 tok/s | 1,671.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 389.97 us |
| DSV4-Flash/b200_sxm-x231-hybrid | DeepSeek-V4-Flash-0731 | 231 | hybrid | nvlink5 | infiniband_ndr | 114 | 269.88 us | 370.5 tok/s | 3,705.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 61.43 us |
| DSV4-Flash/b200_sxm-x347-pipeline | DeepSeek-V4-Flash-0731 | 347 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x347-tensor | DeepSeek-V4-Flash-0731 | 347 | tensor | nvlink5 | infiniband_ndr | 172 | 598.92 us | 167.0 tok/s | 1,669.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 390.47 us |
| DSV4-Flash/b200_sxm-x347-hybrid | DeepSeek-V4-Flash-0731 | 347 | hybrid | nvlink5 | infiniband_ndr | 128 | 300.60 us | 332.7 tok/s | 3,326.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 42 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 92.14 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 1 | wafer | wafer | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 4,824.6 | 0.104 | 2,374.7 (28,525) | 4,824.6 (46,225) | 2.03x | link_latency |
| DeepSeek-V4-Flash-0731 | 2 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,315.7 | 0.031 | 2,374.7 (28,525) | 4,315.7 (138,675) | 1.82x | link_latency |
| DeepSeek-V4-Flash-0731 | 4 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,060.0 | 0.029 | 2,374.7 (28,525) | 4,060.0 (138,675) | 1.71x | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 3,823.8 | 0.014 | 2,175.9 (30,155) | 3,823.8 (277,350) | 1.76x | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,321.9 | 0.009 | 2,069.1 (35,860) | 3,321.9 (369,800) | 1.61x | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,849.2 | 0.005 | 2,038.5 (70,905) | 2,849.2 (554,700) | 1.40x | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,132.2 | 0.004 | 1,909.1 (138,550) | 2,132.2 (554,700) | 1.12x | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x340-romfill | 277,100 | 1,287.2 | 0.005 | 1,287.2 (277,100) | 849.5 (554,700) | 0.66x | compute |

## The two ROM floorplans on one die

This probe requests 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. The ROM-plus-MAC floorplan holds the requested weights; the compute-in-ROM floorplan holds only 87.0% and is infeasible at this area. The failed floorplan is retained so the capacity cost of the larger cell remains visible.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 374.6 mm2 | 521.6 mm2 |
| weight capacity | 3.51 GB (100.0%) | 3.06 GB (87.0%) |
| capacity-feasible | yes | **no** |
| compute block | 293.7 mm2 | 146.7 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 0.0 mm2 |
| sustained fp8 compute roof | 2.197e+14 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 1.098e+14 | n/a |
| weight bytes/s the array supplies | 1.019e+14 | 8.872e+13 |
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
| DeepSeek-V4-Flash-0731 | 256 | 574.9 MB | 98.1 mm2 | 17.65 mm2 (18.0%) | 25,105 mm2 | 4,519 mm2 | 28,467 mm2 = 34.9 reticles |

## The batch-amortisation fork, reported rather than resolved

`docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md` names an open
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
subject of `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md`: its sweep depth
is the load of the **busiest** expert region, computed from the routing
distribution rather than from the mean engaged region.

| Model | B | Spare silicon | Batched aggregate | Per-stream aggregate | Per-region aggregate | Per-stream penalty | Per-region over broadcast | Batched binds on | Per-stream binds on | Per-region binds on |
|---|---:|---|---:|---:|---:|---:|---:|---|---|---|
| DeepSeek-V4-Flash-0731 | 1 | sram | 26,095.5 | 26,043.0 | 26,043.0 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 26,095.5 | 26,043.0 | 26,043.0 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 26,095.5 | 26,043.0 | 26,043.0 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 26,258.5 | 26,043.0 | 26,353.6 | 1.01x | 1.01x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | sram | 43,449.7 | 26,043.0 | 46,137.9 | 1.67x | 1.77x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | sram | 73,183.4 | 26,043.0 | 48,868.1 | 2.81x | 1.88x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 113,216.5 | 26,043.0 | 70,156.9 | 4.35x | 2.69x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 219,204.9 | 26,066.2 | 123,215.3 | 8.41x | 4.73x | weight_read | weight_read | thermal |
| DeepSeek-V4-Flash-0731 | 1 | rom | 272,902.6 | 68,227.8 | 68,227.8 | 4.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 272,902.6 | 68,227.8 | 68,227.8 | 4.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 272,902.6 | 68,227.8 | 68,227.8 | 4.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 272,902.6 | 68,227.8 | 68,227.8 | 4.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 272,902.6 | 68,227.8 | 68,227.8 | 4.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 272,902.6 | 68,227.8 | 68,227.8 | 4.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 272,902.6 | 68,227.8 | 79,864.9 | 4.00x | 1.17x | kv_read | kv_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 329,530.4 | 68,387.6 | 196,441.3 | 4.82x | 2.87x | compute | kv_read | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,095.5 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 272,902.6 | 0.492 | kv_read | 10.46x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,043.0 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,043.0 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,095.5 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 272,902.6 | 0.492 | kv_read | 10.46x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,043.0 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,043.0 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,095.5 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 272,902.6 | 0.492 | kv_read | 10.46x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,043.0 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,043.0 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 26,258.5 | 0.189 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 272,902.6 | 0.492 | kv_read | 10.39x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,043.0 | 0.188 | weight_read | 0.99x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 2.60x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.57 | 26,353.6 | 0.285 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 2.60x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 43,449.7 | 0.235 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 272,902.6 | 0.492 | kv_read | 6.28x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,043.0 | 0.188 | weight_read | 0.60x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 1.57x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.13 | 46,137.9 | 0.499 | link_latency | 1.06x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 1.57x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 73,183.4 | 0.264 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 272,902.6 | 0.492 | kv_read | 3.73x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,043.0 | 0.188 | weight_read | 0.36x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 0.93x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 2.37 | 48,868.1 | 0.352 | kv_read | 0.67x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 0.93x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 113,216.5 | 0.306 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 272,902.6 | 0.492 | kv_read | 2.41x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,043.0 | 0.188 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.07 | 1.00 | 68,227.8 | 0.492 | kv_read | 0.60x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x61-perregion | 49,715 | 1.00 | 2.13 | 70,156.9 | 1.411 | weight_read | 0.62x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x98-perregion-romfill | 79,870 | 1.62 | 1.76 | 79,864.9 | 1.000 | weight_read | 0.71x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x170 | 138,550 | 1.00 | 1.00 | 219,204.9 | 1.582 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x340-romfill | 277,100 | 6.84 | 1.00 | 329,530.4 | 1.189 | compute | 1.50x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.50 | 26,066.2 | 0.188 | weight_read | 0.12x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 3.07 | 1.50 | 68,387.6 | 0.493 | kv_read | 0.31x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x61-perregion | 49,715 | 1.00 | 4.03 | 123,215.3 | 2.478 | thermal | 0.56x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x98-perregion-romfill | 79,870 | 1.62 | 3.18 | 196,441.3 | 2.460 | kv_read | 0.90x |

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
| DeepSeek-V4-Flash-0731 | 1 | 58 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 61 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 61 | 1.05 | 1.001 | 1.004 | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | 61 | 4.20 | 1.038 | 1.611 | 1.55x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 2 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 8 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 16 | 12 | 6.00 | 3.78 | 1.59x |
| DeepSeek-V4-Flash-0731 | 32 | 12 | 8.94 | 4.77 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 12 | 11.15 | 5.81 | 1.92x |
| DeepSeek-V4-Flash-0731 | 256 | 12 | 12.00 | 7.67 | 1.56x |
| DeepSeek-V4-Flash-0731 | 1 | 17 | 5.18 | 3.76 | 1.38x |
| DeepSeek-V4-Flash-0731 | 2 | 17 | 5.18 | 3.76 | 1.38x |
| DeepSeek-V4-Flash-0731 | 4 | 17 | 5.18 | 3.76 | 1.38x |
| DeepSeek-V4-Flash-0731 | 8 | 17 | 5.18 | 3.76 | 1.38x |
| DeepSeek-V4-Flash-0731 | 16 | 17 | 5.18 | 3.76 | 1.38x |
| DeepSeek-V4-Flash-0731 | 32 | 17 | 8.37 | 4.82 | 1.74x |
| DeepSeek-V4-Flash-0731 | 64 | 17 | 12.48 | 6.19 | 2.02x |
| DeepSeek-V4-Flash-0731 | 256 | 17 | 16.84 | 9.01 | 1.87x |
| DeepSeek-V4-Flash-0731 | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 16 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 32 | 18 | 8.16 | 4.80 | 1.70x |
| DeepSeek-V4-Flash-0731 | 64 | 18 | 12.49 | 6.22 | 2.01x |
| DeepSeek-V4-Flash-0731 | 256 | 18 | 17.73 | 9.20 | 1.93x |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 2 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 8 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 16 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 32 | 19 | 7.95 | 4.78 | 1.66x |
| DeepSeek-V4-Flash-0731 | 64 | 19 | 12.44 | 6.24 | 1.99x |
| DeepSeek-V4-Flash-0731 | 256 | 19 | 18.57 | 9.38 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 4 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 8 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 16 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 32 | 22 | 7.31 | 4.70 | 1.55x |
| DeepSeek-V4-Flash-0731 | 64 | 22 | 12.05 | 6.25 | 1.93x |
| DeepSeek-V4-Flash-0731 | 256 | 22 | 20.76 | 9.81 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1 | 23 | 5.38 | 4.06 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 23 | 5.38 | 4.06 | 1.33x |
| DeepSeek-V4-Flash-0731 | 4 | 23 | 5.38 | 4.06 | 1.33x |
| DeepSeek-V4-Flash-0731 | 8 | 23 | 5.38 | 4.06 | 1.33x |
| DeepSeek-V4-Flash-0731 | 16 | 23 | 5.38 | 4.06 | 1.33x |
| DeepSeek-V4-Flash-0731 | 32 | 23 | 7.10 | 4.67 | 1.52x |
| DeepSeek-V4-Flash-0731 | 64 | 23 | 11.88 | 6.24 | 1.90x |
| DeepSeek-V4-Flash-0731 | 256 | 23 | 21.36 | 9.92 | 2.15x |
| DeepSeek-V4-Flash-0731 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 4 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 8 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 16 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 32 | 29 | 6.01 | 4.50 | 1.34x |
| DeepSeek-V4-Flash-0731 | 64 | 29 | 10.66 | 6.08 | 1.75x |
| DeepSeek-V4-Flash-0731 | 256 | 29 | 23.69 | 10.39 | 2.28x |
| DeepSeek-V4-Flash-0731 | 1 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 4 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 8 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 16 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4-Flash-0731 | 32 | 30 | 5.85 | 4.46 | 1.31x |
| DeepSeek-V4-Flash-0731 | 64 | 30 | 10.45 | 6.05 | 1.73x |
| DeepSeek-V4-Flash-0731 | 256 | 30 | 23.88 | 10.44 | 2.29x |
| DeepSeek-V4-Flash-0731 | 1 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 2 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 8 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 16 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 32 | 31 | 5.70 | 4.42 | 1.29x |
| DeepSeek-V4-Flash-0731 | 64 | 31 | 10.24 | 6.02 | 1.70x |
| DeepSeek-V4-Flash-0731 | 256 | 31 | 24.03 | 10.48 | 2.29x |
| DeepSeek-V4-Flash-0731 | 1 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 2 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 8 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 16 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 32 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 64 | 32 | 10.04 | 5.99 | 1.68x |
| DeepSeek-V4-Flash-0731 | 256 | 32 | 24.15 | 10.52 | 2.30x |
| DeepSeek-V4-Flash-0731 | 1 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 8 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 16 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 32 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 64 | 44 | 7.96 | 5.66 | 1.41x |
| DeepSeek-V4-Flash-0731 | 256 | 44 | 23.39 | 10.61 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 8 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 16 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 32 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 64 | 46 | 7.68 | 5.61 | 1.37x |
| DeepSeek-V4-Flash-0731 | 256 | 46 | 23.06 | 10.59 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1 | 47 | 5.69 | 4.73 | 1.20x |
| DeepSeek-V4-Flash-0731 | 2 | 47 | 5.69 | 4.73 | 1.20x |
| DeepSeek-V4-Flash-0731 | 4 | 47 | 5.69 | 4.73 | 1.20x |
| DeepSeek-V4-Flash-0731 | 8 | 47 | 5.69 | 4.73 | 1.20x |
| DeepSeek-V4-Flash-0731 | 16 | 47 | 5.69 | 4.73 | 1.20x |
| DeepSeek-V4-Flash-0731 | 32 | 47 | 5.69 | 4.73 | 1.20x |
| DeepSeek-V4-Flash-0731 | 64 | 47 | 7.54 | 5.58 | 1.35x |
| DeepSeek-V4-Flash-0731 | 256 | 47 | 22.88 | 10.58 | 2.16x |
| DeepSeek-V4-Flash-0731 | 1 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 2 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 4 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 8 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 16 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 32 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 64 | 50 | 7.16 | 5.48 | 1.31x |
| DeepSeek-V4-Flash-0731 | 256 | 50 | 22.32 | 10.54 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 4 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 8 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 16 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 32 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 64 | 58 | 6.30 | 5.21 | 1.21x |
| DeepSeek-V4-Flash-0731 | 256 | 58 | 20.74 | 10.34 | 2.01x |
| DeepSeek-V4-Flash-0731 | 1 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 4 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 8 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 16 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 32 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 64 | 59 | 6.21 | 5.17 | 1.20x |
| DeepSeek-V4-Flash-0731 | 256 | 59 | 20.54 | 10.31 | 1.99x |
| DeepSeek-V4-Flash-0731 | 1 | 61 | 5.76 | 4.95 | 1.16x |
| DeepSeek-V4-Flash-0731 | 2 | 61 | 5.76 | 4.95 | 1.16x |
| DeepSeek-V4-Flash-0731 | 4 | 61 | 5.76 | 4.95 | 1.16x |
| DeepSeek-V4-Flash-0731 | 8 | 61 | 5.76 | 4.95 | 1.16x |
| DeepSeek-V4-Flash-0731 | 16 | 61 | 5.76 | 4.95 | 1.16x |
| DeepSeek-V4-Flash-0731 | 32 | 61 | 5.76 | 4.95 | 1.16x |
| DeepSeek-V4-Flash-0731 | 64 | 61 | 6.02 | 5.10 | 1.18x |
| DeepSeek-V4-Flash-0731 | 256 | 61 | 20.15 | 10.24 | 1.97x |
| DeepSeek-V4-Flash-0731 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 4 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 8 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 16 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 32 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 64 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 256 | 87 | 15.73 | 9.34 | 1.68x |
| DeepSeek-V4-Flash-0731 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 2 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 4 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 8 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 16 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 32 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 64 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 256 | 116 | 12.40 | 8.75 | 1.42x |
| DeepSeek-V4-Flash-0731 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 2 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 4 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 8 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 16 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 32 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 64 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 256 | 173 | 8.63 | 7.48 | 1.15x |
| DeepSeek-V4-Flash-0731 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 4 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 8 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 16 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 32 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 64 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 256 | 231 | 6.56 | 6.17 | 1.06x |
| DeepSeek-V4-Flash-0731 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 4 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 8 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 16 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 32 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 64 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 256 | 347 | 5.96 | 5.77 | 1.03x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 1.8% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 6.0% |

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
| DeepSeek-V4-Flash-0731 | 1 | 58 | 99.65% | 118.38 | 2.05 |
| DeepSeek-V4-Flash-0731 | 2 | 2 | 5.80% | 13.53 | 2.05 |
| DeepSeek-V4-Flash-0731 | 4 | 2 | 5.80% | 13.53 | 2.05 |
| DeepSeek-V4-Flash-0731 | 8 | 2 | 5.80% | 13.53 | 2.05 |
| DeepSeek-V4-Flash-0731 | 16 | 2 | 5.80% | 13.53 | 2.05 |

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
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 631.4 | 21,466.8 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 631.4 | 21,466.8 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 631.4 | 21,466.8 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 631.4 | 21,466.8 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 631.4 | 21,466.8 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 631.4 | 21,466.8 |
| DeepSeek-V4-Flash-0731 | 64 | 4.37% | 14.2 GB | 8.51% | 411.83 TB/s | 4,841.92 TB/s | 341.0 | 21,824.0 |
| DeepSeek-V4-Flash-0731 | 256 | 16.35% | 31.8 GB | 19.08% | 923.70 TB/s | 4,841.92 TB/s | 86.5 | 22,137.2 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | link_latency | 174 |
| gpu | weight_read | 354 |
| rom | compute | 85 |
| rom | infeasible | 1054 |
| rom | kv_read | 95 |
| rom | link_latency | 580 |
| rom | thermal | 8 |
| rom | weight_read | 514 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 1054 |

## Mechanical consistency audit

**PASS** over 58,205 checks.

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 70 |
| derived | 41 |
| assumed | 59 |

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
- `latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4.1-Flash-engram-host`
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
  2.3-2.9x low on the other.** Leakage, clock distribution, operand
  delivery and a measured clocked-idle floor are charged per mm2 per
  second whether or not a byte moves, and the HBM traffic energy is a
  measured SC 2025 figure rather than an HBM2-era model. The A100 lands
  at 1.15x of its published TDP under a saturating load; the Taalas HC1
  lands at 0.35x of its published card power. **The second one FAILS its
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

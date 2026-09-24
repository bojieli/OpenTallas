# Area-constrained roofline: n5_vs_b200-deepseek-v41-flash-engram-host

> CANDIDATE MODEL under n5_vs_b200: DeepSeek-V4.1-Flash-engram-host at 200,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 164x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 96 devices. On the GPU side the correction reaches 31x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 46 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash-engram-host takes 57 x 815 mm2 (46,455 mm2, array, KV in SRAM) at 13,352 tok/s per user and 287 tok/s per 1,000 mm2, holding 1 session, against 29 copies of one unified HBM die at the same silicon: 3.7x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash-engram-host on 78,240 mm2 of ROM silicon at 17,886 tok/s per user against 78,400 mm2 of b200_sxm-x49-nvl72-tensor at 4,065 tok/s: **4.4x**, ROM binding on `compute` and the GPU on `link_latency`. It holds 53,789 resident sessions against the GPU cluster's 42,226. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 8.86x to it.** At 92,095 mm2 on DeepSeek-V4.1-Flash-engram-host the pipeline-only GPU delivers 471.05 tok/s and the same silicon running tensor delivers 4,174 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4.1-Flash-engram-host, ROM binding on `link_latency`) to 3.35x (DeepSeek-V4.1-Flash-engram-host, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash-engram-host engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 1,937 to 113,676 tok/s, and its rate with every slot occupied from 110,434 to 113,676. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 57 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 567 us over NVLink, capping per-user decode at 1,763 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 154.0 us and cap it at 6,494 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 10 operating points and an array 8; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 85 of 5112 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 179.8x of aggregate throughput (DeepSeek-V4.1-Flash-engram-host). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 25.97x, on DeepSeek-V4.1-Flash-engram-host at batch 4096, where the busiest region carries 3.17x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 300 of 5,112 feasible points (5.9%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x7-pipeline` at batch 4096 on 11,200 mm2, throttled 1.09x from 19 to 18 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 86% weight read against 85.6% weight read. The ROM sweep is not what melts it.


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

### DeepSeek-V4.1-Flash-engram-host at 200,000 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x57`** -- 57 x 815 mm2 reticle dies, 46,455 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **13,352.1 tok/s per user** (0.07 ms/token), binding on `link_latency`
- **287.4 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 13,352 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 2,929 W at 0.063 W/mm2, 219.4 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 29 copies of one unified HBM die -- `b200_sxm-x29-nvl72-tensor`, 46,400 mm2, area ratio 1.0012 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 46,455 | 46,400 | 1.0012 |
| user tok/s | 13,352.1 | 3,644.5 | 3.66x |
| aggregate tok/s | 13,352 | 3,644 | 0.98x |
| resident sessions | 1 | 24,296 | -- |
| J/token | 0.2194 | 4.1675 | 19.0x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 24,296 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x58-nvl72-tensor` at 92,800 mm2 and 4,173.9 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 17,885.6 | 228.6 | 53,789 | 4.40x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 17,885.6 | 228.6 | 53,789 | 4.40x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x54` | 44,010 | 12,460.6 | 283.1 | 1 | 3.45x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x57` | 46,455 | 13,352.1 | 287.4 | 1 | 3.66x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x57` | 46,455 | 13,352.1 | 287.4 | -- | 287.4 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x61` | 49,715 | 13,895.5 | 279.5 | 166.7 | 287.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x62` | 50,530 | 13,982.6 | 276.7 | 154.7 | 287.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | 51,345 | 14,058.1 | 273.8 | 144.4 | 287.4 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x64` | 52,160 | 14,104.0 | 270.4 | 131.8 | 287.4 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 17,885.6 | 228.6 | 142.6 | 287.4 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x57` **<-- recommended** | 46,455 | 57 | 13,352.1 | 13,352 | 287.4 | 1 | `link_latency` | 2,929 | 219.4 | `b200_sxm-x29-nvl72-tensor` | 3.66x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x61` | 49,715 | 61 | 13,895.5 | 13,895 | 279.5 | 1 | `link_latency` | 3,169 | 228.0 | `b200_sxm-x31-nvl72-tensor` | 3.75x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x62` | 50,530 | 62 | 13,982.6 | 13,983 | 276.7 | 1 | `link_latency` | 3,287 | 235.1 | `b200_sxm-x32-nvl72-tensor` | 3.75x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | 51,345 | 63 | 14,058.1 | 14,058 | 273.8 | 1 | `link_latency` | 3,406 | 242.3 | `b200_sxm-x32-nvl72-tensor` | 3.77x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x64` | 52,160 | 64 | 14,104.0 | 14,104 | 270.4 | 1 | `link_latency` | 3,524 | 249.9 | `b200_sxm-x33-nvl72-tensor` | 3.75x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 96 | 17,885.6 | 429,255 | 228.6 | 53,789 | `compute` | 13,839 | 491.6 | `b200_sxm-x49-nvl72-tensor` | 4.40x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 348 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x57` | 46,455 | 13,352.1 | 287.4 | 1 |
| array | 348 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 17,885.6 | 228.6 | 53,789 |
| array | 348 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x54` | 44,010 | 12,460.6 | 283.1 | 1 |
| wafer | 80 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,807.9 | 125.6 | 1 |
| wafer | 80 | fastest | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,986.1 | 64.7 | 9,637 |
| wafer | 80 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,807.9 | 125.6 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 17,885.6 | 429,255 | 53,789 | 13,839 | 491.6 | `compute` | `b200_sxm-x49-nvl72-tensor` | 4,065.4 | 42,226 | 5,602.8 | 0.998 | 4.40x | 11.4x |
| 1 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,986.1 | 11,972 | 9,637 | 8,347 | 1,382.1 | `link_latency` | `b200_sxm-x58-nvl72-tensor` | 4,173.9 | 50,294 | 6,248.6 | 0.996 | 1.43x | 4.5x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 88,020 | 17,039.7 | 460,071 | 60,513 | 15,804 | 608.4 | `weight_read` | `b200_sxm-x55-nvl72-tensor` | 4,141.1 | 47,605 | 6,033.4 | 1.000 | 4.11x | 9.9x |
| 1 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,986.1 | -- | 9,637 | -- | 1,382.1 | -- | -- | -- | -- | -- | 0.952 | 0.35x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 17,885.6 | 429,255 | 53,789 | 13,839 | 251.9 | `compute` | `b200_sxm-x49-nvl72-tensor` | 3,804.6 | 42,226 | 3,184.0 | 0.998 | 4.70x | 12.6x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,986.1 | 11,972 | 9,637 | 8,347 | 697.2 | `link_latency` | `b200_sxm-x58-nvl72-tensor` | 3,933.1 | 50,294 | 3,511.2 | 0.996 | 1.52x | 5.0x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 88,020 | 17,039.7 | 460,071 | 60,513 | 15,804 | 310.4 | `weight_read` | `b200_sxm-x55-nvl72-tensor` | 3,894.1 | 47,605 | 3,402.2 | 1.000 | 4.38x | 11.0x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,986.1 | -- | 9,637 | -- | 697.2 | -- | -- | -- | -- | -- | 0.952 | 0.35x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 17,885.6 | 429,255 | 53,789 | 13,839 | 132.1 | `compute` | `b200_sxm-x49-nvl72-tensor` | 3,379.4 | 42,226 | 1,966.4 | 0.998 | 5.29x | 14.9x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 5,978.8 | 23,915 | 19,274 | 16,693 | 698.0 | `link_latency` | `b200_sxm-x116-nvl72-hybrid` | 3,895.4 | 102,291 | 3,536.2 | 0.996 | 1.53x | 5.1x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 176,040 | 16,612.5 | 897,078 | 121,027 | 29,852 | 295.9 | `compute` | `b200_sxm-x110-nvl72-hybrid` | 3,857.1 | 96,912 | 3,425.9 | 1.000 | 4.31x | 11.6x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 5,978.8 | -- | 19,274 | -- | 698.0 | -- | -- | -- | -- | -- | 0.952 | 0.36x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 17,885.6 | 429,255 | 53,789 | 13,839 | 72.2 | `compute` | `b200_sxm-x49-nvl72-tensor` | 2,781.4 | 42,226 | 1,341.7 | 0.998 | 6.43x | 18.6x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,964.3 | 47,714 | 38,549 | 33,385 | 699.7 | `link_latency` | `b200_sxm-x231-nvl72-hybrid` | 3,819.8 | 205,388 | 3,576.4 | 1.001 | 1.56x | 5.1x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | 17,885.6 | 429,255 | 53,789 | 13,839 | 42.2 | `compute` | `b200_sxm-x49-nvl72-tensor` | 2,094.6 | 42,226 | 999.8 | 0.998 | 8.54x | 23.7x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,915.6 | 94,649 | 57,824 | 50,297 | 531.4 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 3,671.5 | 309,382 | 2,825.0 | 0.999 | 1.61x | 5.3x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill` | 176,040 | 16,612.5 | 897,078 | 121,027 | 29,852 | 47.7 | `compute` | `b200_sxm-x110-nvl72-hybrid` | 2,185.1 | 96,912 | 1,038.7 | 1.000 | 7.60x | 21.8x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,782.4 | 185,037 | 57,824 | 51,160 | 276.5 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 3,184.1 | 309,382 | 1,797.0 | 0.999 | 1.82x | 6.5x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 16,612.5 | 1,412,067 | 190,505 | 46,989 | 40.2 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 1,926.1 | 153,392 | 948.7 | 1.001 | 8.63x | 23.6x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 5,568.7 | 1,264,095 | 19,274 | 31,910 | 58.3 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 1,589.9 | 102,291 | 811.8 | 0.996 | 3.50x | 13.9x |
| 64 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 15,175.5 | 971,235 | 127,190 | 31,440 | 32.4 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 1,589.9 | 102,291 | 811.8 | 0.997 | 9.54x | 25.1x |
| 64 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x4-romfill` | 184,900 | 5,568.7 | -- | 19,274 | -- | 58.3 | -- | -- | -- | -- | -- | 1.001 | 0.37x wafer/array | -- |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,666.3 | 1,706,574 | 190,505 | 47,554 | 27.9 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 926.6 | 153,392 | 537.8 | 1.001 | 7.19x | 17.6x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 369,800 | 5,568.7 | 2,528,190 | 38,549 | 63,820 | 35.3 | `compute` | `b200_sxm-x231-nvl72-hybrid` | 1,060.1 | 205,388 | 622.3 | 1.001 | 5.25x | 16.0x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 1,847.6 | 1,891,956 | 190,505 | 49,497 | 26.2 | `compute` | `b200_sxm-x173-expert` | 474.9 | 152,448 | 164.0 | 1.001 | 3.89x | 6.3x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 3,809.5 | 3,900,897 | 57,824 | 93,589 | 24.0 | `compute` | `b200_sxm-x347-expert` | 664.0 | 307,401 | 218.2 | 0.999 | 5.74x | 9.1x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 566.8 | 2,321,735 | 190,505 | 62,350 | 26.9 | `weight_read` | `b200_sxm-x173-expert` | 228.7 | 152,448 | 81.2 | 1.001 | 2.48x | 3.0x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,273.5 | 5,216,059 | 57,824 | 122,085 | 23.4 | `kv_read` | `b200_sxm-x347-expert` | 379.9 | 307,401 | 94.6 | 0.999 | 3.35x | 4.0x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x57` | 46,455 | array | SRAM | 1 |
| 2 | `ROM-N5-native-HBMKV-array-hw-tensor-x63` | 51,345 | array | HBM | 35,299 |
| 4-16 | `ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 78,240 | array | HBM | 53,789 |
| 32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 88,020 | array | HBM | 60,513 |
| 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 92,095 | array | HBM | 63,315 |
| 256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x162` | 132,030 | array | HBM | 90,770 |
| 1024 | `ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 138,550 | array | HBM | 95,252 |
| 4096 | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 185,005 | array | HBM | 127,190 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash-engram-host | HBM | rom | 57, 58, 63, 68, 78, 81, 90, 91, 108, 113, 162, 170, 216, 227, 340 |
| DeepSeek-V4.1-Flash-engram-host | HBM | sram | 57, 58, 63, 68, 78, 81, 96, 97, 108, 113, 162, 170, 216, 227, 340 |
| DeepSeek-V4.1-Flash-engram-host | SRAM | rom | 54, 57, 61, 62, 63, 64, 75, 100, 113, 150, 170, 200, 227, 340 |
| DeepSeek-V4.1-Flash-engram-host | SRAM | sram | 54, 57, 61, 62, 63, 64, 75, 100, 113, 150, 170, 200, 227, 340 |

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

- **300 of 5,112 feasible points (5.9%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 300.
- By area class: large array (5,000-40,000 mm2) 60, wafer (>=40,000 mm2) 240.
- By KV store: hbm 300.
- By batch: B=1 30, B=2 30, B=4 30, B=8 30, B=16 30, B=32 30, B=64 30, B=256 30, B=1024 30, B=4096 30.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 46% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 350 | 60 | 74.6% | 100.0% | 0.625 | 47% |
| gpu | wafer (>=40,000 mm2) | 1,530 | 240 | 52.8% | 100.0% | 0.625 | 66% |
| rom | large array (5,000-40,000 mm2) | 708 | 0 | 20.6% | 73.5% | 0.367 | 87% |
| rom | wafer (>=40,000 mm2) | 2,524 | 0 | 24.6% | 50.3% | 0.251 | 85% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x7-pipeline` | DeepSeek-V4.1-Flash-engram-host | 4096 | 11,200 | hbm | 1.087x | 7,000.0 / 7,000.0 W | 35% | 17.8 | 19.4 |
| `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x13-pipeline` | DeepSeek-V4.1-Flash-engram-host | 4096 | 20,800 | hbm | 1.068x | 13,000.0 / 13,000.0 W | 35% | 19.2 | 20.5 |
| `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x14-pipeline` | DeepSeek-V4.1-Flash-engram-host | 4096 | 22,400 | hbm | 1.067x | 14,000.0 / 14,000.0 W | 35% | 19.4 | 20.7 |
| `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x16-pipeline` | DeepSeek-V4.1-Flash-engram-host | 4096 | 25,600 | hbm | 1.065x | 16,000.0 / 16,000.0 W | 35% | 19.7 | 21.0 |
| `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x18-pipeline` | DeepSeek-V4.1-Flash-engram-host | 4096 | 28,800 | hbm | 1.062x | 18,000.0 / 18,000.0 W | 35% | 20.0 | 21.3 |
| `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x20-pipeline` | DeepSeek-V4.1-Flash-engram-host | 4096 | 32,000 | hbm | 1.060x | 20,000.0 / 20,000.0 W | 35% | 20.4 | 21.6 |
| `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x7-pipeline` | DeepSeek-V4.1-Flash-engram-host | 1024 | 11,200 | hbm | 1.060x | 7,000.0 / 7,000.0 W | 35% | 22.0 | 23.3 |
| `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-pipeline` | DeepSeek-V4.1-Flash-engram-host | 4096 | 44,800 | hbm | 1.056x | 28,000.0 / 28,000.0 W | 35% | 22.0 | 23.2 |
| `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-pipeline` | DeepSeek-V4.1-Flash-engram-host | 4096 | 46,400 | hbm | 1.056x | 29,000.0 / 29,000.0 W | 35% | 22.2 | 23.5 |
| `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x30-pipeline` | DeepSeek-V4.1-Flash-engram-host | 4096 | 48,000 | hbm | 1.056x | 30,000.0 / 30,000.0 W | 35% | 22.5 | 23.7 |
| `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x31-pipeline` | DeepSeek-V4.1-Flash-engram-host | 4096 | 49,600 | hbm | 1.055x | 31,000.0 / 31,000.0 W | 35% | 22.7 | 23.9 |
| `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x13-pipeline` | DeepSeek-V4.1-Flash-engram-host | 1024 | 20,800 | hbm | 1.055x | 13,000.0 / 13,000.0 W | 35% | 28.0 | 29.6 |

The worst point's dynamic energy is weight read 85.6%, kv read 10.6%, arithmetic 3.6%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4.1-Flash-engram-host | 1 | 78,240 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 0.491557 | 13,839.3 | compute | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-nvl72-tensor` | 5.602771 | 22,777.7 | link_latency | 11.40x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 78,240 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 0.251914 | 13,839.3 | compute | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-nvl72-tensor` | 3.184004 | 24,227.9 | link_latency | 12.64x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 78,240 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 0.132092 | 13,839.3 | compute | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-nvl72-tensor` | 1.966378 | 26,581.1 | link_latency | 14.89x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 78,240 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 0.072181 | 13,839.3 | compute | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-nvl72-tensor` | 1.341672 | 29,854.0 | link_latency | 18.59x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 78,240 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96` | 0.042225 | 13,839.3 | compute | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-nvl72-tensor` | 0.999768 | 33,505.6 | link_latency | 23.68x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 88,020 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 0.031405 | 16,318.7 | weight_read | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x55-nvl72-tensor` | 0.796694 | 39,951.4 | weight_read | 25.37x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 277,100 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.040170 | 46,989.4 | compute | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-nvl72-hybrid` | 0.948673 | 116,940.5 | link_latency | 23.62x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 277,100 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.027865 | 47,553.9 | compute | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-nvl72-hybrid` | 0.537843 | 127,586.4 | weight_read | 17.63x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 554,700 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.023992 | 93,588.7 | compute | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-expert` | 0.218206 | 148,371.1 | link_latency | 9.10x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 554,700 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x12` | 0.023406 | 122,085.4 | kv_read | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-expert` | 0.094635 | 147,244.6 | link_latency | 4.04x |

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
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 552 B | 307.5 GB | 4.46 | 0.047 GB | 0.181 GB | 278.7 |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 46,225 | 43,373.9 | wafer-pipeline | 5,807.9 | wafer-tensor | 7.47x | 8,345.7 | pipeline | 3,644.5 | tensor | 2.29x | 5.20x | 1.59x | 0.31x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 92,450 | 61,059.8 | wafer-pipeline | 5,986.1 | wafer-hybrid | 10.20x | 10,193.7 | pipeline | 4,173.9 | tensor | 2.44x | 5.99x | 1.43x | 0.24x |
| DeepSeek-V4.1-Flash-engram-host | 3 | 138,675 | 62,917.4 | wafer-pipeline | 5,982.4 | wafer-hybrid | 10.52x | 11,593.0 | pipeline | 3,945.6 | hybrid | 2.94x | 5.43x | 1.52x | 0.28x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 184,900 | 63,889.3 | wafer-pipeline | 5,978.8 | wafer-hybrid | 10.69x | 12,447.4 | pipeline | 4,135.2 | hybrid | 3.01x | 5.13x | 1.45x | 0.28x |
| DeepSeek-V4.1-Flash-engram-host | 6 | 277,350 | 64,891.7 | wafer-pipeline | 5,971.5 | wafer-hybrid | 10.87x | 13,425.3 | pipeline | 4,093.9 | hybrid | 3.28x | 4.83x | 1.46x | 0.30x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 369,800 | 65,404.7 | wafer-pipeline | 5,964.3 | wafer-hybrid | 10.97x | 13,986.8 | pipeline | 4,057.6 | hybrid | 3.45x | 4.68x | 1.47x | 0.31x |
| DeepSeek-V4.1-Flash-engram-host | 12 | 554,700 | 65,926.0 | wafer-pipeline | 5,949.8 | wafer-hybrid | 11.08x | 14,595.5 | pipeline | 4,118.5 | hybrid | 3.54x | 4.52x | 1.44x | 0.32x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.24x to 0.32x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash-engram-host | 1 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96 | 78,240 | 17,885.6 | 429,255.4 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-nvl72-tensor | 78,400 | 1.00x | tensor | 194.67 | 4,065.4 | 4,065.4 | link_latency | 4.40x | 18.60x | 37.97x | 4.40x |
| DeepSeek-V4.1-Flash-engram-host | 1 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x54 | 44,010 | 12,460.6 | 12,460.6 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-nvl72-tensor | 44,800 | 0.98x | tensor | 194.63 | 3,611.8 | 3,611.8 | link_latency | 3.45x | 0.94x | 26.45x | 3.45x |
| DeepSeek-V4.1-Flash-engram-host | 2 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96 | 78,240 | 17,885.6 | 429,255.4 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-nvl72-tensor | 78,400 | 1.00x | tensor | 197.35 | 3,804.6 | 7,609.3 | link_latency | 4.70x | 18.60x | 37.97x | 4.70x |
| DeepSeek-V4.1-Flash-engram-host | 2 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 5,505.4 | 11,010.9 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 197.27 | 3,322.3 | 6,644.7 | link_latency | 1.66x | 0.81x | 11.69x | 1.66x |
| DeepSeek-V4.1-Flash-engram-host | 4 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96 | 78,240 | 17,885.6 | 429,255.4 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-nvl72-tensor | 78,400 | 1.00x | tensor | 202.70 | 3,379.4 | 13,517.8 | link_latency | 5.29x | 18.60x | 37.97x | 5.29x |
| DeepSeek-V4.1-Flash-engram-host | 4 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 5,019.4 | 20,077.8 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 202.55 | 2,832.0 | 11,328.2 | link_latency | 1.77x | 1.47x | 10.66x | 1.77x |
| DeepSeek-V4.1-Flash-engram-host | 8 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96 | 78,240 | 17,885.6 | 429,255.4 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-nvl72-tensor | 78,400 | 1.00x | tensor | 213.40 | 2,781.4 | 22,251.3 | link_latency | 6.43x | 18.60x | 37.97x | 6.43x |
| DeepSeek-V4.1-Flash-engram-host | 8 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 4,266.2 | 34,129.8 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 213.09 | 2,207.2 | 17,657.4 | link_latency | 1.93x | 1.93x | 9.06x | 1.93x |
| DeepSeek-V4.1-Flash-engram-host | 16 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96 | 78,240 | 17,885.6 | 429,255.4 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-nvl72-tensor | 78,400 | 1.00x | tensor | 234.80 | 2,094.6 | 33,513.4 | link_latency | 8.54x | 12.81x | 37.97x | 8.54x |
| DeepSeek-V4.1-Flash-engram-host | 16 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 3,281.4 | 52,502.7 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 234.18 | 1,569.4 | 25,109.9 | weight_read | 2.09x | 2.09x | 6.97x | 2.09x |
| DeepSeek-V4.1-Flash-engram-host | 32 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x216-romfill | 176,040 | 16,612.5 | 897,077.6 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x110-nvl72-hybrid | 176,000 | 1.00x | hybrid | 240.39 | 2,185.1 | 69,923.7 | link_latency | 7.60x | 12.83x | 35.27x | 7.60x |
| DeepSeek-V4.1-Flash-engram-host | 32 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 2,245.0 | 71,839.0 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 276.37 | 1,051.8 | 33,657.4 | weight_read | 2.13x | 2.13x | 4.94x | 2.13x |
| DeepSeek-V4.1-Flash-engram-host | 64 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 16,612.5 | 1,412,066.5 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 262.24 | 1,926.1 | 123,267.4 | link_latency | 8.63x | 11.46x | 35.27x | 8.63x |
| DeepSeek-V4.1-Flash-engram-host | 64 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1,731.0 | 110,784.3 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 360.74 | 707.6 | 45,284.2 | weight_read | 2.45x | 2.45x | 5.20x | 2.45x |
| DeepSeek-V4.1-Flash-engram-host | 256 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,666.3 | 1,706,574.0 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 460.79 | 926.6 | 237,218.5 | weight_read | 7.19x | 7.19x | 16.50x | 7.19x |
| DeepSeek-V4.1-Flash-engram-host | 256 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 441.3 | 112,973.6 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 866.95 | 397.3 | 101,704.6 | weight_read | 1.11x | 1.11x | 3.34x | 1.11x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3,809.5 | 3,900,896.7 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-expert | 555,200 | 1.00x | expert | 701.40 | 664.0 | 679,957.6 | link_latency | 5.74x | 5.74x | 13.49x | 5.74x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 110.9 | 113,534.5 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 2,891.78 | 207.2 | 212,222.7 | link_latency | 0.53x | 0.53x | 2.42x | 0.53x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,273.5 | 5,216,059.4 | kv_read | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-expert | 555,200 | 1.00x | expert | 1,742.38 | 379.9 | 1,555,926.7 | link_latency | 3.35x | 3.35x | 12.06x | 3.35x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 27.8 | 113,675.6 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 3,273.91 | 91.1 | 373,140.2 | weight_read | 0.30x | 0.30x | 1.25x | 0.30x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-host | 7 | 11,200 | 194.34 | 194.34 | 2,027.8 | 2,027.8 |
| DeepSeek-V4.1-Flash-engram-host | 13 | 20,800 | 194.52 | 194.52 | 2,777.4 | 2,777.4 |
| DeepSeek-V4.1-Flash-engram-host | 14 | 22,400 | 194.54 | 194.54 | 2,865.6 | 2,865.6 |
| DeepSeek-V4.1-Flash-engram-host | 16 | 25,600 | 194.56 | 194.56 | 3,021.7 | 3,021.7 |
| DeepSeek-V4.1-Flash-engram-host | 18 | 28,800 | 194.58 | 194.58 | 3,155.3 | 3,155.3 |
| DeepSeek-V4.1-Flash-engram-host | 20 | 32,000 | 194.59 | 194.59 | 3,271.1 | 3,271.1 |
| DeepSeek-V4.1-Flash-engram-host | 28 | 44,800 | 194.63 | 194.63 | 3,611.8 | 3,611.8 |
| DeepSeek-V4.1-Flash-engram-host | 29 | 46,400 | 194.64 | 194.64 | 3,644.5 | 3,644.5 |
| DeepSeek-V4.1-Flash-engram-host | 30 | 48,000 | 194.64 | 194.64 | 3,675.6 | 3,675.6 |
| DeepSeek-V4.1-Flash-engram-host | 31 | 49,600 | 194.64 | 194.64 | 3,705.1 | 3,705.1 |
| DeepSeek-V4.1-Flash-engram-host | 32 | 51,200 | 194.65 | 194.65 | 3,733.3 | 3,733.3 |
| DeepSeek-V4.1-Flash-engram-host | 33 | 52,800 | 194.65 | 194.65 | 3,760.1 | 3,760.1 |
| DeepSeek-V4.1-Flash-engram-host | 35 | 56,000 | 194.65 | 194.65 | 3,810.2 | 3,810.2 |
| DeepSeek-V4.1-Flash-engram-host | 38 | 60,800 | 194.66 | 194.66 | 3,877.5 | 3,877.5 |
| DeepSeek-V4.1-Flash-engram-host | 40 | 64,000 | 194.66 | 194.66 | 3,917.8 | 3,917.8 |
| DeepSeek-V4.1-Flash-engram-host | 41 | 65,600 | 194.66 | 194.66 | 3,936.8 | 3,936.8 |
| DeepSeek-V4.1-Flash-engram-host | 46 | 73,600 | 194.67 | 194.67 | 4,021.5 | 4,021.5 |
| DeepSeek-V4.1-Flash-engram-host | 49 | 78,400 | 194.67 | 194.67 | 4,065.4 | 4,065.4 |
| DeepSeek-V4.1-Flash-engram-host | 51 | 81,600 | 194.68 | 194.68 | 4,092.3 | 4,092.3 |
| DeepSeek-V4.1-Flash-engram-host | 55 | 88,000 | 194.68 | 194.68 | 4,141.1 | 4,141.1 |
| DeepSeek-V4.1-Flash-engram-host | 58 | 92,800 | 194.68 | 194.68 | 4,173.9 | 4,173.9 |
| DeepSeek-V4.1-Flash-engram-host | 76 | 121,600 | 196.93 | 196.93 | 3,843.6 | 3,843.6 |
| DeepSeek-V4.1-Flash-engram-host | 83 | 132,800 | 196.93 | 196.93 | 3,911.1 | 3,911.1 |
| DeepSeek-V4.1-Flash-engram-host | 87 | 139,200 | 196.93 | 196.93 | 3,945.6 | 3,945.6 |
| DeepSeek-V4.1-Flash-engram-host | 102 | 163,200 | 196.93 | 196.93 | 4,055.0 | 4,055.0 |
| DeepSeek-V4.1-Flash-engram-host | 110 | 176,000 | 196.93 | 196.93 | 4,102.9 | 4,102.9 |
| DeepSeek-V4.1-Flash-engram-host | 116 | 185,600 | 196.93 | 196.93 | 4,135.2 | 4,135.2 |
| DeepSeek-V4.1-Flash-engram-host | 173 | 276,800 | 199.16 | 199.16 | 4,093.9 | 4,093.9 |
| DeepSeek-V4.1-Flash-engram-host | 231 | 369,600 | 201.40 | 201.40 | 4,057.6 | 4,057.6 |
| DeepSeek-V4.1-Flash-engram-host | 347 | 555,200 | 203.63 | 203.63 | 4,118.5 | 4,118.5 |

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
| DeepSeek-V4.1-Flash-engram-host | 7 | 11,200 | 471.0 | 2,027.8 | — | tensor | 194.34 | 39.4% | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 13 | 20,800 | 471.0 | 2,777.4 | 1,931.9 | tensor | 194.52 | 54.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 14 | 22,400 | 471.0 | 2,865.6 | 2,018.5 | tensor | 194.54 | 55.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 16 | 25,600 | 471.0 | 3,021.7 | 2,177.1 | tensor | 194.56 | 58.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 18 | 28,800 | 471.0 | 3,155.3 | 1,832.2 | tensor | 194.58 | 61.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 20 | 32,000 | 471.0 | 3,271.1 | 1,952.8 | tensor | 194.59 | 63.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 28 | 44,800 | 471.0 | 3,611.8 | 2,000.4 | tensor | 194.63 | 70.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 29 | 46,400 | 471.0 | 3,644.5 | 2,041.1 | tensor | 194.64 | 70.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 30 | 48,000 | 471.0 | 3,675.6 | 2,080.5 | tensor | 194.64 | 71.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 31 | 49,600 | 471.0 | 3,705.1 | 2,118.9 | tensor | 194.64 | 72.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 32 | 51,200 | 471.0 | 3,733.3 | 2,156.1 | tensor | 194.65 | 72.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 33 | 52,800 | 471.0 | 3,760.1 | 1,924.4 | tensor | 194.65 | 73.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 35 | 56,000 | 471.0 | 3,810.2 | 1,991.5 | tensor | 194.65 | 74.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 38 | 60,800 | 471.0 | 3,877.5 | 2,086.2 | tensor | 194.66 | 75.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 40 | 64,000 | 471.0 | 3,917.8 | 2,145.8 | tensor | 194.66 | 76.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 41 | 65,600 | 471.0 | 3,936.8 | 1,955.4 | tensor | 194.66 | 76.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 46 | 73,600 | 471.0 | 4,021.5 | 2,086.6 | tensor | 194.67 | 78.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 49 | 78,400 | 471.0 | 4,065.4 | 1,973.9 | tensor | 194.67 | 79.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 51 | 81,600 | 471.0 | 4,092.3 | 2,019.1 | tensor | 194.68 | 79.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 55 | 88,000 | 471.0 | 4,141.1 | 2,104.8 | tensor | 194.68 | 80.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 58 | 92,800 | 471.0 | 4,173.9 | 2,004.5 | tensor | 194.68 | 81.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 76 | 121,600 | 471.0 | 1,722.0 | 3,843.6 | hybrid | 196.93 | 75.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 83 | 132,800 | 471.0 | 1,728.7 | 3,911.1 | hybrid | 196.93 | 77.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 87 | 139,200 | 471.0 | 1,732.0 | 3,945.6 | hybrid | 196.93 | 77.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 102 | 163,200 | 471.0 | 1,742.4 | 4,055.0 | hybrid | 196.93 | 79.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 110 | 176,000 | 471.0 | 1,746.7 | 4,102.9 | hybrid | 196.93 | 80.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 116 | 185,600 | 471.0 | 1,749.6 | 4,135.2 | hybrid | 196.93 | 81.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 173 | 276,800 | 471.0 | 1,742.2 | 4,093.9 | hybrid | 199.16 | 81.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 231 | 369,600 | 471.0 | 1,738.7 | 4,057.6 | hybrid | 201.40 | 81.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 347 | 555,200 | 471.0 | 1,740.1 | 4,118.5 | hybrid | 203.63 | 83.9% | link_latency |

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
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x64 | DeepSeek-V4.1-Flash-engram-host | 64 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x61 | DeepSeek-V4.1-Flash-engram-host | 61 | tensor | rom_package_ucie | rom_board_serdes | 160 | 56.14 us | 1,781.2 tok/s | 17,812.4 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 16 on rom_board_serdes (traversals 6.6) = 54.08 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x64 | DeepSeek-V4.1-Flash-engram-host | 64 | hybrid | rom_package_ucie | rom_board_serdes | 95 | 3.65 us | 27,426.3 tok/s | 274,263.1 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.59 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-pipeline-x64 | DeepSeek-V4.1-Flash-engram-host | 64 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4.1-Flash-engram-host | 1 | pipeline | on_wafer_n5 | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-tensor-x54 | DeepSeek-V4.1-Flash-engram-host | 54 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4.1-Flash-engram-host | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 80 | 154.00 us | 649.4 tok/s | 6,493.5 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hybrid-x62 | DeepSeek-V4.1-Flash-engram-host | 62 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-pipeline-x97 | DeepSeek-V4.1-Flash-engram-host | 97 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-tensor-x63 | DeepSeek-V4.1-Flash-engram-host | 63 | tensor | rom_package_ucie | rom_board_serdes | 160 | 56.14 us | 1,781.2 tok/s | 17,812.4 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 16 on rom_board_serdes (traversals 6.6) = 54.08 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96 | DeepSeek-V4.1-Flash-engram-host | 96 | hybrid | rom_package_ucie | rom_board_serdes | 103 | 4.49 us | 22,263.6 tok/s | 222,635.6 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 23 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.43 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x97 | DeepSeek-V4.1-Flash-engram-host | 97 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash-engram-host | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-tensor-x58 | DeepSeek-V4.1-Flash-engram-host | 58 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4.1-Flash-engram-host | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 80 | 154.00 us | 649.4 tok/s | 6,493.5 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hybrid-x78 | DeepSeek-V4.1-Flash-engram-host | 78 | hybrid | nvlink5 | infiniband_ndr | 89 | 214.50 us | 466.2 tok/s | 4,661.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.11 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash-engram-host | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 81 | 154.10 us | 648.9 tok/s | 6,489.2 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x7-pipeline | DeepSeek-V4.1-Flash-engram-host | 7 | pipeline | nvlink5 | infiniband_ndr | 6 | 7.27 us | 13,758.4 tok/s | 137,584.4 tok/s | 6 x point_to_point span 2 on nvlink5 (traversals 1.0) = 7.27 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x7-tensor | DeepSeek-V4.1-Flash-engram-host | 7 | tensor | nvlink5 | infiniband_ndr | 80 | 194.34 us | 514.6 tok/s | 5,145.6 tok/s | 80 x all_reduce span 7 on nvlink5 (traversals 2.0) = 194.34 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x7-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 7 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.34 us | 514.6 tok/s | 5,145.6 tok/s | 80 x all_reduce span 7 on nvlink5_nvl72 (traversals 2.0) = 194.34 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x7-expert | DeepSeek-V4.1-Flash-engram-host | 7 | expert | nvlink5 | infiniband_ndr | 160 | 291.12 us | 343.5 tok/s | 3,435.0 tok/s | 80 x all_reduce span 7 on nvlink5 (traversals 2.0) = 194.34 us; 80 x point_to_point span 2 on nvlink5 (traversals 1.0) = 96.78 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x7-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 7 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 291.12 us | 343.5 tok/s | 3,435.0 tok/s | 80 x all_reduce span 7 on nvlink5_nvl72 (traversals 2.0) = 194.34 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.78 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x13-pipeline | DeepSeek-V4.1-Flash-engram-host | 13 | pipeline | nvlink5 | infiniband_ndr | 12 | 15.56 us | 6,426.8 tok/s | 64,267.5 tok/s | 11 x point_to_point span 2 on nvlink5 (traversals 1.0) = 13.33 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x13-tensor | DeepSeek-V4.1-Flash-engram-host | 13 | tensor | nvlink5 | infiniband_ndr | 160 | 543.77 us | 183.9 tok/s | 1,839.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x13-hybrid | DeepSeek-V4.1-Flash-engram-host | 13 | hybrid | nvlink5 | infiniband_ndr | 81 | 196.62 us | 508.6 tok/s | 5,085.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x13-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 13 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.52 us | 514.1 tok/s | 5,140.8 tok/s | 80 x all_reduce span 13 on nvlink5_nvl72 (traversals 2.0) = 194.52 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x13-expert | DeepSeek-V4.1-Flash-engram-host | 13 | expert | nvlink5 | infiniband_ndr | 160 | 364.35 us | 274.5 tok/s | 2,744.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 169.96 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x13-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 13 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.94 us | 343.7 tok/s | 3,437.1 tok/s | 80 x all_reduce span 13 on nvlink5_nvl72 (traversals 2.0) = 194.52 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.42 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x14-pipeline | DeepSeek-V4.1-Flash-engram-host | 14 | pipeline | nvlink5 | infiniband_ndr | 13 | 16.77 us | 5,962.6 tok/s | 59,625.6 tok/s | 12 x point_to_point span 2 on nvlink5 (traversals 1.0) = 14.54 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x14-tensor | DeepSeek-V4.1-Flash-engram-host | 14 | tensor | nvlink5 | infiniband_ndr | 160 | 543.77 us | 183.9 tok/s | 1,839.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x14-hybrid | DeepSeek-V4.1-Flash-engram-host | 14 | hybrid | nvlink5 | infiniband_ndr | 81 | 196.62 us | 508.6 tok/s | 5,085.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x14-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 14 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.54 us | 514.0 tok/s | 5,140.4 tok/s | 80 x all_reduce span 14 on nvlink5_nvl72 (traversals 2.0) = 194.54 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x14-expert | DeepSeek-V4.1-Flash-engram-host | 14 | expert | nvlink5 | infiniband_ndr | 160 | 363.81 us | 274.9 tok/s | 2,748.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 169.42 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x14-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 14 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.93 us | 343.7 tok/s | 3,437.3 tok/s | 80 x all_reduce span 14 on nvlink5_nvl72 (traversals 2.0) = 194.54 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.39 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x16-pipeline | DeepSeek-V4.1-Flash-engram-host | 16 | pipeline | nvlink5 | infiniband_ndr | 15 | 19.19 us | 5,209.9 tok/s | 52,099.4 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.96 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x16-tensor | DeepSeek-V4.1-Flash-engram-host | 16 | tensor | nvlink5 | infiniband_ndr | 160 | 543.77 us | 183.9 tok/s | 1,839.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x16-hybrid | DeepSeek-V4.1-Flash-engram-host | 16 | hybrid | nvlink5 | infiniband_ndr | 81 | 196.62 us | 508.6 tok/s | 5,085.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x16-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 16 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.56 us | 514.0 tok/s | 5,139.8 tok/s | 80 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 194.56 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x16-expert | DeepSeek-V4.1-Flash-engram-host | 16 | expert | nvlink5 | infiniband_ndr | 160 | 361.74 us | 276.4 tok/s | 2,764.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 193.19 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 168.54 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x16-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 16 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.90 us | 343.8 tok/s | 3,437.6 tok/s | 80 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 194.56 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.34 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x18-pipeline | DeepSeek-V4.1-Flash-engram-host | 18 | pipeline | nvlink5 | infiniband_ndr | 17 | 22.64 us | 4,416.9 tok/s | 44,169.1 tok/s | 15 x point_to_point span 2 on nvlink5 (traversals 1.0) = 18.17 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x18-tensor | DeepSeek-V4.1-Flash-engram-host | 18 | tensor | nvlink5 | infiniband_ndr | 160 | 551.96 us | 181.2 tok/s | 1,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x18-hybrid | DeepSeek-V4.1-Flash-engram-host | 18 | hybrid | nvlink5 | infiniband_ndr | 82 | 198.86 us | 502.9 tok/s | 5,028.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x18-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 18 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.58 us | 513.9 tok/s | 5,139.3 tok/s | 80 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 194.58 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x18-expert | DeepSeek-V4.1-Flash-engram-host | 18 | expert | nvlink5 | infiniband_ndr | 160 | 361.06 us | 277.0 tok/s | 2,769.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 193.19 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 167.86 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x18-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 18 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.88 us | 343.8 tok/s | 3,437.8 tok/s | 80 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 194.58 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.30 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x20-pipeline | DeepSeek-V4.1-Flash-engram-host | 20 | pipeline | nvlink5 | infiniband_ndr | 19 | 25.06 us | 3,989.9 tok/s | 39,899.4 tok/s | 17 x point_to_point span 2 on nvlink5 (traversals 1.0) = 20.59 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x20-tensor | DeepSeek-V4.1-Flash-engram-host | 20 | tensor | nvlink5 | infiniband_ndr | 160 | 551.96 us | 181.2 tok/s | 1,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x20-hybrid | DeepSeek-V4.1-Flash-engram-host | 20 | hybrid | nvlink5 | infiniband_ndr | 82 | 198.86 us | 502.9 tok/s | 5,028.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x20-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 20 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.59 us | 513.9 tok/s | 5,138.9 tok/s | 80 x all_reduce span 20 on nvlink5_nvl72 (traversals 2.0) = 194.59 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x20-expert | DeepSeek-V4.1-Flash-engram-host | 20 | expert | nvlink5 | infiniband_ndr | 160 | 360.51 us | 277.4 tok/s | 2,773.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 193.19 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 167.32 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x20-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 20 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.87 us | 343.8 tok/s | 3,438.0 tok/s | 80 x all_reduce span 20 on nvlink5_nvl72 (traversals 2.0) = 194.59 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.27 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-pipeline | DeepSeek-V4.1-Flash-engram-host | 28 | pipeline | nvlink5 | infiniband_ndr | 27 | 35.78 us | 2,795.1 tok/s | 27,950.6 tok/s | 24 x point_to_point span 2 on nvlink5 (traversals 1.0) = 29.07 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-tensor | DeepSeek-V4.1-Flash-engram-host | 28 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-hybrid | DeepSeek-V4.1-Flash-engram-host | 28 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 28 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.63 us | 513.8 tok/s | 5,137.9 tok/s | 80 x all_reduce span 28 on nvlink5_nvl72 (traversals 2.0) = 194.63 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-expert | DeepSeek-V4.1-Flash-engram-host | 28 | expert | nvlink5 | infiniband_ndr | 160 | 358.71 us | 278.8 tok/s | 2,787.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.91 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 28 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.83 us | 343.8 tok/s | 3,438.5 tok/s | 80 x all_reduce span 28 on nvlink5_nvl72 (traversals 2.0) = 194.63 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.20 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-pipeline | DeepSeek-V4.1-Flash-engram-host | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.99 us | 2,703.5 tok/s | 27,035.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.28 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-tensor | DeepSeek-V4.1-Flash-engram-host | 29 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-hybrid | DeepSeek-V4.1-Flash-engram-host | 29 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.64 us | 513.8 tok/s | 5,137.8 tok/s | 80 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 194.64 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-expert | DeepSeek-V4.1-Flash-engram-host | 29 | expert | nvlink5 | infiniband_ndr | 160 | 358.59 us | 278.9 tok/s | 2,788.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.79 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.8 tok/s | 3,438.5 tok/s | 80 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 194.64 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.19 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x30-pipeline | DeepSeek-V4.1-Flash-engram-host | 30 | pipeline | nvlink5 | infiniband_ndr | 29 | 38.20 us | 2,617.8 tok/s | 26,177.9 tok/s | 26 x point_to_point span 2 on nvlink5 (traversals 1.0) = 31.50 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x30-tensor | DeepSeek-V4.1-Flash-engram-host | 30 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x30-hybrid | DeepSeek-V4.1-Flash-engram-host | 30 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x30-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 30 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.64 us | 513.8 tok/s | 5,137.7 tok/s | 80 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 194.64 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x30-expert | DeepSeek-V4.1-Flash-engram-host | 30 | expert | nvlink5 | infiniband_ndr | 160 | 358.47 us | 279.0 tok/s | 2,789.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.68 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x30-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 30 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.9 tok/s | 3,438.5 tok/s | 80 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 194.64 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.18 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x31-pipeline | DeepSeek-V4.1-Flash-engram-host | 31 | pipeline | nvlink5 | infiniband_ndr | 30 | 39.41 us | 2,537.3 tok/s | 25,373.2 tok/s | 27 x point_to_point span 2 on nvlink5 (traversals 1.0) = 32.71 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x31-tensor | DeepSeek-V4.1-Flash-engram-host | 31 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x31-hybrid | DeepSeek-V4.1-Flash-engram-host | 31 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x31-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 31 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.64 us | 513.8 tok/s | 5,137.6 tok/s | 80 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 194.64 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x31-expert | DeepSeek-V4.1-Flash-engram-host | 31 | expert | nvlink5 | infiniband_ndr | 160 | 358.37 us | 279.0 tok/s | 2,790.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.57 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x31-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 31 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.9 tok/s | 3,438.6 tok/s | 80 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 194.64 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.18 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x32-pipeline | DeepSeek-V4.1-Flash-engram-host | 32 | pipeline | nvlink5 | infiniband_ndr | 31 | 40.62 us | 2,461.7 tok/s | 24,616.6 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.92 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x32-tensor | DeepSeek-V4.1-Flash-engram-host | 32 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x32-hybrid | DeepSeek-V4.1-Flash-engram-host | 32 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x32-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 32 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.65 us | 513.8 tok/s | 5,137.5 tok/s | 80 x all_reduce span 32 on nvlink5_nvl72 (traversals 2.0) = 194.65 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x32-expert | DeepSeek-V4.1-Flash-engram-host | 32 | expert | nvlink5 | infiniband_ndr | 160 | 358.07 us | 279.3 tok/s | 2,792.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.47 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x32-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 32 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.9 tok/s | 3,438.6 tok/s | 80 x all_reduce span 32 on nvlink5_nvl72 (traversals 2.0) = 194.65 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.17 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x33-pipeline | DeepSeek-V4.1-Flash-engram-host | 33 | pipeline | nvlink5 | infiniband_ndr | 32 | 42.86 us | 2,333.3 tok/s | 23,333.0 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.92 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x33-tensor | DeepSeek-V4.1-Flash-engram-host | 33 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x33-hybrid | DeepSeek-V4.1-Flash-engram-host | 33 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x33-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 33 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.65 us | 513.7 tok/s | 5,137.5 tok/s | 80 x all_reduce span 33 on nvlink5_nvl72 (traversals 2.0) = 194.65 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x33-expert | DeepSeek-V4.1-Flash-engram-host | 33 | expert | nvlink5 | infiniband_ndr | 160 | 357.98 us | 279.3 tok/s | 2,793.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.38 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x33-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 33 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.81 us | 343.9 tok/s | 3,438.6 tok/s | 80 x all_reduce span 33 on nvlink5_nvl72 (traversals 2.0) = 194.65 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.17 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x35-pipeline | DeepSeek-V4.1-Flash-engram-host | 35 | pipeline | nvlink5 | infiniband_ndr | 34 | 45.28 us | 2,208.5 tok/s | 22,084.5 tok/s | 30 x point_to_point span 2 on nvlink5 (traversals 1.0) = 36.34 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x35-tensor | DeepSeek-V4.1-Flash-engram-host | 35 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x35-hybrid | DeepSeek-V4.1-Flash-engram-host | 35 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x35-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 35 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.65 us | 513.7 tok/s | 5,137.4 tok/s | 80 x all_reduce span 35 on nvlink5_nvl72 (traversals 2.0) = 194.65 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x35-expert | DeepSeek-V4.1-Flash-engram-host | 35 | expert | nvlink5 | infiniband_ndr | 160 | 357.81 us | 279.5 tok/s | 2,794.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.21 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x35-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 35 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.81 us | 343.9 tok/s | 3,438.7 tok/s | 80 x all_reduce span 35 on nvlink5_nvl72 (traversals 2.0) = 194.65 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.16 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x38-pipeline | DeepSeek-V4.1-Flash-engram-host | 38 | pipeline | nvlink5 | infiniband_ndr | 37 | 48.91 us | 2,044.4 tok/s | 20,443.8 tok/s | 33 x point_to_point span 2 on nvlink5 (traversals 1.0) = 39.98 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x38-tensor | DeepSeek-V4.1-Flash-engram-host | 38 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x38-hybrid | DeepSeek-V4.1-Flash-engram-host | 38 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x38-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 38 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.66 us | 513.7 tok/s | 5,137.2 tok/s | 80 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 194.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x38-expert | DeepSeek-V4.1-Flash-engram-host | 38 | expert | nvlink5 | infiniband_ndr | 160 | 357.58 us | 279.7 tok/s | 2,796.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.99 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x38-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 38 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.80 us | 343.9 tok/s | 3,438.8 tok/s | 80 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 194.66 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.14 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x40-pipeline | DeepSeek-V4.1-Flash-engram-host | 40 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x40-tensor | DeepSeek-V4.1-Flash-engram-host | 40 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x40-hybrid | DeepSeek-V4.1-Flash-engram-host | 40 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x40-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 40 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.66 us | 513.7 tok/s | 5,137.1 tok/s | 80 x all_reduce span 40 on nvlink5_nvl72 (traversals 2.0) = 194.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x40-expert | DeepSeek-V4.1-Flash-engram-host | 40 | expert | nvlink5 | infiniband_ndr | 160 | 357.34 us | 279.8 tok/s | 2,798.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.86 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x40-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 40 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.80 us | 343.9 tok/s | 3,438.8 tok/s | 80 x all_reduce span 40 on nvlink5_nvl72 (traversals 2.0) = 194.66 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.14 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x41-pipeline | DeepSeek-V4.1-Flash-engram-host | 41 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x41-tensor | DeepSeek-V4.1-Flash-engram-host | 41 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x41-hybrid | DeepSeek-V4.1-Flash-engram-host | 41 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x41-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 41 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.66 us | 513.7 tok/s | 5,137.1 tok/s | 80 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 194.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x41-expert | DeepSeek-V4.1-Flash-engram-host | 41 | expert | nvlink5 | infiniband_ndr | 160 | 357.28 us | 279.9 tok/s | 2,799.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.80 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x41-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 41 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.80 us | 343.9 tok/s | 3,438.8 tok/s | 80 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 194.66 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.13 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x46-pipeline | DeepSeek-V4.1-Flash-engram-host | 46 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x46-tensor | DeepSeek-V4.1-Flash-engram-host | 46 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x46-hybrid | DeepSeek-V4.1-Flash-engram-host | 46 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x46-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 46 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.9 tok/s | 80 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x46-expert | DeepSeek-V4.1-Flash-engram-host | 46 | expert | nvlink5 | infiniband_ndr | 160 | 357.01 us | 280.1 tok/s | 2,801.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.54 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x46-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 46 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.12 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-pipeline | DeepSeek-V4.1-Flash-engram-host | 49 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-tensor | DeepSeek-V4.1-Flash-engram-host | 49 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-hybrid | DeepSeek-V4.1-Flash-engram-host | 49 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 49 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.8 tok/s | 80 x all_reduce span 49 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-expert | DeepSeek-V4.1-Flash-engram-host | 49 | expert | nvlink5 | infiniband_ndr | 160 | 356.80 us | 280.3 tok/s | 2,802.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.41 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x49-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 49 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 49 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.11 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x51-pipeline | DeepSeek-V4.1-Flash-engram-host | 51 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x51-tensor | DeepSeek-V4.1-Flash-engram-host | 51 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x51-hybrid | DeepSeek-V4.1-Flash-engram-host | 51 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x51-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 51 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.7 tok/s | 80 x all_reduce span 51 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x51-expert | DeepSeek-V4.1-Flash-engram-host | 51 | expert | nvlink5 | infiniband_ndr | 160 | 356.73 us | 280.3 tok/s | 2,803.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.33 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x51-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 51 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 51 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.11 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x55-pipeline | DeepSeek-V4.1-Flash-engram-host | 55 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x55-tensor | DeepSeek-V4.1-Flash-engram-host | 55 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x55-hybrid | DeepSeek-V4.1-Flash-engram-host | 55 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x55-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 55 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.6 tok/s | 80 x all_reduce span 55 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x55-expert | DeepSeek-V4.1-Flash-engram-host | 55 | expert | nvlink5 | infiniband_ndr | 160 | 356.59 us | 280.4 tok/s | 2,804.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.19 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x55-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 55 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 55 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.10 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-pipeline | DeepSeek-V4.1-Flash-engram-host | 58 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-tensor | DeepSeek-V4.1-Flash-engram-host | 58 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-hybrid | DeepSeek-V4.1-Flash-engram-host | 58 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.5 tok/s | 80 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-expert | DeepSeek-V4.1-Flash-engram-host | 58 | expert | nvlink5 | infiniband_ndr | 160 | 356.44 us | 280.6 tok/s | 2,805.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.34 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.09 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.09 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x76-pipeline | DeepSeek-V4.1-Flash-engram-host | 76 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x76-tensor | DeepSeek-V4.1-Flash-engram-host | 76 | tensor | nvlink5 | infiniband_ndr | 160 | 563.43 us | 177.5 tok/s | 1,774.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 369.04 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x76-hybrid | DeepSeek-V4.1-Flash-engram-host | 76 | hybrid | nvlink5 | infiniband_ndr | 89 | 214.50 us | 466.2 tok/s | 4,661.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.11 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x76-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 76 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x76-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-host | 76 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x76-expert | DeepSeek-V4.1-Flash-engram-host | 76 | expert | nvlink5 | infiniband_ndr | 160 | 355.96 us | 280.9 tok/s | 2,809.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.27 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.69 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x76-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 76 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.39 us | 279.0 tok/s | 2,790.3 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.69 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x83-pipeline | DeepSeek-V4.1-Flash-engram-host | 83 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x83-tensor | DeepSeek-V4.1-Flash-engram-host | 83 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x83-hybrid | DeepSeek-V4.1-Flash-engram-host | 83 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x83-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 83 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x83-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-host | 83 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x83-expert | DeepSeek-V4.1-Flash-engram-host | 83 | expert | nvlink5 | infiniband_ndr | 160 | 355.82 us | 281.0 tok/s | 2,810.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.58 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x83-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 83 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.28 us | 279.1 tok/s | 2,791.1 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.58 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x87-pipeline | DeepSeek-V4.1-Flash-engram-host | 87 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x87-tensor | DeepSeek-V4.1-Flash-engram-host | 87 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x87-hybrid | DeepSeek-V4.1-Flash-engram-host | 87 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x87-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-host | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x87-expert | DeepSeek-V4.1-Flash-engram-host | 87 | expert | nvlink5 | infiniband_ndr | 160 | 355.77 us | 281.1 tok/s | 2,810.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.53 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x87-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.22 us | 279.2 tok/s | 2,791.6 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.53 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x102-pipeline | DeepSeek-V4.1-Flash-engram-host | 102 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x102-tensor | DeepSeek-V4.1-Flash-engram-host | 102 | tensor | nvlink5 | infiniband_ndr | 160 | 564.56 us | 177.1 tok/s | 1,771.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 370.17 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x102-hybrid | DeepSeek-V4.1-Flash-engram-host | 102 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.21 us | 452.1 tok/s | 4,520.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 26.82 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x102-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 102 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x102-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-host | 102 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x102-expert | DeepSeek-V4.1-Flash-engram-host | 102 | expert | nvlink5 | infiniband_ndr | 160 | 355.56 us | 281.2 tok/s | 2,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.20 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.36 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x102-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 102 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.06 us | 279.3 tok/s | 2,792.9 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.36 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x110-pipeline | DeepSeek-V4.1-Flash-engram-host | 110 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x110-tensor | DeepSeek-V4.1-Flash-engram-host | 110 | tensor | nvlink5 | infiniband_ndr | 160 | 564.83 us | 177.0 tok/s | 1,770.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 370.44 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x110-hybrid | DeepSeek-V4.1-Flash-engram-host | 110 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.44 us | 447.5 tok/s | 4,475.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 29.05 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x110-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 110 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x110-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-host | 110 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x110-expert | DeepSeek-V4.1-Flash-engram-host | 110 | expert | nvlink5 | infiniband_ndr | 160 | 355.48 us | 281.3 tok/s | 2,813.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.18 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.29 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x110-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 110 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.99 us | 279.3 tok/s | 2,793.4 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.29 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x116-pipeline | DeepSeek-V4.1-Flash-engram-host | 116 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x116-tensor | DeepSeek-V4.1-Flash-engram-host | 116 | tensor | nvlink5 | infiniband_ndr | 160 | 565.06 us | 177.0 tok/s | 1,769.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 370.68 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x116-hybrid | DeepSeek-V4.1-Flash-engram-host | 116 | hybrid | nvlink5 | infiniband_ndr | 94 | 225.68 us | 443.1 tok/s | 4,431.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 31.29 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x116-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-host | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x116-expert | DeepSeek-V4.1-Flash-engram-host | 116 | expert | nvlink5 | infiniband_ndr | 160 | 355.42 us | 281.4 tok/s | 2,813.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.17 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.25 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x116-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.94 us | 279.4 tok/s | 2,793.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.25 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-pipeline | DeepSeek-V4.1-Flash-engram-host | 173 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-tensor | DeepSeek-V4.1-Flash-engram-host | 173 | tensor | nvlink5 | infiniband_ndr | 160 | 566.11 us | 176.6 tok/s | 1,766.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 371.72 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-hybrid | DeepSeek-V4.1-Flash-engram-host | 173 | hybrid | nvlink5 | infiniband_ndr | 101 | 241.32 us | 414.4 tok/s | 4,143.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.93 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-host | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-expert | DeepSeek-V4.1-Flash-engram-host | 173 | expert | nvlink5 | infiniband_ndr | 160 | 355.08 us | 281.6 tok/s | 2,816.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.11 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.97 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.31 us | 280.7 tok/s | 2,806.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.97 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x231-pipeline | DeepSeek-V4.1-Flash-engram-host | 231 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x231-tensor | DeepSeek-V4.1-Flash-engram-host | 231 | tensor | nvlink5 | infiniband_ndr | 160 | 566.65 us | 176.5 tok/s | 1,764.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 372.26 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x231-hybrid | DeepSeek-V4.1-Flash-engram-host | 231 | hybrid | nvlink5 | infiniband_ndr | 108 | 256.96 us | 389.2 tok/s | 3,891.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 62.57 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x231-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 556.36 us | 179.7 tok/s | 1,797.4 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-host | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 83 | 201.40 us | 496.5 tok/s | 4,965.3 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x231-expert | DeepSeek-V4.1-Flash-engram-host | 231 | expert | nvlink5 | infiniband_ndr | 160 | 354.91 us | 281.8 tok/s | 2,817.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.09 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.83 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x231-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.72 us | 281.1 tok/s | 2,811.2 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.90 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.83 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-pipeline | DeepSeek-V4.1-Flash-engram-host | 347 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-tensor | DeepSeek-V4.1-Flash-engram-host | 347 | tensor | nvlink5 | infiniband_ndr | 160 | 567.22 us | 176.3 tok/s | 1,763.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 372.83 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-hybrid | DeepSeek-V4.1-Flash-engram-host | 347 | hybrid | nvlink5 | infiniband_ndr | 119 | 281.55 us | 355.2 tok/s | 3,551.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 39 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 87.16 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-nvl72-tensor | DeepSeek-V4.1-Flash-engram-host | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 558.81 us | 179.0 tok/s | 1,789.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-host | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 84 | 203.63 us | 491.1 tok/s | 4,910.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-expert | DeepSeek-V4.1-Flash-engram-host | 347 | expert | nvlink5 | infiniband_ndr | 160 | 354.74 us | 281.9 tok/s | 2,819.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.06 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.68 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-nvl72-expert | DeepSeek-V4.1-Flash-engram-host | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.36 us | 281.4 tok/s | 2,814.1 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.67 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.68 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4.1-Flash-engram-host | 1 | array | array | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96 | 78,240 | 17,885.6 | 0.229 | 17,885.6 (78,240) | 5,807.9 (46,225) | 0.32x | compute |
| DeepSeek-V4.1-Flash-engram-host | 2 | array | array | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96 | 78,240 | 17,885.6 | 0.229 | 17,885.6 (78,240) | 5,986.1 (92,450) | 0.33x | compute |
| DeepSeek-V4.1-Flash-engram-host | 4 | array | array | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96 | 78,240 | 17,885.6 | 0.229 | 17,885.6 (78,240) | 5,934.4 (92,450) | 0.33x | compute |
| DeepSeek-V4.1-Flash-engram-host | 8 | array | array | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96 | 78,240 | 17,885.6 | 0.229 | 17,885.6 (78,240) | 5,785.4 (92,450) | 0.32x | compute |
| DeepSeek-V4.1-Flash-engram-host | 16 | array | array | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x96 | 78,240 | 17,885.6 | 0.229 | 17,885.6 (78,240) | 5,677.1 (138,675) | 0.32x | compute |
| DeepSeek-V4.1-Flash-engram-host | 32 | array | array | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x108 | 88,020 | 16,238.4 | 0.184 | 16,238.4 (88,020) | 5,546.3 (92,450) | 0.34x | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 64 | array | array | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 16,612.5 | 0.060 | 16,612.5 (277,100) | 5,546.3 (92,450) | 0.33x | compute |
| DeepSeek-V4.1-Flash-engram-host | 256 | array | array | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,666.3 | 0.024 | 6,666.3 (277,100) | 5,561.2 (277,350) | 0.83x | compute |
| DeepSeek-V4.1-Flash-engram-host | 1024 | wafer | array | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3,809.5 | 0.007 | 1,847.6 (277,100) | 3,809.5 (554,700) | 2.06x | compute |
| DeepSeek-V4.1-Flash-engram-host | 4096 | wafer | array | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,273.5 | 0.002 | 553.0 (185,005) | 1,273.5 (554,700) | 2.30x | kv_read |

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
| DeepSeek-V4.1-Flash-engram-host | 384 | 752.0 MB | 128.3 mm2 | 23.09 mm2 (18.0%) | 49,261 mm2 | 8,867 mm2 | 52,460 mm2 = 64.4 reticles |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | sram | 607,862.2 | 28,795.8 | 28,795.8 | 21.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 2 | sram | 607,862.2 | 28,795.8 | 28,795.8 | 21.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 4 | sram | 607,862.2 | 28,795.8 | 36,995.6 | 21.11x | 1.28x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 8 | sram | 607,862.2 | 28,795.8 | 58,749.1 | 21.11x | 2.04x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 16 | sram | 607,862.2 | 28,795.8 | 93,946.4 | 21.11x | 3.26x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 32 | sram | 607,862.2 | 28,795.8 | 137,559.1 | 21.11x | 4.78x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 64 | sram | 674,655.1 | 28,819.6 | 191,793.5 | 23.41x | 6.65x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 256 | sram | 1,271,077.0 | 28,965.6 | 472,336.4 | 43.88x | 16.31x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 1024 | sram | 2,414,298.6 | 29,002.3 | 562,306.5 | 83.24x | 19.39x | weight_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-host | 4096 | sram | 5,216,059.4 | 29,011.5 | 753,319.7 | 179.79x | 25.97x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 1 | rom | 3,792,284.8 | 63,427.3 | 63,427.3 | 59.79x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 2 | rom | 3,792,284.8 | 63,427.3 | 63,427.3 | 59.79x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 4 | rom | 3,792,284.8 | 63,427.3 | 63,427.3 | 59.79x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 8 | rom | 3,792,284.8 | 63,427.3 | 66,198.2 | 59.79x | 1.04x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 16 | rom | 3,792,284.8 | 63,427.3 | 105,959.6 | 59.79x | 1.67x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 32 | rom | 3,792,284.8 | 63,427.3 | 154,910.8 | 59.79x | 2.44x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 64 | rom | 3,792,284.8 | 63,542.7 | 239,149.1 | 59.68x | 3.76x | compute | weight_read | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 256 | rom | 3,792,284.8 | 64,257.0 | 442,671.8 | 59.02x | 6.89x | compute | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-host | 1024 | rom | 3,900,896.7 | 64,438.0 | 569,805.7 | 60.54x | 8.84x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 4096 | rom | 4,074,670.0 | 64,483.5 | 951,715.3 | 63.19x | 14.76x | compute | weight_read | weight_read |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 1 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 3,792,284.8 | 6.837 | compute | 6.24x |
| DeepSeek-V4.1-Flash-engram-host | 1 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 1 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-host | 1 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 1 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-host | 2 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 2 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 3,792,284.8 | 6.837 | compute | 6.24x |
| DeepSeek-V4.1-Flash-engram-host | 2 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 2 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-host | 2 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 2 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-host | 4 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 4 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 3,792,284.8 | 6.837 | compute | 6.24x |
| DeepSeek-V4.1-Flash-engram-host | 4 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 4 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-host | 4 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x26-perregion | 21,190 | 1.00 | 1.43 | 36,995.6 | 1.746 | weight_read | 0.06x |
| DeepSeek-V4.1-Flash-engram-host | 4 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-host | 8 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 8 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 3,792,284.8 | 6.837 | compute | 6.24x |
| DeepSeek-V4.1-Flash-engram-host | 8 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 8 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-host | 8 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x26-perregion | 21,190 | 1.00 | 1.99 | 58,749.1 | 2.772 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-host | 8 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-tensor-x35-perregion-romfill | 28,525 | 1.26 | 1.99 | 66,198.2 | 2.321 | weight_read | 0.11x |
| DeepSeek-V4.1-Flash-engram-host | 16 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 16 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 3,792,284.8 | 6.837 | compute | 6.24x |
| DeepSeek-V4.1-Flash-engram-host | 16 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 16 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-host | 16 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-tensor-x28-perregion | 22,820 | 1.00 | 2.54 | 93,946.4 | 4.117 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-host | 16 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-tensor-x35-perregion-romfill | 28,525 | 1.26 | 2.54 | 105,959.6 | 3.715 | weight_read | 0.17x |
| DeepSeek-V4.1-Flash-engram-host | 32 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 32 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 3,792,284.8 | 6.837 | compute | 6.24x |
| DeepSeek-V4.1-Flash-engram-host | 32 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 32 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 63,427.3 | 1.372 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-host | 32 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-tensor-x28-perregion | 22,820 | 1.00 | 3.49 | 137,559.1 | 6.028 | weight_read | 0.23x |
| DeepSeek-V4.1-Flash-engram-host | 32 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-tensor-x35-perregion-romfill | 28,525 | 1.26 | 3.49 | 154,910.8 | 5.431 | weight_read | 0.25x |
| DeepSeek-V4.1-Flash-engram-host | 64 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x113 | 92,095 | 1.00 | 1.00 | 674,655.1 | 7.326 | compute | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 64 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 3,792,284.8 | 6.837 | compute | 5.62x |
| DeepSeek-V4.1-Flash-engram-host | 64 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,819.6 | 0.623 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-host | 64 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.12 | 63,542.7 | 1.375 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash-engram-host | 64 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 4.92 | 191,793.5 | 4.149 | weight_read | 0.28x |
| DeepSeek-V4.1-Flash-engram-host | 64 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.22 | 4.92 | 239,149.1 | 5.174 | link_latency | 0.35x |
| DeepSeek-V4.1-Flash-engram-host | 256 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x162 | 132,030 | 1.00 | 1.00 | 1,271,077.0 | 9.627 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 256 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 3,792,284.8 | 6.837 | compute | 2.98x |
| DeepSeek-V4.1-Flash-engram-host | 256 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,965.6 | 0.627 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-host | 256 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 4.49 | 64,257.0 | 1.390 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash-engram-host | 256 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 10.96 | 472,336.4 | 10.218 | weight_read | 0.37x |
| DeepSeek-V4.1-Flash-engram-host | 256 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.22 | 10.96 | 442,671.8 | 9.576 | kv_read | 0.35x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 2,414,298.6 | 6.529 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 3,900,896.7 | 7.032 | compute | 1.62x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 17.96 | 29,002.3 | 0.627 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 17.96 | 64,438.0 | 1.394 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 28.90 | 562,306.5 | 12.165 | kv_read | 0.23x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x39-perregion-romfill | 31,785 | 1.40 | 6.34 | 569,805.7 | 17.927 | weight_read | 0.24x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 5,216,059.4 | 9.403 | kv_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 4,074,670.0 | 7.346 | compute | 0.78x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 71.86 | 29,011.5 | 0.628 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 71.86 | 64,483.5 | 1.395 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x28-perregion | 22,820 | 1.00 | 19.16 | 753,319.7 | 33.011 | weight_read | 0.14x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hw-hybrid-x39-perregion-romfill | 31,785 | 1.40 | 14.95 | 951,715.3 | 29.942 | weight_read | 0.18x |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 26 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 26 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 26 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 26 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 57 | 1.12 | 1.001 | 1.009 | 1.01x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 57 | 4.49 | 1.028 | 1.519 | 1.48x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 28 | 36.57 | 1.305 | 3.718 | 2.85x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 28 | 146.29 | 2.539 | 7.780 | 3.06x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-host | 1 | 7 | 4.22 | 2.86 | 1.47x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 7 | 5.88 | 3.47 | 1.69x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 7 | 6.81 | 4.08 | 1.67x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 7 | 6.99 | 4.64 | 1.51x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 7 | 7.00 | 5.12 | 1.37x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 7 | 7.00 | 5.49 | 1.27x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 7 | 7.00 | 5.76 | 1.22x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 7 | 7.00 | 5.97 | 1.17x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 7 | 7.00 | 5.98 | 1.17x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 7 | 7.00 | 5.98 | 1.17x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 13 | 4.96 | 3.49 | 1.42x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 13 | 7.99 | 4.49 | 1.78x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 13 | 11.01 | 5.61 | 1.96x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 13 | 12.66 | 6.75 | 1.87x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 13 | 12.99 | 7.82 | 1.66x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 13 | 13.00 | 8.72 | 1.49x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 13 | 13.00 | 9.39 | 1.38x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 13 | 13.00 | 9.95 | 1.31x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 13 | 13.00 | 9.97 | 1.30x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 13 | 13.00 | 9.97 | 1.30x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 14 | 8.21 | 4.62 | 1.78x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 14 | 11.54 | 5.81 | 1.99x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 14 | 13.52 | 7.04 | 1.92x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 14 | 13.98 | 8.20 | 1.71x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 14 | 14.00 | 9.19 | 1.52x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 14 | 14.00 | 9.93 | 1.41x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 14 | 14.00 | 10.55 | 1.33x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 14 | 14.00 | 10.57 | 1.32x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 14 | 14.00 | 10.57 | 1.32x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 16 | 8.58 | 4.84 | 1.77x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 16 | 12.48 | 6.17 | 2.02x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 16 | 15.15 | 7.57 | 2.00x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 16 | 15.94 | 8.91 | 1.79x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 16 | 16.00 | 10.08 | 1.59x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 16 | 16.00 | 10.97 | 1.46x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 16 | 16.00 | 11.71 | 1.37x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 16 | 16.00 | 11.74 | 1.36x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 16 | 16.00 | 11.74 | 1.36x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 18 | 8.89 | 5.04 | 1.76x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 18 | 13.29 | 6.50 | 2.04x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 18 | 16.66 | 8.05 | 2.07x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 18 | 17.86 | 9.57 | 1.87x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 18 | 18.00 | 10.92 | 1.65x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 18 | 18.00 | 11.95 | 1.51x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 18 | 18.00 | 12.83 | 1.40x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 18 | 18.00 | 12.86 | 1.40x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 18 | 18.00 | 12.86 | 1.40x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 20 | 9.14 | 5.21 | 1.75x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 20 | 13.99 | 6.79 | 2.06x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 20 | 18.06 | 8.50 | 2.12x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 20 | 19.75 | 10.19 | 1.94x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 20 | 19.99 | 11.71 | 1.71x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 20 | 20.00 | 12.89 | 1.55x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 20 | 20.00 | 13.90 | 1.44x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 20 | 20.00 | 13.93 | 1.44x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 20 | 20.00 | 13.93 | 1.44x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 28 | 9.84 | 5.77 | 1.70x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 28 | 16.06 | 7.76 | 2.07x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 28 | 22.64 | 10.00 | 2.26x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 28 | 26.75 | 12.33 | 2.17x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 28 | 27.89 | 14.50 | 1.92x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 28 | 28.00 | 16.26 | 1.72x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 28 | 28.00 | 17.80 | 1.57x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 28 | 28.00 | 17.86 | 1.57x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 28 | 28.00 | 17.86 | 1.57x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 29 | 9.90 | 5.83 | 1.70x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 29 | 16.26 | 7.87 | 2.07x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 29 | 23.12 | 10.16 | 2.27x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 29 | 27.56 | 12.57 | 2.19x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 29 | 28.86 | 14.82 | 1.95x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 29 | 28.99 | 16.64 | 1.74x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 29 | 29.00 | 18.25 | 1.59x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 30 | 9.96 | 5.89 | 1.69x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 30 | 16.45 | 7.97 | 2.06x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 30 | 23.58 | 10.32 | 2.28x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 30 | 28.35 | 12.80 | 2.22x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 30 | 29.83 | 15.13 | 1.97x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 30 | 29.99 | 17.02 | 1.76x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 30 | 30.00 | 18.69 | 1.60x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 30 | 30.00 | 18.76 | 1.60x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 30 | 30.00 | 18.76 | 1.60x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 31 | 10.02 | 5.94 | 1.69x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 31 | 16.63 | 8.07 | 2.06x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 31 | 24.02 | 10.47 | 2.29x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 31 | 29.12 | 13.02 | 2.24x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 31 | 30.79 | 15.43 | 2.00x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 31 | 30.99 | 17.39 | 1.78x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 31 | 31.00 | 19.13 | 1.62x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 31 | 31.00 | 19.20 | 1.61x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 31 | 31.00 | 19.20 | 1.61x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 32 | 10.07 | 6.00 | 1.68x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 32 | 16.80 | 8.16 | 2.06x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 32 | 24.44 | 10.62 | 2.30x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 32 | 29.88 | 13.24 | 2.26x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 32 | 31.74 | 15.73 | 2.02x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 32 | 31.99 | 17.76 | 1.80x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 32 | 32.00 | 19.56 | 1.64x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 32 | 32.00 | 19.64 | 1.63x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 32 | 32.00 | 19.64 | 1.63x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 33 | 5.56 | 4.41 | 1.26x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 33 | 10.12 | 6.05 | 1.67x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 33 | 16.96 | 8.25 | 2.06x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 33 | 24.85 | 10.77 | 2.31x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 33 | 30.63 | 13.46 | 2.28x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 33 | 32.69 | 16.02 | 2.04x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 33 | 32.98 | 18.12 | 1.82x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 33 | 33.00 | 19.99 | 1.65x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 33 | 33.00 | 20.06 | 1.64x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 33 | 33.00 | 20.06 | 1.64x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 35 | 5.59 | 4.47 | 1.25x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 35 | 10.22 | 6.15 | 1.66x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 35 | 17.26 | 8.43 | 2.05x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 35 | 25.63 | 11.05 | 2.32x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 35 | 32.07 | 13.87 | 2.31x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 35 | 34.57 | 16.58 | 2.08x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 35 | 34.97 | 18.82 | 1.86x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 35 | 35.00 | 20.82 | 1.68x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 35 | 35.00 | 20.90 | 1.67x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 35 | 35.00 | 20.90 | 1.67x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 38 | 10.34 | 6.29 | 1.64x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 38 | 17.66 | 8.67 | 2.04x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 38 | 26.69 | 11.45 | 2.33x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 38 | 34.12 | 14.46 | 2.36x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 38 | 37.34 | 17.39 | 2.15x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 38 | 37.94 | 19.83 | 1.91x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 38 | 38.00 | 22.03 | 1.72x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 38 | 38.00 | 22.12 | 1.72x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 38 | 38.00 | 22.12 | 1.72x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 40 | 10.41 | 6.38 | 1.63x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 40 | 17.91 | 8.83 | 2.03x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 40 | 27.35 | 11.70 | 2.34x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 40 | 35.41 | 14.84 | 2.39x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 40 | 39.15 | 17.91 | 2.19x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 40 | 39.92 | 20.48 | 1.95x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 40 | 40.00 | 22.81 | 1.75x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 40 | 40.00 | 22.90 | 1.75x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 40 | 40.00 | 22.90 | 1.75x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 41 | 10.44 | 6.42 | 1.63x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 41 | 18.02 | 8.90 | 2.02x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 41 | 27.65 | 11.82 | 2.34x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 41 | 36.04 | 15.02 | 2.40x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 41 | 40.04 | 18.16 | 2.20x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 41 | 40.90 | 20.80 | 1.97x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 41 | 41.00 | 23.19 | 1.77x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 41 | 41.00 | 23.29 | 1.76x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 41 | 41.00 | 23.29 | 1.76x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 46 | 10.59 | 6.62 | 1.60x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 46 | 18.52 | 9.24 | 2.00x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 46 | 29.06 | 12.38 | 2.35x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 46 | 38.98 | 15.89 | 2.45x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 46 | 44.37 | 19.37 | 2.29x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 46 | 45.78 | 22.32 | 2.05x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 46 | 45.99 | 25.03 | 1.84x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 46 | 45.99 | 25.14 | 1.83x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 46 | 45.99 | 25.14 | 1.83x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 49 | 5.70 | 4.77 | 1.20x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 49 | 10.67 | 6.73 | 1.58x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 49 | 18.78 | 9.43 | 1.99x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 49 | 29.81 | 12.70 | 2.35x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 49 | 40.60 | 16.37 | 2.48x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 49 | 46.87 | 20.05 | 2.34x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 49 | 48.68 | 23.19 | 2.10x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 49 | 48.98 | 26.09 | 1.88x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 49 | 48.98 | 26.21 | 1.87x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 49 | 48.98 | 26.21 | 1.87x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 51 | 5.71 | 4.80 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 51 | 10.71 | 6.80 | 1.57x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 51 | 18.94 | 9.55 | 1.98x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 51 | 30.27 | 12.89 | 2.35x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 51 | 41.62 | 16.68 | 2.50x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 51 | 48.49 | 20.48 | 2.37x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 51 | 50.59 | 23.75 | 2.13x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 51 | 50.97 | 26.77 | 1.90x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 51 | 50.97 | 26.90 | 1.90x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 51 | 50.97 | 26.90 | 1.90x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 55 | 10.79 | 6.94 | 1.56x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 55 | 19.23 | 9.76 | 1.97x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 55 | 31.11 | 13.27 | 2.34x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 55 | 43.55 | 17.27 | 2.52x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 55 | 51.62 | 21.32 | 2.42x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 55 | 54.37 | 24.83 | 2.19x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 55 | 54.95 | 28.10 | 1.96x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 55 | 54.95 | 28.23 | 1.95x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 55 | 54.95 | 28.23 | 1.95x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 76 | 11.09 | 7.54 | 1.47x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 76 | 20.29 | 10.66 | 1.90x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 76 | 34.38 | 14.92 | 2.30x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 76 | 51.52 | 19.89 | 2.59x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 76 | 65.85 | 25.12 | 2.62x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 76 | 72.99 | 29.79 | 2.45x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 76 | 75.49 | 34.28 | 2.20x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 76 | 75.53 | 34.47 | 2.19x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 76 | 75.53 | 34.47 | 2.19x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 83 | 11.15 | 7.71 | 1.45x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 83 | 20.53 | 10.90 | 1.88x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 83 | 35.16 | 15.38 | 2.29x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 83 | 53.57 | 20.63 | 2.60x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 83 | 69.85 | 26.20 | 2.67x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 83 | 78.68 | 31.24 | 2.52x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 83 | 82.14 | 36.11 | 2.27x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 83 | 82.21 | 36.31 | 2.26x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 83 | 82.21 | 36.31 | 2.26x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 87 | 11.19 | 7.80 | 1.44x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 87 | 20.65 | 11.02 | 1.87x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 87 | 35.56 | 15.63 | 2.27x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 87 | 54.63 | 21.03 | 2.60x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 87 | 71.99 | 26.79 | 2.69x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 87 | 81.81 | 32.02 | 2.55x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 87 | 85.89 | 37.11 | 2.31x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 102 | 5.85 | 5.30 | 1.11x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 102 | 11.29 | 8.10 | 1.39x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 102 | 21.04 | 11.44 | 1.84x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 102 | 36.82 | 16.50 | 2.23x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 102 | 58.08 | 22.40 | 2.59x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 102 | 79.19 | 28.83 | 2.75x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 102 | 92.77 | 34.76 | 2.67x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 102 | 99.52 | 40.62 | 2.45x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 102 | 99.68 | 40.86 | 2.44x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 102 | 99.68 | 40.86 | 2.44x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 110 | 11.33 | 8.24 | 1.37x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 110 | 21.20 | 11.65 | 1.82x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 110 | 37.37 | 16.92 | 2.21x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 110 | 59.63 | 23.06 | 2.59x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 110 | 82.55 | 29.82 | 2.77x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 110 | 98.14 | 36.10 | 2.72x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 110 | 106.49 | 42.35 | 2.51x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 110 | 106.70 | 42.61 | 2.50x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 110 | 106.70 | 42.61 | 2.50x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 116 | 11.36 | 8.35 | 1.36x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 116 | 21.31 | 11.79 | 1.81x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 116 | 37.74 | 17.21 | 2.19x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 116 | 60.68 | 23.52 | 2.58x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 116 | 84.89 | 30.52 | 2.78x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 116 | 101.95 | 37.06 | 2.75x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 116 | 111.57 | 43.59 | 2.56x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 173 | 11.54 | 9.09 | 1.27x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 173 | 21.98 | 12.94 | 1.70x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 173 | 40.08 | 19.31 | 2.08x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 173 | 67.63 | 26.93 | 2.51x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 173 | 101.33 | 35.95 | 2.82x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 173 | 130.91 | 44.63 | 2.93x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 173 | 153.57 | 53.58 | 2.87x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 231 | 11.63 | 9.58 | 1.21x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 231 | 22.34 | 13.86 | 1.61x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 231 | 41.34 | 20.63 | 2.00x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 231 | 71.61 | 29.55 | 2.42x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 231 | 111.55 | 40.16 | 2.78x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 231 | 150.80 | 50.51 | 2.99x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 231 | 186.03 | 61.46 | 3.03x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 347 | 11.72 | 10.18 | 1.15x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 347 | 22.70 | 15.30 | 1.48x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 347 | 42.66 | 22.28 | 1.92x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 347 | 75.90 | 33.59 | 2.26x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 347 | 123.23 | 45.96 | 2.68x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 347 | 175.33 | 59.00 | 2.97x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 347 | 230.16 | 73.28 | 3.14x |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 347 | 232.44 | 73.90 | 3.15x |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 347 | 232.44 | 73.90 | 3.15x |

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
| gpu | DeepSeek-V4.1-Flash-engram-host | 1 | 10.05 | 4.2% |
| rom | DeepSeek-V4.1-Flash-engram-host | 1 | 10.05 | 18.0% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash-engram-host | sram | interleaved | 128 B | 1.77x |
| DeepSeek-V4.1-Flash-engram-host | hbm | interleaved | 32 B | 1.34x |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 26 | 10.46% | 11.52 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 2 | 26 | 10.46% | 11.52 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 4 | 26 | 10.46% | 11.52 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 8 | 26 | 10.46% | 11.52 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 16 | 1 | 0.28% | 0.69 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 32 | 1 | 0.28% | 0.69 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 64 | 1 | 0.32% | 0.77 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 256 | 1 | 1.27% | 3.08 | 4.24 |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 1,937.4 | 110,433.9 |
| DeepSeek-V4.1-Flash-engram-host | 2 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 1,937.4 | 110,433.9 |
| DeepSeek-V4.1-Flash-engram-host | 4 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 1,937.4 | 110,433.9 |
| DeepSeek-V4.1-Flash-engram-host | 8 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 1,937.4 | 110,433.9 |
| DeepSeek-V4.1-Flash-engram-host | 16 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 1,937.4 | 110,433.9 |
| DeepSeek-V4.1-Flash-engram-host | 32 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 1,937.4 | 110,433.9 |
| DeepSeek-V4.1-Flash-engram-host | 64 | 1.75% | 13.6 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 1,731.0 | 110,784.3 |
| DeepSeek-V4.1-Flash-engram-host | 256 | 6.83% | 28.2 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 441.3 | 112,973.6 |
| DeepSeek-V4.1-Flash-engram-host | 1024 | 24.64% | 79.7 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 110.9 | 113,534.5 |
| DeepSeek-V4.1-Flash-engram-host | 4096 | 67.75% | 204.2 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 27.8 | 113,675.6 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | link_latency | 864 |
| gpu | thermal | 300 |
| gpu | weight_read | 716 |
| rom | compute | 1028 |
| rom | infeasible | 2528 |
| rom | kv_read | 85 |
| rom | link_latency | 1322 |
| rom | weight_read | 797 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2528 |

## Mechanical consistency audit

**FAIL** over 160,623 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x54', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x57', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x61', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x62', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x63', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x64', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x75', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x100', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x150', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x200', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x54', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x57', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x61', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x62', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x63', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x64', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x75', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x100', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x150', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x200', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x54', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x57', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x61', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x62', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x63', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x64', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x75', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x100', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x150', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x200', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-pipeline-x54', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-pipeline-x57', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-pipeline-x61', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-pipeline-x62', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-pipeline-x63', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-pipeline-x64', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-pipeline-x75', 'DeepSeek-V4.1-Flash-engram-host', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-pipeline-x100', 'DeepSeek-V4.1-Flash-engram-host', 1)

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

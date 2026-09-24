# Area-constrained roofline: n5_vs_b200

> Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 248x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 4 devices. On the GPU side the correction reaches 5x (b200_sxm-x1358-pipeline, 1,358 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 31 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Qwen3-8B takes 5 x 815 mm2 (4,075 mm2, array, KV in SRAM) at 9,333 tok/s per user and 2,290 tok/s per 1,000 mm2, holding 1 session, against 3 copies of one unified HBM die at the same silicon: 14.8x per user. DeepSeek-V4-Flash-0731 takes 30 x 815 mm2 (24,450 mm2, array, KV in SRAM) at 2,815 tok/s per user and 115 tok/s per 1,000 mm2, holding 1 session, against 15 copies of one unified HBM die at the same silicon: 4.8x per user. DeepSeek-V4-Pro-0813 takes 3 x 46,225 mm2 (138,675 mm2, wafer, KV in SRAM) at 1,220 tok/s per user and 9 tok/s per 1,000 mm2, holding 1 session, against 87 copies of one unified HBM die at the same silicon: 3.3x per user. Two granularities come out of one rule, which is the point: the class is chosen per model on evidence rather than assumed. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Qwen3-8B on 4,890 mm2 of ROM silicon at 9,934 tok/s per user against 4,800 mm2 of b200_sxm-x3-tensor at 631 tok/s: **15.7x**, ROM binding on `layer_fixed_latency` and the GPU on `weight_read`. It holds 1 resident session against the GPU cluster's 388. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 3.98x to it.** At 92,095 mm2 on Qwen3-8B the pipeline-only GPU delivers 318.73 tok/s and the same silicon running tensor delivers 1,269 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.00x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 4.71x (DeepSeek-V4-Flash-0731, ROM binding on `weight_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 2,592 to 258,510 tok/s, and its rate with every slot occupied from 145,176 to 258,510. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 56 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,393 us over NVLink, capping per-user decode at 718 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 396.7 us and cap it at 2,521 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 1.3x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 4 of 30 operating points and an array 26; on tokens per second per square millimetre the same points go 29 to the array and 1 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 392 of 8937 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 54.1x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 15.14x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.03x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 50 of 60 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 533 of 8,937 feasible points (6.0%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x147` at batch 4096 on 119,805 mm2, throttled 1.54x from 116 to 75 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 96% kv read against 0.0% weight read. The ROM sweep is not what melts it.


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

### Qwen3-8B at 8,192 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill`** -- 5 x 815 mm2 reticle dies, 4,075 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `rom`.

- **9,332.7 tok/s per user** (0.11 ms/token), binding on `layer_fixed_latency`
- **2,290.2 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 9,333 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 453 W at 0.111 W/mm2, 48.6 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 3 copies of one unified HBM die -- `b200_sxm-x3-tensor`, 4,800 mm2, area ratio 0.8490 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 4,075 | 4,800 | 0.8490 |
| user tok/s | 9,332.7 | 631.1 | 14.79x |
| aggregate tok/s | 9,333 | 631 | 9.62x |
| resident sessions | 1 | 388 | -- |
| J/token | 0.0486 | 3.3889 | 69.8x |

**The areas do not match exactly, and the mismatch is stated rather than rounded away.** A GPU cluster is quantised in whole dies and a ROM design is not, so at 4,075 mm2 the closest whole number of 1,600 mm2 dies is 3, i.e. 4,800 mm2. The ROM side is therefore compared against 18% MORE silicon than it has, which makes the ratio CONSERVATIVE for the ROM side.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 388 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x58-nvl72-tensor` at 92,800 mm2 and 1,268.9 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | 10,396.9 | 1,822.4 | 1 | 14.29x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 10,793.3 | 827.7 | 1 | 11.44x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | 9,332.7 | 2,290.2 | 1 | 14.79x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | 9,332.7 | 2,290.2 | 1 | 14.79x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | 9,332.7 | 2,290.2 | -- | 2,290.2 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x6-romfill` | 4,890 | 9,933.9 | 2,031.5 | 737.6 | 2,290.2 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | 10,396.9 | 1,822.4 | 652.9 | 2,290.2 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 10,760.9 | 1,650.5 | 584.2 | 2,290.2 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 10,793.3 | 827.7 | 162.9 | 2,290.2 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` **<-- recommended** | 4,075 | 5 | 9,332.7 | 9,333 | 2,290.2 | 1 | `layer_fixed_latency` | 453 | 48.6 | `b200_sxm-x3-tensor` | 14.79x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x6-romfill` | 4,890 | 6 | 9,933.9 | 9,934 | 2,031.5 | 1 | `layer_fixed_latency` | 531 | 53.4 | `b200_sxm-x3-tensor` | 15.74x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x7-romfill` | 5,705 | 7 | 10,396.9 | 10,397 | 1,822.4 | 1 | `layer_fixed_latency` | 607 | 58.3 | `b200_sxm-x4-tensor` | 14.29x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x8-romfill` | 6,520 | 8 | 10,760.9 | 10,761 | 1,650.5 | 1 | `layer_fixed_latency` | 681 | 63.3 | `b200_sxm-x4-tensor` | 14.79x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 16 | 10,793.3 | 10,793 | 827.7 | 1 | `layer_fixed_latency` | 1,238 | 114.7 | `b200_sxm-x8-tensor` | 11.44x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 257 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | 9,332.7 | 2,290.2 | 1 |
| array | 257 | fastest | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 10,793.3 | 827.7 | 1 |
| array | 257 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | 9,332.7 | 2,290.2 | 1 |
| wafer | 58 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,904.9 | 106.1 | 1 |
| wafer | 58 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,080.9 | 55.0 | 1 |
| wafer | 58 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,904.9 | 106.1 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | 13,040 | 10,793.3 | 10,793 | 1 | 1,238 | 114.7 | `layer_fixed_latency` | `b200_sxm-x8-tensor` | 943.8 | 1,059 | 4,693.6 | 1.019 | 11.44x | 40.9x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,080.9 | 5,081 | 1 | 7,946 | 1,563.9 | `link_latency` | `b200_sxm-x58-nvl72-tensor` | 1,268.9 | 7,764 | 17,740.8 | 0.996 | 4.00x | 11.3x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 92,095 | 9,685.1 | 77,481 | 9,471 | 20,448 | 1,154.6 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 1,268.9 | 7,764 | 17,740.8 | 0.992 | 7.63x | 15.4x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,080.9 | -- | 1 | -- | 1,563.9 | -- | -- | -- | -- | -- | 0.996 | 0.52x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 50,530 | 9,880.7 | 39,523 | 5,196 | 10,811 | 410.4 | `layer_fixed_latency` | `b200_sxm-x32-nvl72-tensor` | 1,202.3 | 4,277 | 5,591.0 | 0.987 | 8.22x | 13.6x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,545.7 | 50,003 | 4,325 | 31,433 | 2,842.4 | `link_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,258.3 | 23,187 | 25,814.0 | 1.002 | 3.61x | 9.1x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,672.8 | 212,803 | 28,498 | 58,748 | 1,670.0 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,258.3 | 23,187 | 25,814.0 | 1.001 | 7.69x | 15.5x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,545.7 | -- | 4,325 | -- | 2,842.4 | -- | -- | -- | -- | -- | 0.999 | 0.47x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill` | 50,530 | 9,880.7 | 39,523 | 5,196 | 10,811 | 273.5 | `layer_fixed_latency` | `b200_sxm-x32-nvl72-tensor` | 1,178.6 | 4,277 | 2,908.4 | 0.987 | 8.38x | 10.6x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,545.7 | 50,003 | 4,325 | 31,433 | 1,489.6 | `link_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,255.0 | 23,187 | 13,401.8 | 1.002 | 3.62x | 9.0x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,672.8 | 212,803 | 28,498 | 58,748 | 903.3 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,255.0 | 23,187 | 13,401.8 | 1.001 | 7.71x | 14.8x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,545.7 | -- | 4,325 | -- | 1,489.6 | -- | -- | -- | -- | -- | 0.999 | 0.47x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 9,796.1 | 107,757 | 14,249 | 29,559 | 325.9 | `layer_fixed_latency` | `b200_sxm-x87-nvl72-hybrid` | 1,207.9 | 11,654 | 3,684.8 | 0.995 | 8.11x | 11.3x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,545.7 | 50,003 | 4,325 | 31,433 | 813.1 | `link_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,242.3 | 23,187 | 6,828.9 | 1.002 | 3.66x | 8.4x |
| 8 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,672.8 | 212,803 | 28,498 | 58,748 | 520.0 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,242.3 | 23,187 | 6,828.9 | 1.001 | 7.79x | 13.1x |
| 8 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 4,545.7 | -- | 4,325 | -- | 813.1 | -- | -- | -- | -- | -- | 0.999 | 0.47x wafer/array | -- |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 9,672.8 | 212,803 | 28,498 | 58,748 | 328.3 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,217.5 | 23,187 | 3,542.5 | 1.001 | 7.94x | 10.8x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,521.9 | 99,481 | 8,650 | 62,795 | 816.7 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 1,242.6 | 46,522 | 6,745.6 | 0.999 | 3.64x | 8.3x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 8,789.7 | 377,957 | 28,498 | 81,319 | 242.1 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,170.8 | 23,187 | 1,899.3 | 1.001 | 7.51x | 7.8x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,937.8 | 169,327 | 8,650 | 72,341 | 527.1 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 1,214.0 | 46,522 | 3,510.9 | 0.999 | 3.24x | 6.7x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 7,163.6 | 458,470 | 28,498 | 91,617 | 199.8 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,087.4 | 23,187 | 1,077.7 | 1.001 | 6.59x | 5.4x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,112.9 | 199,225 | 8,650 | 76,120 | 382.1 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 1,160.5 | 46,522 | 1,893.5 | 0.999 | 2.68x | 5.0x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 3,148.4 | 805,998 | 28,498 | 138,550 | 171.9 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 811.6 | 23,187 | 461.1 | 1.001 | 3.88x | 2.7x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,209.8 | 309,706 | 8,650 | 91,044 | 294.0 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 951.5 | 46,522 | 699.6 | 0.999 | 1.27x | 2.4x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 801.0 | 820,187 | 28,498 | 138,550 | 168.9 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 439.4 | 23,187 | 283.8 | 1.001 | 1.82x | 1.7x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 330.9 | 338,841 | 8,650 | 94,976 | 280.3 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 613.1 | 46,522 | 359.8 | 0.999 | 0.54x | 1.3x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 201.1 | 823,812 | 28,498 | 138,550 | 168.2 | `thermal` | `b200_sxm-x173-nvl72-hybrid` | 166.6 | 23,187 | 229.4 | 1.001 | 1.21x | 1.4x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 84.0 | 344,035 | 8,650 | 94,873 | 275.8 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 280.0 | 46,522 | 255.1 | 0.999 | 0.30x | 0.9x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 4,075 | array | SRAM | 1 |
| 2-4096 | `ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill` | 39,935 | array | HBM | 4,107 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Flash-0731 at 200,000 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-hybrid-x30`** -- 30 x 815 mm2 reticle dies, 24,450 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **2,815.4 tok/s per user** (0.36 ms/token), binding on `layer_fixed_latency`
- **115.2 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 2,815 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 1,518 W at 0.062 W/mm2, 539.2 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 15 copies of one unified HBM die -- `b200_sxm-x15-hybrid`, 24,000 mm2, area ratio 1.0188 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 24,450 | 24,000 | 1.0188 |
| user tok/s | 2,815.4 | 584.6 | 4.82x |
| aggregate tok/s | 2,815 | 1,169 | 0.48x |
| resident sessions | 1 | 1,637 | -- |
| J/token | 0.5392 | 10.2073 | 18.9x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 1,637 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x58-nvl72-tensor` at 92,800 mm2 and 607.7 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-hybrid-x42` | 34,230 | 3,247.3 | 94.9 | 1 | 5.47x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 45,640 | 3,374.2 | 73.9 | 1 | 5.63x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-hybrid-x29` | 23,635 | 2,558.9 | 108.3 | 1 | 4.38x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-hybrid-x30` | 24,450 | 2,815.4 | 115.2 | 1 | 4.82x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x30` | 24,450 | 2,815.4 | 115.2 | -- | 115.2 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x35` | 28,525 | 3,084.3 | 108.1 | 66.0 | 115.2 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x37` | 30,155 | 3,156.5 | 104.7 | 59.8 | 115.2 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x42` | 34,230 | 3,247.3 | 94.9 | 44.2 | 115.2 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x43-romfill` | 35,045 | 3,270.8 | 93.3 | 43.0 | 115.2 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x45-romfill` | 36,675 | 3,280.0 | 89.4 | 38.0 | 115.2 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x48` | 39,120 | 3,330.1 | 85.1 | 35.1 | 115.2 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x55` | 44,825 | 3,364.9 | 75.1 | 27.0 | 115.2 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 45,640 | 3,374.2 | 73.9 | 26.4 | 115.2 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x30` **<-- recommended** | 24,450 | 30 | 2,815.4 | 2,815 | 115.2 | 1 | `layer_fixed_latency` | 1,518 | 539.2 | `b200_sxm-x15-hybrid` | 4.82x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x35` | 28,525 | 35 | 3,084.3 | 3,084 | 108.1 | 1 | `layer_fixed_latency` | 1,877 | 608.5 | `b200_sxm-x18-nvl72-tensor` | 5.23x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x37` | 30,155 | 37 | 3,156.5 | 3,157 | 104.7 | 1 | `layer_fixed_latency` | 2,113 | 669.6 | `b200_sxm-x19-nvl72-tensor` | 5.34x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x42` | 34,230 | 42 | 3,247.3 | 3,247 | 94.9 | 1 | `layer_fixed_latency` | 2,705 | 833.0 | `b200_sxm-x21-nvl72-tensor` | 5.47x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x43-romfill` | 35,045 | 43 | 3,270.8 | 3,271 | 93.3 | 1 | `layer_fixed_latency` | 2,823 | 863.2 | `b200_sxm-x22-nvl72-tensor` | 5.50x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x45-romfill` | 36,675 | 45 | 3,280.0 | 3,280 | 89.4 | 1 | `layer_fixed_latency` | 3,060 | 932.8 | `b200_sxm-x23-nvl72-tensor` | 5.51x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x48` | 39,120 | 48 | 3,330.1 | 3,330 | 85.1 | 1 | `layer_fixed_latency` | 3,414 | 1,025.3 | `b200_sxm-x24-nvl72-tensor` | 5.59x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x55` | 44,825 | 55 | 3,364.9 | 3,365 | 75.1 | 1 | `layer_fixed_latency` | 4,242 | 1,260.7 | `b200_sxm-x28-nvl72-tensor` | 5.62x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 45,640 | 56 | 3,374.2 | 3,374 | 73.9 | 1 | `layer_fixed_latency` | 4,360 | 1,292.2 | `b200_sxm-x29-nvl72-tensor` | 5.63x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 318 | densest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x30` | 24,450 | 2,815.4 | 115.2 | 1 |
| array | 318 | fastest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 45,640 | 3,374.2 | 73.9 | 1 |
| array | 318 | smallest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x29` | 23,635 | 2,558.9 | 108.3 | 1 |
| wafer | 58 | densest | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 46,225 | 2,786.2 | 60.3 | 1 |
| wafer | 58 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 2,899.9 | 31.4 | 1 |
| wafer | 58 | smallest | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 46,225 | 2,786.2 | 60.3 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 45,640 | 3,374.2 | 3,374 | 1 | 4,360 | 1,292.2 | `layer_fixed_latency` | `b200_sxm-x29-nvl72-tensor` | 599.7 | 3,279 | 18,161.2 | 0.984 | 5.63x | 14.1x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 2,899.9 | 2,900 | 1 | 11,145 | 3,843.1 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 607.7 | 6,679 | 34,659.8 | 0.996 | 4.77x | 9.0x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x112-romfill` | 91,280 | 3,279.2 | 91,817 | 8,207 | 13,340 | 3,018.7 | `layer_fixed_latency` | `b200_sxm-x57-nvl72-tensor` | 607.6 | 6,562 | 34,089.9 | 1.001 | 5.40x | 11.3x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 2,899.9 | -- | 1 | -- | 3,843.1 | -- | -- | -- | -- | -- | 0.987 | 0.88x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 48,900 | 3,373.9 | 50,608 | 4,396 | 7,664 | 883.1 | `layer_fixed_latency` | `b200_sxm-x31-hybrid` | 585.0 | 3,514 | 10,500.4 | 0.986 | 5.77x | 11.6x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 2,543.0 | 144,953 | 5,041 | 38,434 | 6,487.7 | `layer_fixed_latency` | `b200_sxm-x231-nvl72-hybrid` | 603.8 | 26,964 | 68,255.8 | 1.001 | 4.21x | 10.5x |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 48,900 | 3,373.9 | 50,608 | 4,396 | 7,664 | 461.0 | `layer_fixed_latency` | `b200_sxm-x31-hybrid` | 585.0 | 3,514 | 5,857.8 | 0.986 | 5.77x | 12.4x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 2,543.0 | 144,953 | 5,041 | 38,434 | 3,263.3 | `layer_fixed_latency` | `b200_sxm-x231-nvl72-hybrid` | 603.8 | 26,964 | 34,735.5 | 1.001 | 4.21x | 10.6x |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x60` | 48,900 | 3,373.9 | 50,608 | 4,396 | 7,664 | 249.9 | `layer_fixed_latency` | `b200_sxm-x31-hybrid` | 547.7 | 3,514 | 3,282.0 | 0.986 | 6.16x | 13.1x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 2,543.0 | 144,953 | 5,041 | 38,434 | 1,651.1 | `layer_fixed_latency` | `b200_sxm-x231-nvl72-hybrid` | 594.1 | 26,964 | 18,247.3 | 1.001 | 4.28x | 11.1x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 57,050 | 3,362.0 | 60,515 | 5,129 | 9,371 | 169.3 | `layer_fixed_latency` | `b200_sxm-x36-hybrid` | 501.7 | 4,100 | 2,216.3 | 0.990 | 6.70x | 13.1x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 2,543.0 | 144,953 | 5,041 | 38,434 | 845.0 | `layer_fixed_latency` | `b200_sxm-x231-nvl72-hybrid` | 576.4 | 26,964 | 9,993.3 | 1.001 | 4.41x | 11.8x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill` | 136,920 | 3,253.3 | 136,641 | 12,311 | 19,969 | 179.7 | `layer_fixed_latency` | `b200_sxm-x86-nvl72-hybrid` | 517.7 | 9,962 | 2,490.4 | 0.995 | 6.28x | 13.9x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 2,543.0 | 144,953 | 5,041 | 38,434 | 441.9 | `layer_fixed_latency` | `b200_sxm-x231-nvl72-hybrid` | 572.4 | 26,964 | 5,557.6 | 1.001 | 4.44x | 12.6x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 3,251.5 | 276,379 | 24,915 | 40,406 | 181.4 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 513.7 | 20,163 | 2,515.3 | 1.001 | 6.33x | 13.9x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,541.0 | 218,528 | 7,562 | 57,693 | 341.4 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 552.7 | 40,565 | 4,395.5 | 0.999 | 4.60x | 12.9x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 2,536.0 | 649,222 | 24,915 | 54,370 | 83.7 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 364.6 | 20,163 | 1,168.7 | 1.001 | 6.96x | 14.0x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,071.6 | 530,319 | 7,562 | 69,385 | 130.8 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 442.1 | 40,565 | 1,742.5 | 0.999 | 4.69x | 13.3x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 1,134.8 | 1,162,030 | 24,915 | 72,934 | 62.8 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 197.9 | 20,163 | 724.8 | 1.001 | 5.73x | 11.5x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,018.1 | 1,042,528 | 7,562 | 88,875 | 85.2 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 275.2 | 40,565 | 857.2 | 0.999 | 3.70x | 10.1x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 344.7 | 1,411,894 | 24,915 | 93,658 | 66.3 | `weight_read` | `b200_sxm-x173-nvl72-hybrid` | 87.7 | 20,163 | 443.3 | 1.001 | 3.93x | 6.7x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 295.8 | 1,211,780 | 7,562 | 93,794 | 77.4 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 132.3 | 40,565 | 576.3 | 0.999 | 2.24x | 7.4x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x30` | 24,450 | array | SRAM | 1 |
| 2-32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x56` | 45,640 | array | HBM | 4,103 |
| 64 | `ROM-N5-native-HBMKV-array-hw-pipeline-x56` | 45,640 | array | HBM | 4,103 |
| 256 | `ROM-N5-native-HBMKV-array-hw-pipeline-x84` | 68,460 | array | HBM | 6,155 |
| 1024 | `ROM-N5-native-HBMKV-array-hw-pipeline-x113` | 92,095 | array | HBM | 8,280 |
| 4096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x168` | 136,920 | array | HBM | 12,311 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Pro-0813 at 1,000,000 tokens

**Recommended: `ROM-N5-native-SRAMKV-wafer-hybrid-x3`** -- 3 x 46,225 mm2 wafers, 138,675 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **1,220.4 tok/s per user** (0.82 ms/token), binding on `layer_fixed_latency`
- **8.8 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 1,220 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 7,871 W at 0.057 W/mm2, 6,449.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 87 copies of one unified HBM die -- `b200_sxm-x87-nvl72-hybrid`, 139,200 mm2, area ratio 0.9962 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 138,675 | 139,200 | 0.9962 |
| user tok/s | 1,220.4 | 372.9 | 3.27x |
| aggregate tok/s | 1,220 | 746 | 0.11x |
| resident sessions | 1 | 1,339 | -- |
| J/token | 6.4493 | 86.1872 | 13.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 1,339 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x144-nvl72-hybrid` at 230,400 mm2 and 379.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-hybrid-x5` | 231,125 | 1,509.5 | 6.5 | 1 | 3.98x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 1,539.2 | 5.5 | 1 | 4.09x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x150` | 122,250 | 814.8 | 6.7 | 1 | 2.20x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 1,220.4 | 8.8 | 1 | 3.27x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 1,220.4 | 8.8 | -- | 8.8 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x184` | 149,960 | 1,300.3 | 8.7 | 7.1 | 8.8 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x217-romfill` | 176,855 | 1,396.6 | 7.9 | 4.6 | 8.8 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x218` | 177,670 | 1,398.6 | 7.9 | 4.6 | 8.8 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x219-romfill` | 178,485 | 1,400.4 | 7.8 | 4.5 | 8.8 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x221` | 180,115 | 1,404.0 | 7.8 | 4.4 | 8.8 | stop |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 1,423.8 | 7.7 | 4.4 | 8.8 | stop |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x5` | 231,125 | 1,509.5 | 6.5 | 3.1 | 8.8 | stop |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 1,539.2 | 5.5 | 2.3 | 8.8 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x3` **<-- recommended** | 138,675 | 3 | 1,220.4 | 1,220 | 8.8 | 1 | `layer_fixed_latency` | 7,871 | 6,449.3 | `b200_sxm-x87-nvl72-hybrid` | 3.27x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x184` | 149,960 | 184 | 1,300.3 | 1,300 | 8.7 | 1 | `layer_fixed_latency` | 9,510 | 7,313.6 | `b200_sxm-x94-nvl72-hybrid` | 3.48x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x217-romfill` | 176,855 | 217 | 1,396.6 | 1,397 | 7.9 | 1 | `layer_fixed_latency` | 13,412 | 9,603.3 | `b200_sxm-x111-nvl72-hybrid` | 3.71x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x218` | 177,670 | 218 | 1,398.6 | 1,399 | 7.9 | 1 | `layer_fixed_latency` | 13,531 | 9,674.7 | `b200_sxm-x111-nvl72-hybrid` | 3.71x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x219-romfill` | 178,485 | 219 | 1,400.4 | 1,400 | 7.8 | 1 | `layer_fixed_latency` | 13,649 | 9,746.2 | `b200_sxm-x112-nvl72-hybrid` | 3.72x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x221` | 180,115 | 221 | 1,404.0 | 1,404 | 7.8 | 1 | `layer_fixed_latency` | 13,885 | 9,889.7 | `b200_sxm-x113-nvl72-hybrid` | 3.73x |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 4 | 1,423.8 | 1,424 | 7.7 | 1 | `layer_fixed_latency` | 14,580 | 10,240.3 | `b200_sxm-x116-nvl72-hybrid` | 3.77x |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x5` | 231,125 | 5 | 1,509.5 | 1,510 | 6.5 | 1 | `layer_fixed_latency` | 21,285 | 14,100.2 | `b200_sxm-x144-nvl72-hybrid` | 3.98x |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 6 | 1,539.2 | 1,539 | 5.5 | 1 | `layer_fixed_latency` | 27,988 | 18,183.7 | `b200_sxm-x173-nvl72-hybrid` | 4.09x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 150 | densest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x160` | 130,400 | 1,144.9 | 8.8 | 1 |
| array | 150 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 1,491.0 | 4.6 | 4,098 |
| array | 150 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x150` | 122,250 | 814.8 | 6.7 | 1 |
| wafer | 42 | densest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 1,220.4 | 8.8 | 1 |
| wafer | 42 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 1,539.2 | 5.5 | 1 |
| wafer | 42 | smallest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 1,220.4 | 8.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 1,491.0 | 149,103 | 4,098 | 78,956 | 27,611.7 | `layer_fixed_latency` | `b200_sxm-x203-nvl72-hybrid` | 378.3 | 3,246 | 192,482.6 | 1.001 | 3.94x | 7.0x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 1,539.2 | 1,539 | 1 | 27,988 | 18,183.7 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 376.7 | 2,752 | 165,360.5 | 1.002 | 4.09x | 9.1x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-hybrid-x335` | 273,025 | 1,474.6 | 1,475 | 1 | 27,359 | 18,553.4 | `layer_fixed_latency` | `b200_sxm-x171-nvl72-hybrid` | 376.5 | 2,720 | 163,565.6 | 0.998 | 3.92x | 8.8x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 1,539.2 | -- | 1 | -- | 18,183.7 | -- | -- | -- | -- | -- | 0.984 | 1.04x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 1,491.0 | 149,103 | 4,098 | 78,956 | 13,933.8 | `layer_fixed_latency` | `b200_sxm-x203-nvl72-hybrid` | 378.3 | 3,246 | 98,449.6 | 1.001 | 3.94x | 7.1x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,172,575 | 1,156.1 | 193,073 | 4,152 | 242,118 | 83,592.3 | `layer_fixed_latency` | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 22,230 | 644,549.3 | 1.000 | 3.11x | 7.7x |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 1,491.0 | 149,103 | 4,098 | 78,956 | 7,094.9 | `layer_fixed_latency` | `b200_sxm-x203-nvl72-hybrid` | 374.4 | 3,246 | 51,913.5 | 1.001 | 3.98x | 7.3x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,172,575 | 1,156.1 | 193,073 | 4,152 | 242,118 | 41,924.1 | `layer_fixed_latency` | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 22,230 | 324,482.9 | 1.000 | 3.11x | 7.7x |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 1,491.0 | 149,103 | 4,098 | 78,956 | 3,675.4 | `layer_fixed_latency` | `b200_sxm-x203-nvl72-hybrid` | 363.9 | 3,246 | 28,856.2 | 1.001 | 4.10x | 7.9x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,172,575 | 1,156.1 | 193,073 | 4,152 | 242,118 | 21,090.1 | `layer_fixed_latency` | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 22,230 | 164,449.7 | 1.000 | 3.11x | 7.8x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 1,491.0 | 149,103 | 4,098 | 78,956 | 1,965.7 | `layer_fixed_latency` | `b200_sxm-x203-nvl72-hybrid` | 350.8 | 3,246 | 16,559.6 | 1.001 | 4.25x | 8.4x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,172,575 | 1,156.1 | 193,073 | 4,152 | 242,118 | 10,673.0 | `layer_fixed_latency` | `b200_sxm-x1358-nvl72-hybrid` | 371.7 | 22,230 | 84,433.1 | 1.000 | 3.11x | 7.9x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 1,491.0 | 149,103 | 4,098 | 78,956 | 1,110.8 | `layer_fixed_latency` | `b200_sxm-x203-nvl72-hybrid` | 310.8 | 3,246 | 11,039.3 | 1.001 | 4.80x | 9.9x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,172,575 | 1,156.1 | 193,073 | 4,152 | 242,118 | 5,464.5 | `layer_fixed_latency` | `b200_sxm-x1358-nvl72-hybrid` | 356.5 | 22,230 | 46,132.0 | 1.000 | 3.24x | 8.4x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 1,491.0 | 149,103 | 4,098 | 78,956 | 683.4 | `layer_fixed_latency` | `b200_sxm-x203-nvl72-hybrid` | 257.2 | 3,246 | 7,049.6 | 1.001 | 5.80x | 10.3x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47-romfill` | 2,172,575 | 1,156.1 | 193,073 | 4,152 | 242,118 | 2,860.2 | `layer_fixed_latency` | `b200_sxm-x1358-nvl72-hybrid` | 354.1 | 22,230 | 25,415.9 | 1.000 | 3.26x | 8.9x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 959.9 | 245,736 | 4,098 | 103,243 | 420.1 | `layer_fixed_latency` | `b200_sxm-x203-nvl72-hybrid` | 148.6 | 3,246 | 3,987.8 | 1.001 | 6.46x | 9.5x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 2,172,575 | 1,038.8 | 265,925 | 4,152 | 376,031 | 1,414.0 | `layer_fixed_latency` | `b200_sxm-x1358-nvl72-hybrid` | 293.7 | 22,230 | 9,793.3 | 1.000 | 3.54x | 6.9x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 325,185 | 339.9 | 348,028 | 4,098 | 128,093 | 368.1 | `compute` | `b200_sxm-x203-nvl72-hybrid` | 64.8 | 3,246 | 2,858.1 | 1.001 | 5.24x | 7.8x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x47` | 2,172,575 | 551.7 | 564,962 | 4,152 | 451,704 | 799.5 | `kv_read` | `b200_sxm-x1358-nvl72-hybrid` | 189.8 | 22,230 | 4,960.7 | 1.000 | 2.91x | 6.2x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 325,185 | 92.1 | 377,103 | 4,098 | 134,385 | 356.4 | `compute` | `b200_sxm-x203-pipeline` | 0.0 | 3,246 | 2,390.3 | 1.001 | --x | --x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x47` | 2,172,575 | 168.6 | 690,484 | 4,152 | 483,467 | 700.2 | `kv_read` | `b200_sxm-x1358-nvl72-hybrid` | 92.1 | 22,230 | 3,274.6 | 1.000 | 1.83x | 4.7x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | wafer | SRAM | 1 |
| 2-256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 325,185 | array | HBM | 4,098 |
| 1024-4096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | 325,185 | array | HBM | 4,098 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 56, 57, 70, 84, 112, 113, 168, 170, 224, 227, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 56, 57, 60, 70, 84, 112, 113, 168, 170, 224, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 29, 30, 35, 37, 42, 43, 45, 56, 57, 84, 112, 113, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 29, 30, 35, 37, 42, 48, 55, 56, 57, 84, 112, 113, 170, 227, 340 |
| DeepSeek-V4-Pro-0813 | HBM | rom | 399 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 399 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 150, 160, 170, 184, 217, 219, 221, 227, 246, 294, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 150, 160, 170, 184, 218, 221, 227, 286, 294, 334, 335, 340 |
| Qwen3-8B | HBM | rom | 49, 57, 62, 74, 98, 113, 147, 170, 196, 227, 340 |
| Qwen3-8B | HBM | sram | 49, 57, 62, 74, 98, 113, 147, 170, 196, 227, 340 |
| Qwen3-8B | SRAM | rom | 5, 6, 7, 8, 12, 15, 16, 57, 113, 170, 227, 340 |
| Qwen3-8B | SRAM | sram | 5, 6, 8, 12, 16, 57, 113, 170, 227, 340 |

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
| Qwen3-8B | `ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill` | 1 | 5 | 2.03 | hierarchical | 63.04 | 11.04 | 35.25 | 24.92 | 9,332.7 |
| Qwen3-8B | `b200_sxm-x3-tensor` | 1 | 3 | 2.03 | measured_floor | 566.80 | 176.95 | 840.79 | 180.93 | 631.1 |
| Qwen3-8B | `b200_sxm-x3-tensor` | 64 | 3 | 2.03 | measured_floor | 566.80 | 287.05 | 4,755.95 | 263.50 | 178.3 |
| DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x30` | 1 | 16 | 6.51 | hierarchical, one_shot | 256.93 | 57.95 | 58.57 | 34.41 | 2,815.4 |
| DeepSeek-V4-Flash-0731 | `b200_sxm-x15-hybrid` | 1 | 8 | 5.51 | measured_floor | 894.40 | 612.17 | 237.35 | 223.04 | 584.6 |
| DeepSeek-V4-Flash-0731 | `b200_sxm-x15-hybrid` | 64 | 2 | 5.51 | measured_floor | 946.40 | 602.49 | 2,941.74 | 239.16 | 234.0 |
| DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 1 | 16 | 5.51 | one_shot | 363.36 | 259.07 | 218.00 | 119.44 | 1,220.4 |
| DeepSeek-V4-Pro-0813 | `b200_sxm-x87-nvl72-hybrid` | 1 | 64 | 6.51 | measured_floor | 1,259.70 | 1,298.12 | 148.55 | 318.46 | 372.9 |
| DeepSeek-V4-Pro-0813 | `b200_sxm-x87-nvl72-hybrid` | 64 | 4 | 5.51 | measured_floor | 1,263.60 | 1,551.46 | 2,733.82 | 350.92 | 194.0 |

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

**The thermal limit binds here, and this is the first version of this
study in which it could.**
Static power is charged per mm2 per second whether or not a byte moves,
so the coolable step time solves
`t >= E_dynamic / (cooling_limit - P_static)` rather than dividing the
total energy by the total limit. Under the old rule stretching a step
always reduced modelled power, so every design was coolable at some speed
and `thermal_scale` was exactly 1.0 at all 11,747 feasible points across
both studies.

- **533 of 8,937 feasible points (6.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 72, rom 461.
- By area class: large array (5,000-40,000 mm2) 95, small array (1,600-5,000 mm2) 8, wafer (>=40,000 mm2) 430.
- By KV store: hbm 533.
- By batch: B=1 26, B=2 26, B=4 26, B=8 27, B=16 27, B=32 29, B=64 41, B=256 80, B=1024 126, B=4096 125.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 46% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 547 | 14 | 45.6% | 100.0% | 0.625 | 77% |
| gpu | small array (1,600-5,000 mm2) | 52 | 8 | 91.1% | 100.0% | 0.625 | 39% |
| gpu | wafer (>=40,000 mm2) | 3,069 | 50 | 38.6% | 100.0% | 0.625 | 91% |
| rom | large array (5,000-40,000 mm2) | 529 | 81 | 32.2% | 100.0% | 0.500 | 63% |
| rom | small array (1,600-5,000 mm2) | 100 | 0 | 20.3% | 25.3% | 0.127 | 69% |
| rom | wafer (>=40,000 mm2) | 4,640 | 380 | 30.5% | 100.0% | 0.500 | 83% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x147` | Qwen3-8B | 4096 | 119,805 | hbm | 1.538x | 59,902.5 / 59,902.5 W | 32% | 75.2 | 115.6 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x170` | Qwen3-8B | 4096 | 138,550 | hbm | 1.538x | 69,275.0 / 69,275.0 W | 32% | 86.9 | 133.6 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x113` | Qwen3-8B | 4096 | 92,095 | hbm | 1.538x | 46,047.5 / 46,047.5 W | 32% | 57.9 | 89.0 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x98` | Qwen3-8B | 4096 | 79,870 | hbm | 1.537x | 39,935.0 / 39,935.0 W | 32% | 50.3 | 77.3 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x74` | Qwen3-8B | 4096 | 60,310 | hbm | 1.534x | 30,155.0 / 30,155.0 W | 32% | 38.1 | 58.4 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x62` | Qwen3-8B | 4096 | 50,530 | hbm | 1.532x | 25,265.0 / 25,265.0 W | 32% | 32.0 | 49.0 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x57` | Qwen3-8B | 4096 | 46,455 | hbm | 1.529x | 23,227.5 / 23,227.5 W | 31% | 29.4 | 45.0 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x147` | Qwen3-8B | 4096 | 119,805 | hbm | 1.529x | 59,902.5 / 59,902.5 W | 32% | 75.2 | 115.0 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x170` | Qwen3-8B | 4096 | 138,550 | hbm | 1.528x | 69,275.0 / 69,275.0 W | 32% | 86.9 | 132.9 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x98` | Qwen3-8B | 4096 | 79,870 | hbm | 1.528x | 39,935.0 / 39,935.0 W | 32% | 50.3 | 76.8 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x113` | Qwen3-8B | 4096 | 92,095 | hbm | 1.528x | 46,047.5 / 46,047.5 W | 32% | 57.9 | 88.5 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x196` | Qwen3-8B | 4096 | 159,740 | hbm | 1.528x | 79,870.0 / 79,870.0 W | 32% | 100.1 | 153.0 |

The worst point's dynamic energy is kv read 95.9%, arithmetic 3.8%, operand delivery 0.3%, weight read 0.0%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4-Flash-0731 | 1 | 34,230 | `DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x42` | 0.832966 | 2,704.9 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x21-nvl72-tensor` | 13.619769 | 8,080.2 | layer_fixed_latency | 16.35x |
| DeepSeek-V4-Flash-0731 | 2 | 45,640 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56` | 0.809241 | 6,993.4 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x29-hybrid` | 9.970569 | 12,983.8 | layer_fixed_latency | 11.93x |
| DeepSeek-V4-Flash-0731 | 4 | 45,640 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56` | 0.424056 | 6,993.4 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x29-hybrid` | 5.592882 | 12,983.8 | layer_fixed_latency | 12.72x |
| DeepSeek-V4-Flash-0731 | 8 | 45,640 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56` | 0.231463 | 6,993.4 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x29-hybrid` | 3.144905 | 13,645.6 | layer_fixed_latency | 13.59x |
| DeepSeek-V4-Flash-0731 | 16 | 45,640 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56` | 0.137242 | 7,188.0 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x29-hybrid` | 1.912022 | 14,701.1 | layer_fixed_latency | 13.93x |
| DeepSeek-V4-Flash-0731 | 32 | 57,050 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x70` | 0.108167 | 10,789.8 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x36-hybrid` | 1.533147 | 21,125.9 | layer_fixed_latency | 14.17x |
| DeepSeek-V4-Flash-0731 | 64 | 182,560 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x224-romfill` | 0.134912 | 27,366.2 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x114-nvl72-hybrid` | 1.887526 | 57,513.5 | layer_fixed_latency | 13.99x |
| DeepSeek-V4-Flash-0731 | 256 | 277,100 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.083746 | 54,369.6 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x173-nvl72-hybrid` | 1.168712 | 109,078.8 | weight_read | 13.96x |
| DeepSeek-V4-Flash-0731 | 1024 | 277,100 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.062764 | 72,933.8 | compute | `DSV4-Flash/b200_sxm-x173-nvl72-hybrid` | 0.724806 | 146,864.9 | weight_read | 11.55x |
| DeepSeek-V4-Flash-0731 | 4096 | 277,100 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 0.066335 | 93,658.0 | weight_read | `DSV4-Flash/b200_sxm-x173-nvl72-hybrid` | 0.443288 | 159,179.0 | weight_read | 6.68x |
| DeepSeek-V4-Pro-0813 | 1 | 231,125 | `DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x5` | 14.100184 | 21,284.9 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x144-nvl72-hybrid` | 137.420131 | 53,814.7 | link_latency | 9.75x |
| DeepSeek-V4-Pro-0813 | 2 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 13.933850 | 78,955.5 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 98.449554 | 76,151.2 | link_latency | 7.07x |
| DeepSeek-V4-Pro-0813 | 4 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 7.094915 | 78,955.5 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 51.913486 | 77,754.2 | link_latency | 7.32x |
| DeepSeek-V4-Pro-0813 | 8 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 3.675448 | 78,955.5 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 28.856191 | 92,029.6 | layer_fixed_latency | 7.85x |
| DeepSeek-V4-Pro-0813 | 16 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1.965714 | 78,955.5 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 16.559574 | 92,948.1 | layer_fixed_latency | 8.42x |
| DeepSeek-V4-Pro-0813 | 32 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 1.110847 | 78,955.5 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 11.039300 | 109,776.9 | layer_fixed_latency | 9.94x |
| DeepSeek-V4-Pro-0813 | 64 | 325,185 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399` | 0.683414 | 78,955.5 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x203-nvl72-hybrid` | 7.049621 | 116,023.6 | link_latency | 10.32x |
| DeepSeek-V4-Pro-0813 | 256 | 2,172,575 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47` | 1.414049 | 376,030.9 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x1358-nvl72-hybrid` | 9.793345 | 736,358.3 | link_latency | 6.93x |
| DeepSeek-V4-Pro-0813 | 1024 | 2,172,575 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47` | 0.799531 | 451,704.5 | kv_read | `DSV4-Pro/b200_sxm-x1358-nvl72-hybrid` | 4.960654 | 964,189.0 | weight_read | 6.20x |
| DeepSeek-V4-Pro-0813 | 4096 | 2,172,575 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47` | 0.700186 | 483,466.8 | kv_read | `DSV4-Pro/b200_sxm-x1358-nvl72-hybrid` | 3.274618 | 1,234,843.3 | weight_read | 4.68x |
| Qwen3-8B | 1 | 5,705 | `Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x7-romfill` | 0.058336 | 606.5 | layer_fixed_latency | `Qwen3-8B/b200_sxm-x4-tensor` | 3.649809 | 2,655.3 | layer_fixed_latency | 62.57x |
| Qwen3-8B | 2 | 39,935 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill` | 0.362160 | 9,457.3 | layer_fixed_latency | `Qwen3-8B/b200_sxm-x25-nvl72-tensor` | 4.674509 | 10,929.6 | layer_fixed_latency | 12.91x |
| Qwen3-8B | 4 | 39,935 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill` | 0.249416 | 9,457.3 | layer_fixed_latency | `Qwen3-8B/b200_sxm-x25-nvl72-tensor` | 2.446936 | 11,181.7 | layer_fixed_latency | 9.81x |
| Qwen3-8B | 8 | 92,095 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 0.263913 | 20,448.1 | layer_fixed_latency | `Qwen3-8B/b200_sxm-x58-nvl72-tensor` | 2.436074 | 23,519.9 | layer_fixed_latency | 9.23x |
| Qwen3-8B | 16 | 277,100 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.328338 | 58,747.5 | layer_fixed_latency | `Qwen3-8B/b200_sxm-x173-nvl72-hybrid` | 3.542506 | 69,008.4 | layer_fixed_latency | 10.79x |
| Qwen3-8B | 32 | 277,100 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.242134 | 81,319.4 | layer_fixed_latency | `Qwen3-8B/b200_sxm-x173-nvl72-hybrid` | 1.899297 | 71,159.3 | layer_fixed_latency | 7.84x |
| Qwen3-8B | 64 | 277,100 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.199833 | 91,617.3 | layer_fixed_latency | `Qwen3-8B/b200_sxm-x173-nvl72-hybrid` | 1.077692 | 75,001.5 | layer_fixed_latency | 5.39x |
| Qwen3-8B | 256 | 277,100 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.171899 | 138,550.0 | thermal | `Qwen3-8B/b200_sxm-x173-nvl72-hybrid` | 0.461054 | 95,796.2 | layer_fixed_latency | 2.68x |
| Qwen3-8B | 1024 | 277,100 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.168925 | 138,550.0 | thermal | `Qwen3-8B/b200_sxm-x173-nvl72-hybrid` | 0.283811 | 127,699.8 | kv_read | 1.68x |
| Qwen3-8B | 4096 | 277,100 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.168182 | 138,550.0 | thermal | `Qwen3-8B/b200_sxm-x173-nvl72-hybrid` | 0.229368 | 156,520.0 | kv_read | 1.36x |

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
| Qwen3-8B | 8,192 | 8 B | 16.4 GB | 16.00 | 1.208 GB | 1.208 GB | 12.5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 284 B | 166.9 GB | 4.70 | 0.317 GB | 1.382 GB | 35.3 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1,600 B | 892.7 GB | 4.46 | 2.207 GB | 9.856 GB | 18.0 |

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
| Qwen3-8B | 1 | 46,225 | 12,757.3 | wafer-pipeline | 4,904.9 | wafer-tensor | 2.60x | 1,443.8 | pipeline | 1,202.6 | tensor | 1.20x | 8.84x | 4.08x | 0.46x |
| Qwen3-8B | 2 | 92,450 | 12,482.1 | wafer-pipeline | 5,080.9 | wafer-hybrid | 2.46x | 1,518.4 | pipeline | 1,268.9 | tensor | 1.20x | 8.22x | 4.00x | 0.49x |
| Qwen3-8B | 3 | 138,675 | 12,427.9 | wafer-pipeline | 4,596.7 | wafer-hybrid | 2.70x | 1,552.6 | pipeline | 1,239.5 | hybrid | 1.25x | 8.00x | 3.71x | 0.46x |
| Qwen3-8B | 4 | 184,900 | 12,398.1 | wafer-pipeline | 4,243.5 | wafer-hybrid | 2.92x | 1,570.3 | pipeline | 1,262.2 | hybrid | 1.24x | 7.90x | 3.36x | 0.43x |
| Qwen3-8B | 6 | 277,350 | 13,096.7 | wafer-pipeline | 4,545.7 | wafer-hybrid | 2.88x | 1,588.1 | pipeline | 1,258.3 | hybrid | 1.26x | 8.25x | 3.61x | 0.44x |
| Qwen3-8B | 8 | 369,800 | 13,329.9 | wafer-pipeline | 4,508.4 | wafer-hybrid | 2.96x | 1,597.4 | pipeline | 1,254.9 | hybrid | 1.27x | 8.34x | 3.59x | 0.43x |
| Qwen3-8B | 12 | 554,700 | 13,535.4 | wafer-pipeline | 4,521.9 | wafer-hybrid | 2.99x | 1,606.8 | pipeline | 1,263.0 | hybrid | 1.27x | 8.42x | 3.58x | 0.42x |
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 3,503.0 | wafer-pipeline | 2,786.2 | wafer-pipeline | 1.26x | 983.5 | pipeline | 599.7 | tensor | 1.64x | 3.56x | 4.65x | 1.30x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 3,503.2 | wafer-pipeline | 2,899.9 | wafer-hybrid | 1.21x | 991.4 | pipeline | 607.7 | tensor | 1.63x | 3.53x | 4.77x | 1.35x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 3,503.2 | wafer-pipeline | 2,734.5 | wafer-hybrid | 1.28x | 1,000.8 | pipeline | 602.6 | hybrid | 1.66x | 3.50x | 4.54x | 1.30x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 3,503.2 | wafer-pipeline | 2,632.6 | wafer-hybrid | 1.33x | 1,005.6 | pipeline | 605.8 | hybrid | 1.66x | 3.48x | 4.35x | 1.25x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 3,503.2 | wafer-pipeline | 2,414.5 | wafer-hybrid | 1.45x | 1,010.3 | pipeline | 604.7 | hybrid | 1.67x | 3.47x | 3.99x | 1.15x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 3,503.2 | wafer-pipeline | 2,543.0 | wafer-hybrid | 1.38x | 1,012.7 | pipeline | 603.8 | hybrid | 1.68x | 3.46x | 4.21x | 1.22x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 3,503.2 | wafer-pipeline | 2,541.0 | wafer-hybrid | 1.38x | 1,015.2 | pipeline | 604.0 | hybrid | 1.68x | 3.45x | 4.21x | 1.22x |
| DeepSeek-V4-Pro-0813 | 3 | 138,675 | 1,748.7 | wafer-pipeline | 1,220.4 | wafer-hybrid | 1.43x | 682.5 | pipeline | 372.9 | hybrid | 1.83x | 2.56x | 3.27x | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 1,750.0 | wafer-pipeline | 1,423.8 | wafer-hybrid | 1.23x | 690.6 | pipeline | 377.2 | hybrid | 1.83x | 2.53x | 3.77x | 1.49x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 1,749.7 | wafer-pipeline | 1,539.2 | wafer-hybrid | 1.14x | 698.8 | pipeline | 376.7 | hybrid | 1.86x | 2.50x | 4.09x | 1.63x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 1,749.7 | wafer-pipeline | 1,484.5 | wafer-hybrid | 1.18x | 703.0 | pipeline | 376.3 | hybrid | 1.87x | 2.49x | 3.95x | 1.59x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 1,749.9 | wafer-pipeline | 1,382.1 | wafer-hybrid | 1.27x | 707.4 | pipeline | 377.6 | hybrid | 1.87x | 2.47x | 3.66x | 1.48x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.42x to 1.63x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill | 13,040 | 10,793.3 | 10,793.3 | layer_fixed_latency | Qwen3-8B/b200_sxm-x8-tensor | 12,800 | 1.02x | tensor | 177.49 | 943.8 | 943.8 | layer_fixed_latency | 11.44x | 4.18x | 33.45x | 11.44x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x5-romfill | 4,075 | 9,332.7 | 9,332.7 | layer_fixed_latency | Qwen3-8B/b200_sxm-x3-tensor | 4,800 | 0.85x | tensor | 176.95 | 631.1 | 631.1 | weight_read | 14.79x | 9.62x | 28.86x | 14.79x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill | 50,530 | 9,880.7 | 39,523.0 | layer_fixed_latency | Qwen3-8B/b200_sxm-x32-nvl72-tensor | 51,200 | 0.99x | tensor | 180.28 | 1,202.3 | 2,404.6 | layer_fixed_latency | 8.22x | 3.87x | 30.94x | 8.22x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 9,479.5 | 37,917.9 | layer_fixed_latency | Qwen3-8B/b200_sxm-x25-nvl72-tensor | 40,000 | 1.00x | tensor | 180.23 | 1,169.1 | 2,338.1 | layer_fixed_latency | 8.11x | 4.74x | 29.61x | 8.11x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x62-romfill | 50,530 | 9,880.7 | 39,523.0 | layer_fixed_latency | Qwen3-8B/b200_sxm-x32-nvl72-tensor | 51,200 | 0.99x | tensor | 185.36 | 1,178.6 | 4,714.4 | layer_fixed_latency | 8.38x | 3.87x | 30.94x | 8.38x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 9,479.5 | 37,917.9 | layer_fixed_latency | Qwen3-8B/b200_sxm-x25-nvl72-tensor | 40,000 | 1.00x | tensor | 185.27 | 1,142.4 | 4,569.7 | layer_fixed_latency | 8.30x | 4.74x | 29.61x | 8.30x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill | 138,550 | 9,796.1 | 107,756.6 | layer_fixed_latency | Qwen3-8B/b200_sxm-x87-nvl72-hybrid | 139,200 | 1.00x | hybrid | 190.24 | 1,207.9 | 9,663.2 | layer_fixed_latency | 8.11x | 3.89x | 30.73x | 8.11x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 7,895.1 | 63,161.0 | layer_fixed_latency | Qwen3-8B/b200_sxm-x25-nvl72-tensor | 40,000 | 1.00x | tensor | 195.33 | 1,092.6 | 8,741.0 | layer_fixed_latency | 7.23x | 7.23x | 24.66x | 7.23x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 9,672.8 | 212,802.7 | layer_fixed_latency | Qwen3-8B/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 196.80 | 1,217.5 | 19,480.1 | layer_fixed_latency | 7.94x | 3.86x | 30.35x | 7.94x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 6,016.1 | 96,257.4 | kv_read | Qwen3-8B/b200_sxm-x25-nvl72-tensor | 40,000 | 1.00x | tensor | 215.47 | 1,005.0 | 16,080.1 | layer_fixed_latency | 5.99x | 5.99x | 18.79x | 5.99x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 8,789.7 | 377,956.9 | layer_fixed_latency | Qwen3-8B/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 212.31 | 1,170.8 | 37,466.1 | layer_fixed_latency | 7.51x | 6.85x | 27.58x | 7.51x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 3,615.2 | 115,687.7 | thermal | Qwen3-8B/b200_sxm-x25-nvl72-tensor | 40,000 | 1.00x | tensor | 255.73 | 866.1 | 27,715.1 | layer_fixed_latency | 4.17x | 4.17x | 11.48x | 4.17x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 7,163.6 | 458,469.6 | layer_fixed_latency | Qwen3-8B/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 243.33 | 1,087.4 | 69,594.5 | layer_fixed_latency | 6.59x | 6.59x | 22.48x | 6.59x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 1,832.4 | 117,272.4 | thermal | Qwen3-8B/b200_sxm-x25-nvl72-tensor | 40,000 | 1.00x | tensor | 336.26 | 678.5 | 43,425.9 | layer_fixed_latency | 2.70x | 2.70x | 6.26x | 2.70x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 3,148.4 | 805,998.1 | thermal | Qwen3-8B/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 308.40 | 811.6 | 207,776.4 | layer_fixed_latency | 3.88x | 3.88x | 10.16x | 3.88x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 462.9 | 118,489.7 | thermal | Qwen3-8B/b200_sxm-x25-hybrid | 40,000 | 1.00x | hybrid | 361.59 | 311.4 | 79,719.9 | kv_read | 1.49x | 1.49x | 2.25x | 1.49x |
| Qwen3-8B | 1024 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 801.0 | 820,186.7 | thermal | Qwen3-8B/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 456.97 | 439.4 | 449,946.5 | kv_read | 1.82x | 1.82x | 3.25x | 1.82x |
| Qwen3-8B | 1024 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 116.0 | 118,798.0 | thermal | Qwen3-8B/b200_sxm-x25-hybrid | 40,000 | 1.00x | hybrid | 550.45 | 106.3 | 108,846.5 | kv_read | 1.09x | 1.09x | 1.25x | 1.09x |
| Qwen3-8B | 4096 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 201.1 | 823,812.2 | thermal | Qwen3-8B/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 724.38 | 166.6 | 682,398.3 | kv_read | 1.21x | 1.21x | 1.49x | 1.21x |
| Qwen3-8B | 4096 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 29.0 | 118,875.3 | thermal | Qwen3-8B/b200_sxm-x25-pipeline | 40,000 | 1.00x | pipeline | 145.19 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x56 | 45,640 | 3,374.2 | 3,374.2 | layer_fixed_latency | DSV4-Flash/b200_sxm-x29-nvl72-tensor | 46,400 | 0.98x | tensor | 725.33 | 599.7 | 599.7 | layer_fixed_latency | 5.63x | 0.30x | 8.78x | 5.63x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x29 | 23,635 | 2,558.9 | 2,558.9 | layer_fixed_latency | DSV4-Flash/b200_sxm-x15-hybrid | 24,000 | 0.98x | hybrid | 612.17 | 584.6 | 1,169.2 | layer_fixed_latency | 4.38x | 0.44x | 6.61x | 4.38x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x60 | 48,900 | 3,373.9 | 50,608.5 | layer_fixed_latency | DSV4-Flash/b200_sxm-x31-hybrid | 49,600 | 0.99x | hybrid | 617.54 | 585.0 | 2,340.0 | layer_fixed_latency | 5.77x | 4.25x | 8.79x | 5.77x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 3,354.3 | 46,959.5 | layer_fixed_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 0.98x | hybrid | 617.54 | 580.4 | 2,321.5 | layer_fixed_latency | 5.78x | 4.21x | 8.73x | 5.78x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x60 | 48,900 | 3,373.9 | 50,608.5 | layer_fixed_latency | DSV4-Flash/b200_sxm-x31-hybrid | 49,600 | 0.99x | hybrid | 617.54 | 585.0 | 2,340.0 | layer_fixed_latency | 5.77x | 4.25x | 8.79x | 5.77x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 3,354.3 | 46,959.5 | layer_fixed_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 0.98x | hybrid | 617.54 | 580.4 | 2,321.5 | layer_fixed_latency | 5.78x | 4.21x | 8.73x | 5.78x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x60 | 48,900 | 3,373.9 | 50,608.5 | layer_fixed_latency | DSV4-Flash/b200_sxm-x31-hybrid | 49,600 | 0.99x | hybrid | 670.16 | 547.7 | 4,381.8 | layer_fixed_latency | 6.16x | 4.25x | 8.79x | 6.16x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 3,354.3 | 46,959.5 | layer_fixed_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 0.98x | hybrid | 670.16 | 542.4 | 4,338.9 | layer_fixed_latency | 6.18x | 4.21x | 8.73x | 6.18x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x70 | 57,050 | 3,362.0 | 60,515.5 | layer_fixed_latency | DSV4-Flash/b200_sxm-x36-hybrid | 57,600 | 0.99x | hybrid | 737.43 | 501.7 | 8,026.6 | layer_fixed_latency | 6.70x | 4.39x | 8.78x | 6.70x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 3,273.4 | 52,374.6 | layer_fixed_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 0.98x | hybrid | 775.40 | 480.5 | 7,688.8 | layer_fixed_latency | 6.81x | 4.70x | 8.52x | 6.81x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x168-romfill | 136,920 | 3,253.3 | 136,640.6 | layer_fixed_latency | DSV4-Flash/b200_sxm-x86-nvl72-hybrid | 137,600 | 1.00x | hybrid | 721.88 | 517.7 | 16,567.8 | layer_fixed_latency | 6.28x | 4.17x | 8.53x | 6.28x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 2,916.0 | 93,311.4 | layer_fixed_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 0.98x | hybrid | 750.69 | 405.3 | 12,969.1 | layer_fixed_latency | 7.19x | 7.19x | 7.75x | 7.19x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 3,251.5 | 276,379.1 | layer_fixed_latency | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 738.87 | 513.7 | 32,877.3 | layer_fixed_latency | 6.33x | 4.19x | 8.53x | 6.33x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56 | 45,640 | 2,435.9 | 155,900.0 | layer_fixed_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 0.98x | hybrid | 931.67 | 318.1 | 20,357.7 | weight_read | 7.66x | 7.66x | 7.92x | 7.66x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 2,536.0 | 649,221.6 | layer_fixed_latency | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 877.94 | 364.6 | 93,332.5 | weight_read | 6.96x | 6.96x | 7.30x | 6.96x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56 | 45,640 | 888.8 | 227,539.1 | compute | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 0.98x | hybrid | 1,011.24 | 157.9 | 40,433.7 | weight_read | 5.63x | 5.63x | 5.89x | 5.63x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 1,134.8 | 1,162,029.6 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 972.67 | 197.9 | 202,626.6 | weight_read | 5.73x | 5.73x | 5.94x | 5.80x |
| DeepSeek-V4-Flash-0731 | 1024 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56 | 45,640 | 247.1 | 253,032.8 | compute | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 0.98x | hybrid | 2,598.60 | 70.4 | 72,115.0 | weight_read | 3.51x | 3.51x | 4.13x | 3.51x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 344.7 | 1,411,894.1 | weight_read | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 1,963.41 | 87.7 | 359,087.4 | weight_read | 3.93x | 3.93x | 4.41x | 3.96x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56 | 45,640 | 63.1 | 258,510.1 | compute | DSV4-Flash/b200_sxm-x29-pipeline | 46,400 | 0.98x | pipeline | 444.59 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x6 | 277,350 | 1,539.2 | 1,539.2 | layer_fixed_latency | DSV4-Pro/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 1,301.29 | 376.7 | 1,130.1 | link_latency | 4.09x | 0.07x | 11.61x | 4.09x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x150 | 122,250 | 814.8 | 814.8 | link_latency | DSV4-Pro/b200_sxm-x76-nvl72-hybrid | 121,600 | 1.01x | hybrid | 1,298.12 | 370.4 | 740.7 | link_latency | 2.20x | 0.08x | 6.15x | 2.20x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,491.0 | 149,102.8 | layer_fixed_latency | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 1,304.07 | 378.3 | 1,134.8 | link_latency | 3.94x | 5.54x | 11.25x | 3.94x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,491.0 | 149,102.8 | layer_fixed_latency | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 1,304.47 | 374.4 | 1,497.8 | link_latency | 3.98x | 5.54x | 11.25x | 3.98x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,491.0 | 149,102.8 | layer_fixed_latency | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 1,133.36 | 363.9 | 4,730.1 | layer_fixed_latency | 4.10x | 5.54x | 11.25x | 4.10x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,491.0 | 149,102.8 | layer_fixed_latency | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 1,206.11 | 350.8 | 5,613.0 | layer_fixed_latency | 4.25x | 5.54x | 11.25x | 4.25x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,491.0 | 149,102.8 | layer_fixed_latency | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 1,192.67 | 310.8 | 9,944.2 | layer_fixed_latency | 4.80x | 5.54x | 11.25x | 4.80x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,491.0 | 149,102.8 | layer_fixed_latency | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 1,552.46 | 257.2 | 16,458.1 | link_latency | 5.80x | 5.54x | 11.25x | 5.80x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47 | 2,172,575 | 1,038.8 | 265,925.0 | layer_fixed_latency | DSV4-Pro/b200_sxm-x1358-nvl72-hybrid | 2,172,800 | 1.00x | hybrid | 1,328.30 | 293.7 | 75,189.7 | link_latency | 3.54x | 1.48x | 7.84x | 3.69x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 959.9 | 245,735.7 | layer_fixed_latency | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 2,127.20 | 148.6 | 38,030.0 | weight_read | 6.46x | 6.46x | 7.81x | 6.46x |
| DeepSeek-V4-Pro-0813 | 1024 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47 | 2,172,575 | 551.7 | 564,961.9 | kv_read | DSV4-Pro/b200_sxm-x1358-nvl72-hybrid | 2,172,800 | 1.00x | hybrid | 1,639.49 | 189.8 | 194,367.3 | weight_read | 2.91x | 2.91x | 4.16x | 3.11x |
| DeepSeek-V4-Pro-0813 | 1024 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399 | 325,185 | 339.9 | 348,028.1 | compute | DSV4-Pro/b200_sxm-x203-nvl72-hybrid | 324,800 | 1.00x | hybrid | 2,430.81 | 64.8 | 66,393.4 | weight_read | 5.24x | 5.24x | 5.60x | 5.26x |
| DeepSeek-V4-Pro-0813 | 4096 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 168.6 | 690,483.5 | kv_read | DSV4-Pro/b200_sxm-x1358-nvl72-hybrid | 2,172,800 | 1.00x | hybrid | 1,753.93 | 92.1 | 377,095.4 | weight_read | 1.83x | 1.83x | 2.03x | 1.97x |
| DeepSeek-V4-Pro-0813 | 4096 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399 | 325,185 | 92.1 | 377,103.5 | compute | DSV4-Pro/b200_sxm-x203-pipeline | 324,800 | 1.00x | pipeline | 310.03 | infeasible | — | capacity_or_format | — | — | — | — |

## The headline is a band, and each side's share of it is reported apart

Every hop latency in this model states a range, and the ratio moves inside it.
This table re-runs the whole study at both ends of those ranges three ways:
the **wafer fabric** alone (`on_wafer_n5`, `rom_wafer_serdes`), which no GPU design touches; the
**cluster fabric** alone (`nvlink5`, `infiniband_ndr`), which is charged to both families; and
both together.

**Why three and not one.** This study used to publish the joint band only. Moving
both sides at once is the right test for a *common-mode* error, and the wrong one
for asking how much of the uncertainty is ours: the two sides partly cancel, so the
joint band comes out narrower than the wafer side's own band and the reader cannot
see that most of the width sits on the side with the weaker evidence. Reading the
cells: a **low** wafer hop makes the ROM machine faster and the ratio larger, and a
**low** cluster hop makes the GPU faster and the ratio smaller, so the two columns
run in opposite directions by construction.

| Model | ROM mm2 | Ratio stated | Wafer fabric low → high | Cluster fabric low → high | Both together | Widest one-sided span |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 23,635 | 4.38x | 4.38x → 4.38x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 24,450 | 4.82x | 4.82x → 4.82x | 4.18x → 4.82x | — | 1.2x |
| DeepSeek-V4-Flash-0731 | 28,525 | 5.23x | 5.23x → 5.23x | 4.75x → 5.23x | 4.55x → 8.14x | 1.1x |
| DeepSeek-V4-Flash-0731 | 30,155 | 5.34x | 5.34x → 5.34x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 34,230 | 5.47x | 5.47x → 5.47x | 4.88x → 5.47x | 4.73x → 8.77x | 1.1x |
| DeepSeek-V4-Flash-0731 | 35,045 | 5.50x | 5.50x → 5.50x | 4.88x → 5.50x | — | 1.1x |
| DeepSeek-V4-Flash-0731 | 36,675 | 5.51x | 5.51x → 5.51x | 4.86x → 5.51x | 4.76x → 8.88x | 1.1x |
| DeepSeek-V4-Flash-0731 | 39,120 | 5.59x | 5.59x → 5.59x | 4.90x → 5.59x | — | 1.1x |
| DeepSeek-V4-Flash-0731 | 44,825 | 5.62x | 5.62x → 5.62x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 45,640 | 5.63x | 5.63x → 5.63x | 5.05x → 5.63x | 4.78x → 9.30x | 1.1x |
| DeepSeek-V4-Flash-0731 | 46,225 | 4.65x | 4.67x → 4.58x | 4.17x → 4.65x | 3.90x → 7.66x | 1.1x |
| DeepSeek-V4-Flash-0731 | 46,455 | 5.61x | 5.61x → 5.61x | 5.03x → 5.61x | 4.76x → 9.26x | 1.1x |
| DeepSeek-V4-Flash-0731 | 48,900 | 5.62x | 5.62x → 5.62x | 5.00x → 5.62x | 4.75x → 9.33x | 1.1x |
| DeepSeek-V4-Flash-0731 | 57,050 | 5.58x | 5.58x → 5.58x | 5.04x → 5.58x | 4.72x → 9.43x | 1.1x |
| DeepSeek-V4-Flash-0731 | 68,460 | 5.50x | 5.50x → 5.50x | 5.01x → 5.50x | 4.69x → 9.51x | 1.1x |
| DeepSeek-V4-Flash-0731 | 91,280 | 5.40x | 5.40x → 5.40x | 4.95x → 5.40x | 4.64x → 9.34x | 1.1x |
| DeepSeek-V4-Flash-0731 | 92,095 | 5.38x | 5.38x → 5.38x | 4.93x → 5.38x | 4.63x → 9.30x | 1.1x |
| DeepSeek-V4-Flash-0731 | 92,450 | 4.77x | 5.13x → 4.23x | 4.37x → 4.77x | 4.27x → 7.46x | 1.2x |
| DeepSeek-V4-Flash-0731 | 136,920 | 5.41x | 5.41x → 5.41x | 4.88x → 5.54x | 4.68x → 9.20x | 1.1x |
| DeepSeek-V4-Flash-0731 | 138,550 | 5.40x | 5.40x → 5.40x | 4.86x → 5.53x | 4.67x → 9.18x | 1.1x |
| DeepSeek-V4-Flash-0731 | 138,675 | 4.54x | 4.97x → 3.89x | 4.09x → 4.65x | 4.14x → 6.80x | 1.3x |
| DeepSeek-V4-Flash-0731 | 182,560 | 5.37x | 5.37x → 5.37x | 4.92x → 5.50x | 4.63x → 9.19x | 1.1x |
| DeepSeek-V4-Flash-0731 | 184,900 | 4.35x | 4.76x → 3.60x | 3.98x → 4.45x | 3.96x → 6.32x | 1.3x |
| DeepSeek-V4-Flash-0731 | 185,005 | 5.37x | 5.37x → 5.37x | 4.91x → 5.50x | 4.63x → 9.19x | 1.1x |
| DeepSeek-V4-Flash-0731 | 277,100 | 5.38x | 5.38x → 5.38x | 4.96x → 5.57x | 4.61x → 9.19x | 1.1x |
| DeepSeek-V4-Flash-0731 | 277,350 | 3.99x | 4.58x → 3.14x | 3.68x → 4.14x | 3.81x → 5.52x | 1.5x |
| DeepSeek-V4-Flash-0731 | 323,575 | 4.20x | 4.62x → 3.58x | 3.91x → 4.35x | 3.84x → 6.29x | 1.3x |
| DeepSeek-V4-Flash-0731 | 369,800 | 4.21x | 4.62x → 3.59x | 3.92x → 4.42x | 3.84x → 6.29x | 1.3x |
| DeepSeek-V4-Flash-0731 | 554,700 | 4.21x | 4.60x → 3.59x | 4.01x → 4.46x | 3.83x → 6.29x | 1.3x |
| DeepSeek-V4-Pro-0813 | 122,250 | 2.20x | 2.20x → 2.20x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 130,400 | 3.08x | 3.08x → 3.08x | 3.08x → 3.13x | 2.91x → 5.43x | 1.0x |
| DeepSeek-V4-Pro-0813 | 138,550 | 3.25x | 3.25x → 3.25x | 3.25x → 3.29x | 3.03x → 6.06x | 1.0x |
| DeepSeek-V4-Pro-0813 | 138,675 | 3.27x | 3.73x → 2.49x | 3.27x → 3.32x | 3.18x → 5.31x | 1.5x |
| DeepSeek-V4-Pro-0813 | 149,960 | 3.48x | 3.48x → 3.48x | 3.48x → 3.53x | 3.16x → 6.64x | 1.0x |
| DeepSeek-V4-Pro-0813 | 176,855 | 3.71x | 3.71x → 3.71x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 177,670 | 3.71x | 3.71x → 3.71x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 178,485 | 3.72x | 3.72x → 3.72x | 3.72x → 3.77x | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 180,115 | 3.73x | 3.73x → 3.73x | 3.73x → 3.78x | 3.30x → 7.43x | 1.0x |
| DeepSeek-V4-Pro-0813 | 184,900 | 3.77x | 4.33x → 3.03x | 3.77x → 3.83x | 3.68x → 6.53x | 1.4x |
| DeepSeek-V4-Pro-0813 | 185,005 | 3.72x | 3.72x → 3.72x | 3.72x → 3.78x | 3.30x → 7.47x | 1.0x |
| DeepSeek-V4-Pro-0813 | 200,490 | 3.76x | 3.76x → 3.76x | 3.76x → 3.82x | 3.33x → 7.60x | 1.0x |
| DeepSeek-V4-Pro-0813 | 231,125 | 3.98x | 4.43x → 3.12x | 3.98x → 4.04x | 3.76x → 6.76x | 1.4x |
| DeepSeek-V4-Pro-0813 | 233,090 | 3.88x | 3.88x → 3.88x | 3.88x → 3.96x | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 239,610 | 3.89x | 3.89x → 3.89x | 3.89x → 3.97x | 3.42x → 8.03x | 1.0x |
| DeepSeek-V4-Pro-0813 | 272,210 | 3.91x | 3.91x → 3.91x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 273,025 | 3.92x | 3.92x → 3.92x | 3.92x → 4.00x | 3.43x → 8.24x | 1.0x |
| DeepSeek-V4-Pro-0813 | 277,100 | 3.91x | 3.91x → 3.91x | 3.91x → 4.00x | 3.42x → 8.26x | 1.0x |
| DeepSeek-V4-Pro-0813 | 277,350 | 4.09x | 4.50x → 3.43x | 4.09x → 4.18x | 3.83x → 7.39x | 1.3x |
| DeepSeek-V4-Pro-0813 | 325,185 | 3.94x | 3.94x → 3.94x | 3.94x → 4.03x | 3.42x → 8.41x | 1.0x |
| DeepSeek-V4-Pro-0813 | 369,800 | 3.95x | 4.42x → 3.23x | 3.94x → 4.06x | 3.76x → 7.02x | 1.4x |
| DeepSeek-V4-Pro-0813 | 554,700 | 3.66x | 4.22x → 2.89x | 3.66x → 3.80x | 3.59x → 6.37x | 1.5x |
| DeepSeek-V4-Pro-0813 | 2,172,575 | 3.11x | 3.61x → 2.36x | 3.11x → 3.55x | 3.07x → 5.46x | 1.5x |
| Qwen3-8B | 4,075 | 14.79x | 14.79x → 14.79x | 14.11x → 14.79x | 14.85x → 18.28x | 1.0x |
| Qwen3-8B | 4,890 | 15.74x | 15.74x → 15.74x | 15.02x → 15.74x | 15.87x → 19.32x | 1.0x |
| Qwen3-8B | 5,705 | 14.29x | 14.29x → 14.29x | — | — | 1.0x |
| Qwen3-8B | 6,520 | 14.79x | 14.79x → 14.79x | 14.01x → 14.79x | 14.87x → 18.75x | 1.1x |
| Qwen3-8B | 9,780 | 12.28x | 12.28x → 12.28x | 11.51x → 12.28x | 12.83x → 16.72x | 1.1x |
| Qwen3-8B | 12,225 | 11.31x | 11.31x → 11.31x | 10.53x → 11.31x | — | 1.1x |
| Qwen3-8B | 13,040 | 11.44x | 11.44x → 11.44x | 10.65x → 11.44x | 11.90x → 15.71x | 1.1x |
| Qwen3-8B | 39,935 | 8.01x | 8.01x → 8.01x | 8.01x → 8.01x | 8.26x → 11.35x | 1.0x |
| Qwen3-8B | 46,225 | 4.08x | 5.44x → 2.51x | 4.08x → 4.08x | 4.96x → 4.40x | 2.2x |
| Qwen3-8B | 46,455 | 8.10x | 8.10x → 8.10x | 8.10x → 8.10x | 8.21x → 11.40x | 1.0x |
| Qwen3-8B | 50,530 | 8.14x | 8.14x → 8.14x | 8.14x → 8.14x | 8.23x → 11.50x | 1.0x |
| Qwen3-8B | 60,310 | 7.94x | 7.94x → 7.94x | 7.94x → 7.94x | 8.02x → 11.27x | 1.0x |
| Qwen3-8B | 79,870 | 7.70x | 7.70x → 7.70x | 7.70x → 7.70x | 7.76x → 11.07x | 1.0x |
| Qwen3-8B | 92,095 | 7.63x | 7.63x → 7.63x | 7.63x → 7.63x | 7.73x → 10.97x | 1.0x |
| Qwen3-8B | 92,450 | 4.00x | 4.92x → 3.04x | 4.00x → 4.00x | 4.47x → 5.46x | 1.6x |
| Qwen3-8B | 119,805 | 7.94x | 7.94x → 7.94x | 7.94x → 8.33x | 8.05x → 11.49x | 1.0x |
| Qwen3-8B | 138,550 | 7.90x | 7.90x → 7.90x | 7.90x → 8.29x | 8.00x → 11.47x | 1.0x |
| Qwen3-8B | 138,675 | 3.71x | 4.64x → 2.76x | 3.71x → 3.89x | 4.22x → 5.04x | 1.7x |
| Qwen3-8B | 159,740 | 7.78x | 7.78x → 7.78x | 7.78x → 8.17x | 7.88x → 11.33x | 1.1x |
| Qwen3-8B | 184,900 | 3.36x | 4.30x → 2.40x | 3.36x → 3.53x | 3.90x → 4.41x | 1.8x |
| Qwen3-8B | 185,005 | 7.70x | 7.70x → 7.70x | 7.70x → 8.09x | 7.80x → 11.24x | 1.1x |
| Qwen3-8B | 277,100 | 7.69x | 7.69x → 7.69x | 7.68x → 8.27x | 7.82x → 11.27x | 1.1x |
| Qwen3-8B | 277,350 | 3.61x | 4.47x → 2.54x | 3.61x → 3.88x | 4.06x → 4.74x | 1.8x |
| Qwen3-8B | 369,800 | 3.59x | 4.48x → 2.53x | 3.59x → 3.95x | 4.06x → 4.77x | 1.8x |
| Qwen3-8B | 554,700 | 3.58x | 4.44x → 2.51x | 3.58x → 4.03x | 4.03x → 4.81x | 1.8x |

## What the fabric clock is worth, and what it is not

`power.fabric_clock_hz` is `assumed` at 1.0 GHz and it has been read as setting
the compute roof on both sides. **It does not.** It is read in one place, `Technology.clock_frequency_hz`, and consumed in one, the clock leg of the static-power
term; the compute roof comes from `compute.format_roofs_ops_s` over the anchor die
area, scaled by node logic density, and never reads it. Where it *is* load-bearing is
the `latency` block: `pipeline_fill_drain_s` (32 fabric cycles) and `sequencer_issue_decode_s`
(3 fabric cycles) are both derived against it and **neither reads it**, so moving the
clock alone silently falsifies two constants that sit on every token's critical path on
both sides. This table moves all three together, which is the only way the question has
an answer that means anything.

The last rows are this repository's own **routed ASAP7** blocks, at the fmax each
artifact records. ASAP7 is a *predictive* academic PDK -- not a foundry PDK, not
silicon -- and `docs/METHODOLOGY.md` section 9 forbids scaling a frequency from it to
N6/N5/N7/N4, so those rows are **the size of a question and never a value**. They are
here because the slowest of them is 17x below the stated clock and a reader is owed
the measurement of what that would cost rather than an argument about it.

| Fabric clock | GHz | In stated band | Qwen3-8B fixed latency/token | DeepSeek-V4-Flash-0731 @ 24,450 mm2 | DeepSeek-V4-Pro-0813 @ 138,675 mm2 | Qwen3-8B @ 4,075 mm2 |
|---|---:|---|---:|---:|---:|---:|
| `band_low` | 0.5000 | yes | 11.53 us | 4.82x | 3.27x | 14.79x |
| `stated` | 1.0000 | yes | 6.82 us | 4.82x | 3.27x | 14.79x |
| `band_high` | 2.0000 | yes | 4.46 us | 4.82x | 3.27x | 14.79x |
| `asap7_reduction_s8_g2` | 1.2874 | yes | 5.77 us | 4.82x | 3.27x | 14.79x |
| `asap7_add_bf16_sram_engine` | 0.2391 | **no** | 21.83 us | 4.82x | 3.27x | 14.79x |
| `asap7_matmul_bf16_sram_engine` | 0.0580 | **no** | 83.47 us | 4.82x | 3.27x | 14.79x |

## What the ROM bit-cell ratio is worth, executed rather than declared

`rom.cell_to_sram_cell_area_ratio` decides how much weight fits per mm2, which
decides how many devices a model needs, which decides mesh diameter, which is over
half the step time at batch 1. Its stated uncertainty used to be the prose string
"1/6 to 1/4", which nothing ran and which **excluded a measurement this repository
had already committed** -- 0.1298 at 130 nm. The band is now 0.11-0.33 and every
row below is a full re-run of this study at one ratio, not an extrapolation.

The `measured_*` rows are this repository's own bit-cell measurements at nodes that
are **not** this study's node. `docs/METHODOLOGY.md` section 9 forbids scaling or
blending a 130 nm or predictive-7 nm open-PDK figure to N6/N5/N7/N4, so they are the
size of a question and never a value.

The sign is not obvious and that is why it is run: a **less** dense array is more ROM
silicon for the same weights and therefore more parallel read bandwidth, so the
capacity loss and the bandwidth gain pull opposite ways. The binding constraint on
each side is in the artifact at every point.

| ROM cell ratio | Value | In stated band | ROM capacity | Full-array sweep | DeepSeek-V4-Flash-0731 @ 24,450 mm2 | DeepSeek-V4-Pro-0813 @ 138,675 mm2 | Qwen3-8B @ 4,075 mm2 |
|---|---:|---|---:|---:|---:|---:|---:|
| `band_low` | 0.1100 | yes | 28.139 MB/mm2 | 103.4 us | 5.76x | 4.18x | 14.79x |
| `stated` | 0.3300 | yes | 9.380 MB/mm2 | 34.5 us | 4.82x | 3.27x | 14.79x |
| `band_high` | 0.3300 | yes | 9.380 MB/mm2 | 34.5 us | 4.82x | 3.27x | 14.79x |
| `measured_ihp_sg13g2_130nm` | 0.1298 | yes | 23.854 MB/mm2 | 87.7 us | — | 4.27x | 14.79x |
| `measured_asap7_7nm_via_programmed` | 0.2500 | yes | 12.381 MB/mm2 | 45.5 us | — | 3.82x | 14.79x |
| `measured_asap7_7nm_shared_source_drain` | 0.1250 | yes | 24.762 MB/mm2 | 91.0 us | — | 4.25x | 14.79x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 8 | 12,800 | 607.45 | 208.45 | 590.6 | 772.7 |
| DeepSeek-V4-Flash-0731 | 10 | 16,000 | 712.47 | 208.51 | 568.2 | 796.2 |
| DeepSeek-V4-Flash-0731 | 15 | 24,000 | 612.17 | 208.59 | 584.6 | 765.1 |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 723.04 | 208.62 | 589.4 | 845.8 |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 723.30 | 208.62 | 590.8 | 848.9 |
| DeepSeek-V4-Flash-0731 | 21 | 33,600 | 723.78 | 208.64 | 593.3 | 854.4 |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 724.00 | 208.64 | 594.3 | 856.8 |
| DeepSeek-V4-Flash-0731 | 23 | 36,800 | 724.21 | 208.65 | 595.3 | 858.9 |
| DeepSeek-V4-Flash-0731 | 24 | 38,400 | 724.41 | 208.65 | 596.2 | 860.9 |
| DeepSeek-V4-Flash-0731 | 28 | 44,800 | 725.16 | 208.66 | 599.1 | 867.6 |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 725.33 | 208.67 | 599.7 | 869.0 |
| DeepSeek-V4-Flash-0731 | 31 | 49,600 | 725.65 | 208.67 | 600.8 | 871.5 |
| DeepSeek-V4-Flash-0731 | 36 | 57,600 | 726.40 | 208.68 | 603.0 | 876.6 |
| DeepSeek-V4-Flash-0731 | 43 | 68,800 | 727.34 | 208.69 | 605.1 | 881.8 |
| DeepSeek-V4-Flash-0731 | 57 | 91,200 | 729.02 | 208.71 | 607.6 | 888.5 |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 729.13 | 208.71 | 607.7 | 888.9 |
| DeepSeek-V4-Flash-0731 | 86 | 137,600 | 734.52 | 210.91 | 602.5 | 880.1 |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 734.52 | 210.91 | 602.6 | 880.4 |
| DeepSeek-V4-Flash-0731 | 114 | 182,400 | 734.52 | 210.91 | 605.6 | 886.8 |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 734.52 | 210.91 | 605.8 | 887.1 |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 737.20 | 213.10 | 604.7 | 885.3 |
| DeepSeek-V4-Flash-0731 | 202 | 323,200 | 738.07 | 213.10 | 605.8 | 888.2 |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 739.89 | 215.30 | 603.8 | 883.6 |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 743.44 | 217.49 | 604.0 | 885.3 |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 1,277.03 | 298.43 | 367.2 | 573.2 |
| DeepSeek-V4-Pro-0813 | 40 | 64,000 | 1,283.24 | 298.48 | 373.4 | 590.6 |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 1,290.74 | 298.53 | 378.3 | 605.5 |
| DeepSeek-V4-Pro-0813 | 76 | 121,600 | 1,298.12 | 300.87 | 370.4 | 587.3 |
| DeepSeek-V4-Pro-0813 | 80 | 128,000 | 1,298.12 | 300.87 | 371.3 | 589.7 |
| DeepSeek-V4-Pro-0813 | 82 | 131,200 | 1,298.12 | 300.87 | 371.8 | 590.9 |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 1,298.12 | 300.87 | 372.9 | 593.5 |
| DeepSeek-V4-Pro-0813 | 94 | 150,400 | 1,298.12 | 300.87 | 374.1 | 596.8 |
| DeepSeek-V4-Pro-0813 | 111 | 177,600 | 1,298.12 | 300.87 | 376.6 | 603.2 |
| DeepSeek-V4-Pro-0813 | 112 | 179,200 | 1,298.12 | 300.87 | 376.7 | 603.5 |
| DeepSeek-V4-Pro-0813 | 113 | 180,800 | 1,298.12 | 300.87 | 376.9 | 603.8 |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 1,298.12 | 300.87 | 377.2 | 604.7 |
| DeepSeek-V4-Pro-0813 | 125 | 200,000 | 1,298.12 | 300.87 | 378.2 | 607.2 |
| DeepSeek-V4-Pro-0813 | 144 | 230,400 | 1,300.90 | 300.87 | 379.4 | 611.4 |
| DeepSeek-V4-Pro-0813 | 146 | 233,600 | 1,301.29 | 303.18 | 374.2 | 597.4 |
| DeepSeek-V4-Pro-0813 | 150 | 240,000 | 1,301.29 | 303.18 | 374.7 | 598.5 |
| DeepSeek-V4-Pro-0813 | 170 | 272,000 | 1,301.29 | 303.18 | 376.5 | 603.0 |
| DeepSeek-V4-Pro-0813 | 171 | 273,600 | 1,301.29 | 303.18 | 376.5 | 603.3 |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 1,301.29 | 303.18 | 376.7 | 603.7 |
| DeepSeek-V4-Pro-0813 | 203 | 324,800 | 1,304.07 | 303.18 | 378.3 | 608.7 |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 1,304.47 | 305.50 | 376.3 | 602.9 |
| DeepSeek-V4-Pro-0813 | 255 | 408,000 | 1,304.47 | 305.50 | 377.5 | 606.1 |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 1,310.43 | 307.82 | 377.6 | 607.8 |
| DeepSeek-V4-Pro-0813 | 1,358 | 2,172,800 | 1,354.91 | 340.25 | 371.7 | 596.8 |
| Qwen3-8B | 1 | 1,600 | 0.00 | 0.00 | 352.5 | 352.5 |
| Qwen3-8B | 2 | 3,200 | 176.51 | 173.78 | 498.9 | 499.6 |
| Qwen3-8B | 3 | 4,800 | 176.95 | 174.11 | 631.1 | 632.2 |
| Qwen3-8B | 4 | 6,400 | 177.17 | 174.27 | 727.5 | 729.0 |
| Qwen3-8B | 6 | 9,600 | 177.38 | 174.44 | 858.7 | 860.9 |
| Qwen3-8B | 8 | 12,800 | 177.49 | 174.52 | 943.8 | 946.4 |
| Qwen3-8B | 25 | 40,000 | 177.72 | 174.69 | 1,182.9 | 1,187.1 |
| Qwen3-8B | 29 | 46,400 | 177.73 | 174.70 | 1,202.6 | 1,207.0 |
| Qwen3-8B | 31 | 49,600 | 177.74 | 174.70 | 1,210.8 | 1,215.3 |
| Qwen3-8B | 32 | 51,200 | 177.74 | 174.70 | 1,214.5 | 1,219.0 |
| Qwen3-8B | 38 | 60,800 | 177.75 | 174.71 | 1,233.2 | 1,237.8 |
| Qwen3-8B | 50 | 80,000 | 177.77 | 174.73 | 1,257.8 | 1,262.7 |
| Qwen3-8B | 58 | 92,800 | 177.78 | 174.73 | 1,268.9 | 1,273.9 |
| Qwen3-8B | 75 | 120,000 | 182.00 | 176.93 | 1,225.4 | 1,233.1 |
| Qwen3-8B | 87 | 139,200 | 182.00 | 176.93 | 1,239.5 | 1,247.3 |
| Qwen3-8B | 100 | 160,000 | 182.00 | 176.93 | 1,251.2 | 1,259.2 |
| Qwen3-8B | 116 | 185,600 | 182.00 | 176.93 | 1,262.2 | 1,270.3 |
| Qwen3-8B | 173 | 276,800 | 184.20 | 179.13 | 1,258.3 | 1,266.4 |
| Qwen3-8B | 231 | 369,600 | 186.39 | 181.32 | 1,254.9 | 1,262.9 |
| Qwen3-8B | 347 | 555,200 | 188.59 | 183.51 | 1,263.0 | 1,271.2 |

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
| DeepSeek-V4-Flash-0731 | 8 | 12,800 | 388.9 | 590.6 | — | tensor | 607.45 | 35.9% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 10 | 16,000 | 388.1 | 568.2 | 551.7 | tensor | 712.47 | 40.5% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 15 | 24,000 | 387.2 | 584.0 | 584.6 | hybrid | 612.17 | 35.8% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 386.4 | 589.4 | 566.8 | tensor | 723.04 | 42.6% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 386.3 | 590.8 | 571.1 | tensor | 723.30 | 42.7% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 21 | 33,600 | 385.9 | 593.3 | 578.7 | tensor | 723.78 | 42.9% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 385.7 | 594.3 | 582.1 | tensor | 724.00 | 43.0% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 23 | 36,800 | 385.5 | 595.3 | 585.2 | tensor | 724.21 | 43.1% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 24 | 38,400 | 385.3 | 596.2 | 588.0 | tensor | 724.41 | 43.2% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 28 | 44,800 | 384.4 | 599.1 | 577.8 | tensor | 725.16 | 43.4% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 384.2 | 599.7 | 580.4 | tensor | 725.33 | 43.5% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 31 | 49,600 | 383.8 | 600.8 | 585.0 | tensor | 725.65 | 43.6% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 36 | 57,600 | 382.7 | 603.0 | 579.0 | tensor | 726.40 | 43.8% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 43 | 68,800 | 381.2 | 605.1 | 577.7 | tensor | 727.34 | 44.0% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 57 | 91,200 | 381.2 | 607.6 | 575.5 | tensor | 729.02 | 44.3% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 381.2 | 607.7 | 576.8 | tensor | 729.13 | 44.3% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 86 | 137,600 | 381.2 | 294.2 | 602.5 | hybrid | 734.52 | 44.3% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 381.2 | 294.1 | 602.6 | hybrid | 734.52 | 44.3% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 114 | 182,400 | 381.2 | 292.2 | 605.6 | hybrid | 734.52 | 44.5% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 381.2 | 292.1 | 605.8 | hybrid | 734.52 | 44.5% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 381.2 | 270.6 | 604.7 | hybrid | 737.20 | 44.6% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 202 | 323,200 | 381.2 | 268.1 | 605.8 | hybrid | 738.07 | 44.7% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 381.2 | 257.4 | 603.8 | hybrid | 739.89 | 44.7% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 381.2 | 242.4 | 604.0 | hybrid | 743.44 | 44.9% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 133.4 | 367.2 | 320.5 | tensor | 1,277.03 | 46.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 40 | 64,000 | 133.1 | 373.4 | 327.6 | tensor | 1,283.24 | 47.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 132.6 | 378.3 | 319.2 | tensor | 1,290.74 | 48.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 76 | 121,600 | 132.5 | 134.6 | 370.4 | hybrid | 1,298.12 | 48.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 80 | 128,000 | 132.5 | 134.5 | 371.3 | hybrid | 1,298.12 | 48.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 82 | 131,200 | 132.5 | 134.4 | 371.8 | hybrid | 1,298.12 | 48.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 132.5 | 134.3 | 372.9 | hybrid | 1,298.12 | 48.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 94 | 150,400 | 132.5 | 134.0 | 374.1 | hybrid | 1,298.12 | 48.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 111 | 177,600 | 132.5 | 133.3 | 376.6 | hybrid | 1,298.12 | 48.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 112 | 179,200 | 132.5 | 133.3 | 376.7 | hybrid | 1,298.12 | 48.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 113 | 180,800 | 132.5 | 133.2 | 376.9 | hybrid | 1,298.12 | 48.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 132.5 | 133.1 | 377.2 | hybrid | 1,298.12 | 49.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 125 | 200,000 | 132.5 | 132.7 | 378.2 | hybrid | 1,298.12 | 49.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 144 | 230,400 | 132.5 | 131.9 | 379.4 | hybrid | 1,300.90 | 49.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 146 | 233,600 | 132.5 | 115.1 | 374.2 | hybrid | 1,301.29 | 48.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 150 | 240,000 | 132.5 | 114.9 | 374.7 | hybrid | 1,301.29 | 48.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 170 | 272,000 | 132.5 | 114.1 | 376.5 | hybrid | 1,301.29 | 49.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 171 | 273,600 | 132.5 | 114.0 | 376.5 | hybrid | 1,301.29 | 49.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 132.5 | 113.9 | 376.7 | hybrid | 1,301.29 | 49.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 203 | 324,800 | 132.5 | 112.6 | 378.3 | hybrid | 1,304.07 | 49.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 132.5 | 104.6 | 376.3 | hybrid | 1,304.47 | 49.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 255 | 408,000 | 132.5 | 103.6 | 377.5 | hybrid | 1,304.47 | 49.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 132.5 | 96.2 | 377.6 | hybrid | 1,310.43 | 49.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 1358 | 2,172,800 | 132.5 | 59.2 | 371.7 | hybrid | 1,354.91 | 50.4% | link_latency |
| Qwen3-8B | 1 | 1,600 | — | — | — | none | 0.00 | 0.0% | weight_read |
| Qwen3-8B | 2 | 3,200 | 323.5 | 498.9 | — | tensor | 176.51 | 8.8% | weight_read |
| Qwen3-8B | 3 | 4,800 | 323.3 | 631.1 | — | tensor | 176.95 | 11.2% | weight_read |
| Qwen3-8B | 4 | 6,400 | 323.2 | 727.5 | — | tensor | 177.17 | 12.9% | layer_fixed_latency |
| Qwen3-8B | 6 | 9,600 | 323.0 | 858.7 | — | tensor | 177.38 | 15.2% | layer_fixed_latency |
| Qwen3-8B | 8 | 12,800 | 322.7 | 943.8 | — | tensor | 177.49 | 16.8% | layer_fixed_latency |
| Qwen3-8B | 25 | 40,000 | 320.2 | 1,182.9 | 864.7 | tensor | 177.72 | 21.0% | layer_fixed_latency |
| Qwen3-8B | 29 | 46,400 | 319.7 | 1,202.6 | 908.4 | tensor | 177.73 | 21.4% | layer_fixed_latency |
| Qwen3-8B | 31 | 49,600 | 319.4 | 1,210.8 | 927.3 | tensor | 177.74 | 21.5% | layer_fixed_latency |
| Qwen3-8B | 32 | 51,200 | 319.3 | 1,214.5 | 936.2 | tensor | 177.74 | 21.6% | layer_fixed_latency |
| Qwen3-8B | 38 | 60,800 | 318.7 | 1,233.2 | 920.0 | tensor | 177.75 | 21.9% | layer_fixed_latency |
| Qwen3-8B | 50 | 80,000 | 318.7 | 1,257.8 | 898.8 | tensor | 177.77 | 22.4% | layer_fixed_latency |
| Qwen3-8B | 58 | 92,800 | 318.7 | 1,268.9 | 901.2 | tensor | 177.78 | 22.6% | layer_fixed_latency |
| Qwen3-8B | 75 | 120,000 | 318.7 | 785.2 | 1,225.4 | hybrid | 182.00 | 22.3% | layer_fixed_latency |
| Qwen3-8B | 87 | 139,200 | 318.7 | 788.1 | 1,239.5 | hybrid | 182.00 | 22.6% | layer_fixed_latency |
| Qwen3-8B | 100 | 160,000 | 318.7 | 790.4 | 1,251.2 | hybrid | 182.00 | 22.8% | layer_fixed_latency |
| Qwen3-8B | 116 | 185,600 | 318.7 | 792.6 | 1,262.2 | hybrid | 182.00 | 23.0% | layer_fixed_latency |
| Qwen3-8B | 173 | 276,800 | 318.7 | 792.1 | 1,258.3 | hybrid | 184.20 | 23.2% | layer_fixed_latency |
| Qwen3-8B | 231 | 369,600 | 318.7 | 792.0 | 1,254.9 | hybrid | 186.39 | 23.4% | layer_fixed_latency |
| Qwen3-8B | 347 | 555,200 | 318.7 | 792.8 | 1,263.0 | hybrid | 188.59 | 23.8% | layer_fixed_latency |

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
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x5 | Qwen3-8B | 5 | pipeline | rom_package_ucie | rom_board_serdes | 4 | 0.14 us | 710,756.8 tok/s | 7,107,567.5 tok/s | 3 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.04 us; 1 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.10 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x5 | Qwen3-8B | 5 | tensor | rom_package_ucie | rom_board_serdes | 144 | 18.10 us | 5,523.9 tok/s | 55,238.6 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 72 x all_reduce span 2 on rom_board_serdes (traversals 2.2) = 16.33 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x5 | Qwen3-8B | 5 | hybrid | rom_package_ucie | rom_board_serdes | 73 | 1.88 us | 53,295.6 tok/s | 532,956.1 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 1 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.10 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x5 | Qwen3-8B | 5 | pipeline | nvlink5 | infiniband_ndr | 4 | 4.84 us | 20,676.5 tok/s | 206,765.0 tok/s | 4 x point_to_point span 2 on nvlink5 (traversals 1.0) = 4.84 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer_n5 | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x5 | Qwen3-8B | 5 | tensor | nvlink5 | infiniband_ndr | 72 | 174.37 us | 573.5 tok/s | 5,734.8 tok/s | 72 x all_reduce span 5 on nvlink5 (traversals 2.0) = 174.37 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x49 | Qwen3-8B | 49 | pipeline | rom_package_ucie | rom_board_serdes | 35 | 1.16 us | 86,080.4 tok/s | 860,803.8 tok/s | 27 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.33 us; 8 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.84 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-hw-tensor-x49 | Qwen3-8B | 49 | tensor | rom_package_ucie | rom_board_serdes | 144 | 50.20 us | 1,992.1 tok/s | 19,920.6 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 72 x all_reduce span 13 on rom_board_serdes (traversals 6.6) = 48.43 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49 | Qwen3-8B | 49 | hybrid | rom_package_ucie | rom_board_serdes | 84 | 3.03 us | 33,042.7 tok/s | 330,426.8 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 12 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.25 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x49 | Qwen3-8B | 49 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6 | Qwen3-8B | 6 | pipeline | on_wafer_n5 | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x49 | Qwen3-8B | 49 | tensor | nvlink5 | infiniband_ndr | 144 | 497.17 us | 201.1 tok/s | 2,011.4 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 322.65 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x6 | Qwen3-8B | 6 | tensor | on_wafer_n5 | rom_wafer_serdes | 144 | 170.53 us | 586.4 tok/s | 5,864.2 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us; 72 x all_reduce span 6 on rom_wafer_serdes (traversals 4.4) = 31.93 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x49 | Qwen3-8B | 49 | hybrid | nvlink5 | infiniband_ndr | 78 | 187.68 us | 532.8 tok/s | 5,328.1 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x6 | Qwen3-8B | 6 | hybrid | on_wafer_n5 | rom_wafer_serdes | 77 | 139.11 us | 718.9 tok/s | 7,188.7 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us; 5 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.51 us |
| Qwen3-8B/b200_sxm-x2-pipeline | Qwen3-8B | 2 | pipeline | nvlink5 | infiniband_ndr | 1 | 1.21 us | 82,706.0 tok/s | 827,059.9 tok/s | 1 x point_to_point span 2 on nvlink5 (traversals 1.0) = 1.21 us |
| Qwen3-8B/b200_sxm-x2-tensor | Qwen3-8B | 2 | tensor | nvlink5 | infiniband_ndr | 72 | 173.78 us | 575.4 tok/s | 5,754.3 tok/s | 72 x all_reduce span 2 on nvlink5 (traversals 2.0) = 173.78 us |
| Qwen3-8B/b200_sxm-x2-nvl72-tensor | Qwen3-8B | 2 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 173.78 us | 575.4 tok/s | 5,754.3 tok/s | 72 x all_reduce span 2 on nvlink5_nvl72 (traversals 2.0) = 173.78 us |
| Qwen3-8B/b200_sxm-x3-pipeline | Qwen3-8B | 3 | pipeline | nvlink5 | infiniband_ndr | 2 | 2.42 us | 41,353.0 tok/s | 413,530.0 tok/s | 2 x point_to_point span 2 on nvlink5 (traversals 1.0) = 2.42 us |
| Qwen3-8B/b200_sxm-x3-tensor | Qwen3-8B | 3 | tensor | nvlink5 | infiniband_ndr | 72 | 174.11 us | 574.3 tok/s | 5,743.5 tok/s | 72 x all_reduce span 3 on nvlink5 (traversals 2.0) = 174.11 us |
| Qwen3-8B/b200_sxm-x3-nvl72-tensor | Qwen3-8B | 3 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.11 us | 574.3 tok/s | 5,743.5 tok/s | 72 x all_reduce span 3 on nvlink5_nvl72 (traversals 2.0) = 174.11 us |
| Qwen3-8B/b200_sxm-x4-pipeline | Qwen3-8B | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 3.63 us | 27,568.7 tok/s | 275,686.6 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.63 us |
| Qwen3-8B/b200_sxm-x4-tensor | Qwen3-8B | 4 | tensor | nvlink5 | infiniband_ndr | 72 | 174.27 us | 573.8 tok/s | 5,738.1 tok/s | 72 x all_reduce span 4 on nvlink5 (traversals 2.0) = 174.27 us |
| Qwen3-8B/b200_sxm-x4-nvl72-tensor | Qwen3-8B | 4 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.27 us | 573.8 tok/s | 5,738.1 tok/s | 72 x all_reduce span 4 on nvlink5_nvl72 (traversals 2.0) = 174.27 us |
| Qwen3-8B/b200_sxm-x6-pipeline | Qwen3-8B | 6 | pipeline | nvlink5 | infiniband_ndr | 5 | 6.05 us | 16,541.2 tok/s | 165,412.0 tok/s | 5 x point_to_point span 2 on nvlink5 (traversals 1.0) = 6.05 us |
| Qwen3-8B/b200_sxm-x6-tensor | Qwen3-8B | 6 | tensor | nvlink5 | infiniband_ndr | 72 | 174.44 us | 573.3 tok/s | 5,732.7 tok/s | 72 x all_reduce span 6 on nvlink5 (traversals 2.0) = 174.44 us |
| Qwen3-8B/b200_sxm-x6-nvl72-tensor | Qwen3-8B | 6 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.44 us | 573.3 tok/s | 5,732.7 tok/s | 72 x all_reduce span 6 on nvlink5_nvl72 (traversals 2.0) = 174.44 us |
| Qwen3-8B/b200_sxm-x8-pipeline | Qwen3-8B | 8 | pipeline | nvlink5 | infiniband_ndr | 7 | 8.46 us | 11,815.1 tok/s | 118,151.4 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.46 us |
| Qwen3-8B/b200_sxm-x8-tensor | Qwen3-8B | 8 | tensor | nvlink5 | infiniband_ndr | 72 | 174.52 us | 573.0 tok/s | 5,730.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us |
| Qwen3-8B/b200_sxm-x8-nvl72-tensor | Qwen3-8B | 8 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.52 us | 573.0 tok/s | 5,730.0 tok/s | 72 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 174.52 us |
| Qwen3-8B/b200_sxm-x25-pipeline | Qwen3-8B | 25 | pipeline | nvlink5 | infiniband_ndr | 24 | 31.97 us | 3,127.7 tok/s | 31,276.7 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x25-tensor | Qwen3-8B | 25 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x25-hybrid | Qwen3-8B | 25 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x25-nvl72-tensor | Qwen3-8B | 25 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.69 us | 572.5 tok/s | 5,724.5 tok/s | 72 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 174.69 us |
| Qwen3-8B/b200_sxm-x29-pipeline | Qwen3-8B | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x29-tensor | Qwen3-8B | 29 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x29-hybrid | Qwen3-8B | 29 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x29-nvl72-tensor | Qwen3-8B | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.70 us | 572.4 tok/s | 5,724.2 tok/s | 72 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 174.70 us |
| Qwen3-8B/b200_sxm-x31-pipeline | Qwen3-8B | 31 | pipeline | nvlink5 | infiniband_ndr | 30 | 39.23 us | 2,549.2 tok/s | 25,492.5 tok/s | 27 x point_to_point span 2 on nvlink5 (traversals 1.0) = 32.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x31-tensor | Qwen3-8B | 31 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x31-hybrid | Qwen3-8B | 31 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x31-nvl72-tensor | Qwen3-8B | 31 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.70 us | 572.4 tok/s | 5,724.0 tok/s | 72 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 174.70 us |
| Qwen3-8B/b200_sxm-x32-pipeline | Qwen3-8B | 32 | pipeline | nvlink5 | infiniband_ndr | 31 | 40.44 us | 2,473.0 tok/s | 24,730.2 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.85 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x32-tensor | Qwen3-8B | 32 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x32-hybrid | Qwen3-8B | 32 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x32-nvl72-tensor | Qwen3-8B | 32 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.70 us | 572.4 tok/s | 5,723.9 tok/s | 72 x all_reduce span 32 on nvlink5_nvl72 (traversals 2.0) = 174.70 us |
| Qwen3-8B/b200_sxm-x38-pipeline | Qwen3-8B | 38 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x38-tensor | Qwen3-8B | 38 | tensor | nvlink5 | infiniband_ndr | 144 | 495.15 us | 202.0 tok/s | 2,019.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 320.63 us |
| Qwen3-8B/b200_sxm-x38-hybrid | Qwen3-8B | 38 | hybrid | nvlink5 | infiniband_ndr | 76 | 183.30 us | 545.6 tok/s | 5,455.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x38-nvl72-tensor | Qwen3-8B | 38 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.71 us | 572.4 tok/s | 5,723.6 tok/s | 72 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 174.71 us |
| Qwen3-8B/b200_sxm-x50-pipeline | Qwen3-8B | 50 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x50-tensor | Qwen3-8B | 50 | tensor | nvlink5 | infiniband_ndr | 144 | 497.17 us | 201.1 tok/s | 2,011.4 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 322.65 us |
| Qwen3-8B/b200_sxm-x50-hybrid | Qwen3-8B | 50 | hybrid | nvlink5 | infiniband_ndr | 78 | 187.68 us | 532.8 tok/s | 5,328.1 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| Qwen3-8B/b200_sxm-x50-nvl72-tensor | Qwen3-8B | 50 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.73 us | 572.3 tok/s | 5,723.2 tok/s | 72 x all_reduce span 50 on nvlink5_nvl72 (traversals 2.0) = 174.73 us |
| Qwen3-8B/b200_sxm-x58-pipeline | Qwen3-8B | 58 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x58-tensor | Qwen3-8B | 58 | tensor | nvlink5 | infiniband_ndr | 144 | 497.81 us | 200.9 tok/s | 2,008.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 323.29 us |
| Qwen3-8B/b200_sxm-x58-hybrid | Qwen3-8B | 58 | hybrid | nvlink5 | infiniband_ndr | 79 | 189.88 us | 526.7 tok/s | 5,266.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| Qwen3-8B/b200_sxm-x58-nvl72-tensor | Qwen3-8B | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.73 us | 572.3 tok/s | 5,723.0 tok/s | 72 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 174.73 us |
| Qwen3-8B/b200_sxm-x75-pipeline | Qwen3-8B | 75 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x75-tensor | Qwen3-8B | 75 | tensor | nvlink5 | infiniband_ndr | 144 | 498.69 us | 200.5 tok/s | 2,005.3 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 324.17 us |
| Qwen3-8B/b200_sxm-x75-hybrid | Qwen3-8B | 75 | hybrid | nvlink5 | infiniband_ndr | 81 | 194.26 us | 514.8 tok/s | 5,147.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.74 us |
| Qwen3-8B/b200_sxm-x75-nvl72-tensor | Qwen3-8B | 75 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x75-nvl72-hybrid | Qwen3-8B | 75 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x87-pipeline | Qwen3-8B | 87 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x87-tensor | Qwen3-8B | 87 | tensor | nvlink5 | infiniband_ndr | 144 | 499.01 us | 200.4 tok/s | 2,004.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 324.49 us |
| Qwen3-8B/b200_sxm-x87-hybrid | Qwen3-8B | 87 | hybrid | nvlink5 | infiniband_ndr | 82 | 196.46 us | 509.0 tok/s | 5,090.1 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| Qwen3-8B/b200_sxm-x87-nvl72-tensor | Qwen3-8B | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x87-nvl72-hybrid | Qwen3-8B | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x100-pipeline | Qwen3-8B | 100 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x100-tensor | Qwen3-8B | 100 | tensor | nvlink5 | infiniband_ndr | 144 | 499.51 us | 200.2 tok/s | 2,002.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 324.99 us |
| Qwen3-8B/b200_sxm-x100-hybrid | Qwen3-8B | 100 | hybrid | nvlink5 | infiniband_ndr | 84 | 200.85 us | 497.9 tok/s | 4,978.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 26.33 us |
| Qwen3-8B/b200_sxm-x100-nvl72-tensor | Qwen3-8B | 100 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x100-nvl72-hybrid | Qwen3-8B | 100 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
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
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x56 | DeepSeek-V4-Flash-0731 | 56 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x30 | DeepSeek-V4-Flash-0731 | 30 | tensor | rom_package_ucie | rom_board_serdes | 172 | 40.98 us | 2,440.0 tok/s | 24,399.9 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 8 on rom_board_serdes (traversals 4.4) = 38.87 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x48 | DeepSeek-V4-Flash-0731 | 48 | hybrid | rom_package_ucie | rom_board_serdes | 97 | 3.27 us | 30,615.2 tok/s | 306,152.1 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 11 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.15 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x55 | DeepSeek-V4-Flash-0731 | 55 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer_n5 | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x29 | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x37 | DeepSeek-V4-Flash-0731 | 37 | hybrid | nvlink5 | infiniband_ndr | 90 | 217.23 us | 460.3 tok/s | 4,603.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x60 | DeepSeek-V4-Flash-0731 | 60 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x56 | DeepSeek-V4-Flash-0731 | 56 | tensor | rom_package_ucie | rom_board_serdes | 172 | 59.97 us | 1,667.6 tok/s | 16,675.9 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 14 on rom_board_serdes (traversals 6.6) = 57.85 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | DeepSeek-V4-Flash-0731 | 56 | hybrid | rom_package_ucie | rom_board_serdes | 99 | 3.48 us | 28,773.2 tok/s | 287,732.3 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 13 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.36 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x60 | DeepSeek-V4-Flash-0731 | 60 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7 | DeepSeek-V4-Flash-0731 | 7 | pipeline | on_wafer_n5 | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-tensor-x56 | DeepSeek-V4-Flash-0731 | 56 | tensor | nvlink5 | infiniband_ndr | 172 | 593.85 us | 168.4 tok/s | 1,683.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 385.39 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x7 | DeepSeek-V4-Flash-0731 | 7 | tensor | on_wafer_n5 | rom_wafer_serdes | 172 | 203.69 us | 490.9 tok/s | 4,909.4 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us; 86 x all_reduce span 7 on rom_wafer_serdes (traversals 4.4) = 38.14 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x56 | DeepSeek-V4-Flash-0731 | 56 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.62 us | 451.2 tok/s | 4,512.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x7 | DeepSeek-V4-Flash-0731 | 7 | hybrid | on_wafer_n5 | rom_wafer_serdes | 92 | 166.16 us | 601.8 tok/s | 6,018.4 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us; 6 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.61 us |
| DSV4-Flash/b200_sxm-x8-pipeline | DeepSeek-V4-Flash-0731 | 8 | pipeline | nvlink5 | infiniband_ndr | 7 | 8.46 us | 11,815.1 tok/s | 118,151.4 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.46 us |
| DSV4-Flash/b200_sxm-x8-tensor | DeepSeek-V4-Flash-0731 | 8 | tensor | nvlink5 | infiniband_ndr | 86 | 208.45 us | 479.7 tok/s | 4,797.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us |
| DSV4-Flash/b200_sxm-x8-nvl72-tensor | DeepSeek-V4-Flash-0731 | 8 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.45 us | 479.7 tok/s | 4,797.2 tok/s | 86 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 208.45 us |
| DSV4-Flash/b200_sxm-x8-expert | DeepSeek-V4-Flash-0731 | 8 | expert | nvlink5 | infiniband_ndr | 172 | 312.24 us | 320.3 tok/s | 3,202.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on nvlink5 (traversals 1.0) = 103.79 us |
| DSV4-Flash/b200_sxm-x8-nvl72-expert | DeepSeek-V4-Flash-0731 | 8 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.24 us | 320.3 tok/s | 3,202.6 tok/s | 86 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.79 us |
| DSV4-Flash/b200_sxm-x10-pipeline | DeepSeek-V4-Flash-0731 | 10 | pipeline | nvlink5 | infiniband_ndr | 9 | 11.87 us | 8,427.0 tok/s | 84,269.7 tok/s | 8 x point_to_point span 2 on nvlink5 (traversals 1.0) = 9.67 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x10-tensor | DeepSeek-V4-Flash-0731 | 10 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x10-hybrid | DeepSeek-V4-Flash-0731 | 10 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x10-nvl72-tensor | DeepSeek-V4-Flash-0731 | 10 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.51 us | 479.6 tok/s | 4,795.9 tok/s | 86 x all_reduce span 10 on nvlink5_nvl72 (traversals 2.0) = 208.51 us |
| DSV4-Flash/b200_sxm-x10-expert | DeepSeek-V4-Flash-0731 | 10 | expert | nvlink5 | infiniband_ndr | 172 | 391.49 us | 255.4 tok/s | 2,554.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 183.03 us |
| DSV4-Flash/b200_sxm-x10-nvl72-expert | DeepSeek-V4-Flash-0731 | 10 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.18 us | 320.3 tok/s | 3,203.2 tok/s | 86 x all_reduce span 10 on nvlink5_nvl72 (traversals 2.0) = 208.51 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.67 us |
| DSV4-Flash/b200_sxm-x15-pipeline | DeepSeek-V4-Flash-0731 | 15 | pipeline | nvlink5 | infiniband_ndr | 14 | 17.91 us | 5,582.8 tok/s | 55,828.0 tok/s | 13 x point_to_point span 2 on nvlink5 (traversals 1.0) = 15.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x15-tensor | DeepSeek-V4-Flash-0731 | 15 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x15-hybrid | DeepSeek-V4-Flash-0731 | 15 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x15-nvl72-tensor | DeepSeek-V4-Flash-0731 | 15 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.59 us | 479.4 tok/s | 4,794.1 tok/s | 86 x all_reduce span 15 on nvlink5_nvl72 (traversals 2.0) = 208.59 us |
| DSV4-Flash/b200_sxm-x15-expert | DeepSeek-V4-Flash-0731 | 15 | expert | nvlink5 | infiniband_ndr | 172 | 388.67 us | 257.3 tok/s | 2,572.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 180.22 us |
| DSV4-Flash/b200_sxm-x15-nvl72-expert | DeepSeek-V4-Flash-0731 | 15 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.10 us | 320.4 tok/s | 3,204.1 tok/s | 86 x all_reduce span 15 on nvlink5_nvl72 (traversals 2.0) = 208.59 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.51 us |
| DSV4-Flash/b200_sxm-x18-pipeline | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink5 | infiniband_ndr | 17 | 22.52 us | 4,439.7 tok/s | 44,396.7 tok/s | 15 x point_to_point span 2 on nvlink5 (traversals 1.0) = 18.14 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x18-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x18-hybrid | DeepSeek-V4-Flash-0731 | 18 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x18-nvl72-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.62 us | 479.3 tok/s | 4,793.5 tok/s | 86 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 208.62 us |
| DSV4-Flash/b200_sxm-x18-expert | DeepSeek-V4-Flash-0731 | 18 | expert | nvlink5 | infiniband_ndr | 172 | 386.70 us | 258.6 tok/s | 2,586.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 179.28 us |
| DSV4-Flash/b200_sxm-x18-nvl72-expert | DeepSeek-V4-Flash-0731 | 18 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.08 us | 320.4 tok/s | 3,204.3 tok/s | 86 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 208.62 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.46 us |
| DSV4-Flash/b200_sxm-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink5 | infiniband_ndr | 18 | 23.73 us | 4,213.5 tok/s | 42,134.9 tok/s | 16 x point_to_point span 2 on nvlink5 (traversals 1.0) = 19.35 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x19-nvl72-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.62 us | 479.3 tok/s | 4,793.3 tok/s | 86 x all_reduce span 19 on nvlink5_nvl72 (traversals 2.0) = 208.62 us |
| DSV4-Flash/b200_sxm-x19-expert | DeepSeek-V4-Flash-0731 | 19 | expert | nvlink5 | infiniband_ndr | 172 | 386.46 us | 258.8 tok/s | 2,587.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 179.03 us |
| DSV4-Flash/b200_sxm-x19-nvl72-expert | DeepSeek-V4-Flash-0731 | 19 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.07 us | 320.4 tok/s | 3,204.4 tok/s | 86 x all_reduce span 19 on nvlink5_nvl72 (traversals 2.0) = 208.62 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.45 us |
| DSV4-Flash/b200_sxm-x21-pipeline | DeepSeek-V4-Flash-0731 | 21 | pipeline | nvlink5 | infiniband_ndr | 20 | 26.15 us | 3,823.9 tok/s | 38,238.7 tok/s | 18 x point_to_point span 2 on nvlink5 (traversals 1.0) = 21.76 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x21-tensor | DeepSeek-V4-Flash-0731 | 21 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x21-hybrid | DeepSeek-V4-Flash-0731 | 21 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x21-nvl72-tensor | DeepSeek-V4-Flash-0731 | 21 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.64 us | 479.3 tok/s | 4,793.0 tok/s | 86 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 208.64 us |
| DSV4-Flash/b200_sxm-x21-expert | DeepSeek-V4-Flash-0731 | 21 | expert | nvlink5 | infiniband_ndr | 172 | 386.03 us | 259.0 tok/s | 2,590.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.61 us |
| DSV4-Flash/b200_sxm-x21-nvl72-expert | DeepSeek-V4-Flash-0731 | 21 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.06 us | 320.5 tok/s | 3,204.5 tok/s | 86 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 208.64 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.42 us |
| DSV4-Flash/b200_sxm-x22-pipeline | DeepSeek-V4-Flash-0731 | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 27.36 us | 3,654.9 tok/s | 36,548.9 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 22.97 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x22-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x22-hybrid | DeepSeek-V4-Flash-0731 | 22 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x22-nvl72-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.64 us | 479.3 tok/s | 4,792.9 tok/s | 86 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 208.64 us |
| DSV4-Flash/b200_sxm-x22-expert | DeepSeek-V4-Flash-0731 | 22 | expert | nvlink5 | infiniband_ndr | 172 | 385.85 us | 259.2 tok/s | 2,591.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.42 us |
| DSV4-Flash/b200_sxm-x22-nvl72-expert | DeepSeek-V4-Flash-0731 | 22 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.06 us | 320.5 tok/s | 3,204.6 tok/s | 86 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 208.64 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.41 us |
| DSV4-Flash/b200_sxm-x23-pipeline | DeepSeek-V4-Flash-0731 | 23 | pipeline | nvlink5 | infiniband_ndr | 22 | 28.57 us | 3,500.2 tok/s | 35,002.1 tok/s | 20 x point_to_point span 2 on nvlink5 (traversals 1.0) = 24.18 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x23-tensor | DeepSeek-V4-Flash-0731 | 23 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x23-hybrid | DeepSeek-V4-Flash-0731 | 23 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x23-nvl72-tensor | DeepSeek-V4-Flash-0731 | 23 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.65 us | 479.3 tok/s | 4,792.8 tok/s | 86 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 208.65 us |
| DSV4-Flash/b200_sxm-x23-expert | DeepSeek-V4-Flash-0731 | 23 | expert | nvlink5 | infiniband_ndr | 172 | 385.68 us | 259.3 tok/s | 2,592.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.26 us |
| DSV4-Flash/b200_sxm-x23-nvl72-expert | DeepSeek-V4-Flash-0731 | 23 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.05 us | 320.5 tok/s | 3,204.6 tok/s | 86 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 208.65 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.40 us |
| DSV4-Flash/b200_sxm-x24-pipeline | DeepSeek-V4-Flash-0731 | 24 | pipeline | nvlink5 | infiniband_ndr | 23 | 29.78 us | 3,358.1 tok/s | 33,580.9 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x24-tensor | DeepSeek-V4-Flash-0731 | 24 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x24-hybrid | DeepSeek-V4-Flash-0731 | 24 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x24-nvl72-tensor | DeepSeek-V4-Flash-0731 | 24 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.65 us | 479.3 tok/s | 4,792.7 tok/s | 86 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 208.65 us |
| DSV4-Flash/b200_sxm-x24-expert | DeepSeek-V4-Flash-0731 | 24 | expert | nvlink5 | infiniband_ndr | 172 | 385.19 us | 259.6 tok/s | 2,596.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.10 us |
| DSV4-Flash/b200_sxm-x24-nvl72-expert | DeepSeek-V4-Flash-0731 | 24 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.05 us | 320.5 tok/s | 3,204.7 tok/s | 86 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 208.65 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.40 us |
| DSV4-Flash/b200_sxm-x28-pipeline | DeepSeek-V4-Flash-0731 | 28 | pipeline | nvlink5 | infiniband_ndr | 27 | 35.60 us | 2,809.0 tok/s | 28,089.9 tok/s | 24 x point_to_point span 2 on nvlink5 (traversals 1.0) = 29.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x28-tensor | DeepSeek-V4-Flash-0731 | 28 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x28-hybrid | DeepSeek-V4-Flash-0731 | 28 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x28-nvl72-tensor | DeepSeek-V4-Flash-0731 | 28 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.66 us | 479.2 tok/s | 4,792.4 tok/s | 86 x all_reduce span 28 on nvlink5_nvl72 (traversals 2.0) = 208.66 us |
| DSV4-Flash/b200_sxm-x28-expert | DeepSeek-V4-Flash-0731 | 28 | expert | nvlink5 | infiniband_ndr | 172 | 384.68 us | 260.0 tok/s | 2,599.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.60 us |
| DSV4-Flash/b200_sxm-x28-nvl72-expert | DeepSeek-V4-Flash-0731 | 28 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.03 us | 320.5 tok/s | 3,204.8 tok/s | 86 x all_reduce span 28 on nvlink5_nvl72 (traversals 2.0) = 208.66 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.37 us |
| DSV4-Flash/b200_sxm-x29-pipeline | DeepSeek-V4-Flash-0731 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x29-tensor | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x29-hybrid | DeepSeek-V4-Flash-0731 | 29 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x29-nvl72-tensor | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.67 us | 479.2 tok/s | 4,792.3 tok/s | 86 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 208.67 us |
| DSV4-Flash/b200_sxm-x29-expert | DeepSeek-V4-Flash-0731 | 29 | expert | nvlink5 | infiniband_ndr | 172 | 384.58 us | 260.0 tok/s | 2,600.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.50 us |
| DSV4-Flash/b200_sxm-x29-nvl72-expert | DeepSeek-V4-Flash-0731 | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.03 us | 320.5 tok/s | 3,204.8 tok/s | 86 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 208.67 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.36 us |
| DSV4-Flash/b200_sxm-x31-pipeline | DeepSeek-V4-Flash-0731 | 31 | pipeline | nvlink5 | infiniband_ndr | 30 | 39.23 us | 2,549.2 tok/s | 25,492.5 tok/s | 27 x point_to_point span 2 on nvlink5 (traversals 1.0) = 32.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x31-tensor | DeepSeek-V4-Flash-0731 | 31 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x31-hybrid | DeepSeek-V4-Flash-0731 | 31 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x31-nvl72-tensor | DeepSeek-V4-Flash-0731 | 31 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.67 us | 479.2 tok/s | 4,792.2 tok/s | 86 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 208.67 us |
| DSV4-Flash/b200_sxm-x31-expert | DeepSeek-V4-Flash-0731 | 31 | expert | nvlink5 | infiniband_ndr | 172 | 384.39 us | 260.2 tok/s | 2,601.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.31 us |
| DSV4-Flash/b200_sxm-x31-nvl72-expert | DeepSeek-V4-Flash-0731 | 31 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.02 us | 320.5 tok/s | 3,204.9 tok/s | 86 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 208.67 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.35 us |
| DSV4-Flash/b200_sxm-x36-pipeline | DeepSeek-V4-Flash-0731 | 36 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/b200_sxm-x36-tensor | DeepSeek-V4-Flash-0731 | 36 | tensor | nvlink5 | infiniband_ndr | 172 | 591.43 us | 169.1 tok/s | 1,690.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 382.98 us |
| DSV4-Flash/b200_sxm-x36-hybrid | DeepSeek-V4-Flash-0731 | 36 | hybrid | nvlink5 | infiniband_ndr | 90 | 217.23 us | 460.3 tok/s | 4,603.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/b200_sxm-x36-nvl72-tensor | DeepSeek-V4-Flash-0731 | 36 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.68 us | 479.2 tok/s | 4,792.0 tok/s | 86 x all_reduce span 36 on nvlink5_nvl72 (traversals 2.0) = 208.68 us |
| DSV4-Flash/b200_sxm-x36-expert | DeepSeek-V4-Flash-0731 | 36 | expert | nvlink5 | infiniband_ndr | 172 | 383.84 us | 260.5 tok/s | 2,605.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.91 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.93 us |
| DSV4-Flash/b200_sxm-x36-nvl72-expert | DeepSeek-V4-Flash-0731 | 36 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.01 us | 320.5 tok/s | 3,205.0 tok/s | 86 x all_reduce span 36 on nvlink5_nvl72 (traversals 2.0) = 208.68 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.33 us |
| DSV4-Flash/b200_sxm-x43-pipeline | DeepSeek-V4-Flash-0731 | 43 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x43-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x43-hybrid | DeepSeek-V4-Flash-0731 | 43 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x43-nvl72-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.69 us | 479.2 tok/s | 4,791.7 tok/s | 86 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 208.69 us |
| DSV4-Flash/b200_sxm-x43-expert | DeepSeek-V4-Flash-0731 | 43 | expert | nvlink5 | infiniband_ndr | 172 | 383.36 us | 260.9 tok/s | 2,608.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.81 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.55 us |
| DSV4-Flash/b200_sxm-x43-nvl72-expert | DeepSeek-V4-Flash-0731 | 43 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.00 us | 320.5 tok/s | 3,205.1 tok/s | 86 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 208.69 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.31 us |
| DSV4-Flash/b200_sxm-x57-pipeline | DeepSeek-V4-Flash-0731 | 57 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x57-tensor | DeepSeek-V4-Flash-0731 | 57 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x57-hybrid | DeepSeek-V4-Flash-0731 | 57 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x57-nvl72-tensor | DeepSeek-V4-Flash-0731 | 57 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.71 us | 479.1 tok/s | 4,791.4 tok/s | 86 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 208.71 us |
| DSV4-Flash/b200_sxm-x57-expert | DeepSeek-V4-Flash-0731 | 57 | expert | nvlink5 | infiniband_ndr | 172 | 382.76 us | 261.3 tok/s | 2,612.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.69 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.06 us |
| DSV4-Flash/b200_sxm-x57-nvl72-expert | DeepSeek-V4-Flash-0731 | 57 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.2 tok/s | 86 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 208.71 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.28 us |
| DSV4-Flash/b200_sxm-x58-pipeline | DeepSeek-V4-Flash-0731 | 58 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x58-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x58-hybrid | DeepSeek-V4-Flash-0731 | 58 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x58-nvl72-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.71 us | 479.1 tok/s | 4,791.4 tok/s | 86 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 208.71 us |
| DSV4-Flash/b200_sxm-x58-expert | DeepSeek-V4-Flash-0731 | 58 | expert | nvlink5 | infiniband_ndr | 172 | 382.73 us | 261.3 tok/s | 2,612.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.69 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.04 us |
| DSV4-Flash/b200_sxm-x58-nvl72-expert | DeepSeek-V4-Flash-0731 | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.2 tok/s | 86 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 208.71 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.28 us |
| DSV4-Flash/b200_sxm-x86-pipeline | DeepSeek-V4-Flash-0731 | 86 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x86-tensor | DeepSeek-V4-Flash-0731 | 86 | tensor | nvlink5 | infiniband_ndr | 172 | 596.04 us | 167.8 tok/s | 1,677.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 387.59 us |
| DSV4-Flash/b200_sxm-x86-hybrid | DeepSeek-V4-Flash-0731 | 86 | hybrid | nvlink5 | infiniband_ndr | 96 | 230.39 us | 434.0 tok/s | 4,340.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| DSV4-Flash/b200_sxm-x86-nvl72-tensor | DeepSeek-V4-Flash-0731 | 86 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x86-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 86 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x86-expert | DeepSeek-V4-Flash-0731 | 86 | expert | nvlink5 | infiniband_ndr | 172 | 382.17 us | 261.7 tok/s | 2,616.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.61 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.56 us |
| DSV4-Flash/b200_sxm-x86-nvl72-expert | DeepSeek-V4-Flash-0731 | 86 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 384.28 us | 260.2 tok/s | 2,602.3 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.56 us |
| DSV4-Flash/b200_sxm-x87-pipeline | DeepSeek-V4-Flash-0731 | 87 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x87-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink5 | infiniband_ndr | 172 | 596.04 us | 167.8 tok/s | 1,677.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 387.59 us |
| DSV4-Flash/b200_sxm-x87-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink5 | infiniband_ndr | 96 | 230.39 us | 434.0 tok/s | 4,340.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| DSV4-Flash/b200_sxm-x87-nvl72-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x87-expert | DeepSeek-V4-Flash-0731 | 87 | expert | nvlink5 | infiniband_ndr | 172 | 382.16 us | 261.7 tok/s | 2,616.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.61 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.55 us |
| DSV4-Flash/b200_sxm-x87-nvl72-expert | DeepSeek-V4-Flash-0731 | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 384.27 us | 260.2 tok/s | 2,602.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.55 us |
| DSV4-Flash/b200_sxm-x114-pipeline | DeepSeek-V4-Flash-0731 | 114 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x114-tensor | DeepSeek-V4-Flash-0731 | 114 | tensor | nvlink5 | infiniband_ndr | 172 | 597.07 us | 167.5 tok/s | 1,674.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 388.61 us |
| DSV4-Flash/b200_sxm-x114-hybrid | DeepSeek-V4-Flash-0731 | 114 | hybrid | nvlink5 | infiniband_ndr | 100 | 239.17 us | 418.1 tok/s | 4,181.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| DSV4-Flash/b200_sxm-x114-nvl72-tensor | DeepSeek-V4-Flash-0731 | 114 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x114-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 114 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x114-expert | DeepSeek-V4-Flash-0731 | 114 | expert | nvlink5 | infiniband_ndr | 172 | 381.87 us | 261.9 tok/s | 2,618.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.55 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.32 us |
| DSV4-Flash/b200_sxm-x114-nvl72-expert | DeepSeek-V4-Flash-0731 | 114 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 384.04 us | 260.4 tok/s | 2,603.9 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.32 us |
| DSV4-Flash/b200_sxm-x116-pipeline | DeepSeek-V4-Flash-0731 | 116 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x116-tensor | DeepSeek-V4-Flash-0731 | 116 | tensor | nvlink5 | infiniband_ndr | 172 | 597.07 us | 167.5 tok/s | 1,674.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 388.61 us |
| DSV4-Flash/b200_sxm-x116-hybrid | DeepSeek-V4-Flash-0731 | 116 | hybrid | nvlink5 | infiniband_ndr | 100 | 239.17 us | 418.1 tok/s | 4,181.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| DSV4-Flash/b200_sxm-x116-nvl72-tensor | DeepSeek-V4-Flash-0731 | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x116-expert | DeepSeek-V4-Flash-0731 | 116 | expert | nvlink5 | infiniband_ndr | 172 | 381.86 us | 261.9 tok/s | 2,618.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.55 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.31 us |
| DSV4-Flash/b200_sxm-x116-nvl72-expert | DeepSeek-V4-Flash-0731 | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 384.02 us | 260.4 tok/s | 2,604.0 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.31 us |
| DSV4-Flash/b200_sxm-x173-pipeline | DeepSeek-V4-Flash-0731 | 173 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x173-tensor | DeepSeek-V4-Flash-0731 | 173 | tensor | nvlink5 | infiniband_ndr | 172 | 597.96 us | 167.2 tok/s | 1,672.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 389.51 us |
| DSV4-Flash/b200_sxm-x173-hybrid | DeepSeek-V4-Flash-0731 | 173 | hybrid | nvlink5 | infiniband_ndr | 107 | 254.53 us | 392.9 tok/s | 3,928.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| DSV4-Flash/b200_sxm-x173-nvl72-tensor | DeepSeek-V4-Flash-0731 | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 586.06 us | 170.6 tok/s | 1,706.3 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 88 | 213.10 us | 469.3 tok/s | 4,692.6 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x173-expert | DeepSeek-V4-Flash-0731 | 173 | expert | nvlink5 | infiniband_ndr | 172 | 381.57 us | 262.1 tok/s | 2,620.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.50 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.07 us |
| DSV4-Flash/b200_sxm-x173-nvl72-expert | DeepSeek-V4-Flash-0731 | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 382.63 us | 261.4 tok/s | 2,613.5 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 207.56 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.07 us |
| DSV4-Flash/b200_sxm-x202-pipeline | DeepSeek-V4-Flash-0731 | 202 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x202-tensor | DeepSeek-V4-Flash-0731 | 202 | tensor | nvlink5 | infiniband_ndr | 172 | 598.26 us | 167.2 tok/s | 1,671.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 26 on infiniband_ndr (traversals 2.0) = 389.80 us |
| DSV4-Flash/b200_sxm-x202-hybrid | DeepSeek-V4-Flash-0731 | 202 | hybrid | nvlink5 | infiniband_ndr | 111 | 263.30 us | 379.8 tok/s | 3,797.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 25 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 54.85 us |
| DSV4-Flash/b200_sxm-x202-nvl72-tensor | DeepSeek-V4-Flash-0731 | 202 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 586.06 us | 170.6 tok/s | 1,706.3 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x202-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 202 | hybrid | nvlink5_nvl72 | infiniband_ndr | 88 | 213.10 us | 469.3 tok/s | 4,692.6 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x202-expert | DeepSeek-V4-Flash-0731 | 202 | expert | nvlink5 | infiniband_ndr | 172 | 381.48 us | 262.1 tok/s | 2,621.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.48 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.00 us |
| DSV4-Flash/b200_sxm-x202-nvl72-expert | DeepSeek-V4-Flash-0731 | 202 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 382.56 us | 261.4 tok/s | 2,614.0 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 207.56 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.00 us |
| DSV4-Flash/b200_sxm-x231-pipeline | DeepSeek-V4-Flash-0731 | 231 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x231-tensor | DeepSeek-V4-Flash-0731 | 231 | tensor | nvlink5 | infiniband_ndr | 172 | 598.43 us | 167.1 tok/s | 1,671.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 389.97 us |
| DSV4-Flash/b200_sxm-x231-hybrid | DeepSeek-V4-Flash-0731 | 231 | hybrid | nvlink5 | infiniband_ndr | 114 | 269.88 us | 370.5 tok/s | 3,705.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 61.43 us |
| DSV4-Flash/b200_sxm-x231-nvl72-tensor | DeepSeek-V4-Flash-0731 | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 589.58 us | 169.6 tok/s | 1,696.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 89 | 215.30 us | 464.5 tok/s | 4,644.7 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x231-expert | DeepSeek-V4-Flash-0731 | 231 | expert | nvlink5 | infiniband_ndr | 172 | 381.42 us | 262.2 tok/s | 2,621.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.47 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.95 us |
| DSV4-Flash/b200_sxm-x231-nvl72-expert | DeepSeek-V4-Flash-0731 | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 382.12 us | 261.7 tok/s | 2,617.0 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 207.17 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.95 us |
| DSV4-Flash/b200_sxm-x347-pipeline | DeepSeek-V4-Flash-0731 | 347 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x347-tensor | DeepSeek-V4-Flash-0731 | 347 | tensor | nvlink5 | infiniband_ndr | 172 | 598.92 us | 167.0 tok/s | 1,669.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 390.47 us |
| DSV4-Flash/b200_sxm-x347-hybrid | DeepSeek-V4-Flash-0731 | 347 | hybrid | nvlink5 | infiniband_ndr | 128 | 300.60 us | 332.7 tok/s | 3,326.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 42 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 92.14 us |
| DSV4-Flash/b200_sxm-x347-nvl72-tensor | DeepSeek-V4-Flash-0731 | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 591.69 us | 169.0 tok/s | 1,690.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 382.98 us |
| DSV4-Flash/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 90 | 217.49 us | 459.8 tok/s | 4,597.9 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/b200_sxm-x347-expert | DeepSeek-V4-Flash-0731 | 347 | expert | nvlink5 | infiniband_ndr | 172 | 381.27 us | 262.3 tok/s | 2,622.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.82 us |
| DSV4-Flash/b200_sxm-x347-nvl72-expert | DeepSeek-V4-Flash-0731 | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 381.80 us | 261.9 tok/s | 2,619.2 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 206.98 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.82 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x335 | DeepSeek-V4-Pro-0813 | 335 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x160 | DeepSeek-V4-Pro-0813 | 160 | tensor | rom_package_ucie | rom_board_serdes | 244 | 167.31 us | 597.7 tok/s | 5,977.1 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 40 on rom_board_serdes (traversals 13.2) = 163.88 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x286 | DeepSeek-V4-Pro-0813 | 286 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 9.90 us | 10,099.3 tok/s | 100,993.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.48 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x334 | DeepSeek-V4-Pro-0813 | 334 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x6 | DeepSeek-V4-Pro-0813 | 6 | pipeline | on_wafer_n5 | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x150 | DeepSeek-V4-Pro-0813 | 150 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x3 | DeepSeek-V4-Pro-0813 | 3 | tensor | on_wafer_n5 | rom_wafer_serdes | 244 | 262.27 us | 381.3 tok/s | 3,812.8 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 27.42 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hybrid-x218 | DeepSeek-V4-Pro-0813 | 218 | hybrid | nvlink5 | infiniband_ndr | 149 | 360.45 us | 277.4 tok/s | 2,774.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 27 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 62.55 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x5 | DeepSeek-V4-Pro-0813 | 5 | hybrid | on_wafer_n5 | rom_wafer_serdes | 126 | 235.26 us | 425.1 tok/s | 4,250.6 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 4 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.41 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399 | DeepSeek-V4-Pro-0813 | 399 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x399 | DeepSeek-V4-Pro-0813 | 399 | tensor | rom_package_ucie | rom_board_serdes | 244 | 247.87 us | 403.4 tok/s | 4,034.4 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 100 on rom_board_serdes (traversals 19.8) = 244.45 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | DeepSeek-V4-Pro-0813 | 399 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 9.90 us | 10,099.3 tok/s | 100,993.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.48 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x399 | DeepSeek-V4-Pro-0813 | 399 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | DeepSeek-V4-Pro-0813 | 47 | pipeline | on_wafer_n5 | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x399 | DeepSeek-V4-Pro-0813 | 399 | tensor | nvlink5 | infiniband_ndr | 244 | 896.06 us | 111.6 tok/s | 1,116.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 50 on infiniband_ndr (traversals 2.0) = 598.16 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x47 | DeepSeek-V4-Pro-0813 | 47 | tensor | on_wafer_n5 | rom_wafer_serdes | 244 | 396.75 us | 252.1 tok/s | 2,520.5 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 47 on rom_wafer_serdes (traversals 13.2) = 161.90 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x399 | DeepSeek-V4-Pro-0813 | 399 | hybrid | nvlink5 | infiniband_ndr | 171 | 411.42 us | 243.1 tok/s | 2,430.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 49 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 113.52 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47 | DeepSeek-V4-Pro-0813 | 47 | hybrid | on_wafer_n5 | rom_wafer_serdes | 168 | 239.56 us | 417.4 tok/s | 4,174.3 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 46 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 4.71 us |
| DSV4-Pro/b200_sxm-x29-pipeline | DeepSeek-V4-Pro-0813 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 37.35 us | 2,677.5 tok/s | 26,774.9 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.40 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x29-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5 | infiniband_ndr | 244 | 871.93 us | 114.7 tok/s | 1,146.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x29-hybrid | DeepSeek-V4-Pro-0813 | 29 | hybrid | nvlink5 | infiniband_ndr | 125 | 304.85 us | 328.0 tok/s | 3,280.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x29-nvl72-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.43 us | 335.1 tok/s | 3,350.9 tok/s | 122 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 298.43 us |
| DSV4-Pro/b200_sxm-x29-expert | DeepSeek-V4-Pro-0813 | 29 | expert | nvlink5 | infiniband_ndr | 244 | 549.40 us | 182.0 tok/s | 1,820.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 294.50 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 254.90 us |
| DSV4-Pro/b200_sxm-x29-nvl72-expert | DeepSeek-V4-Pro-0813 | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.23 us | 224.6 tok/s | 2,246.0 tok/s | 122 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 298.43 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.80 us |
| DSV4-Pro/b200_sxm-x40-pipeline | DeepSeek-V4-Pro-0813 | 40 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.82 us | 1,929.6 tok/s | 19,295.9 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.56 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x40-tensor | DeepSeek-V4-Pro-0813 | 40 | tensor | nvlink5 | infiniband_ndr | 244 | 877.17 us | 114.0 tok/s | 1,140.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x40-hybrid | DeepSeek-V4-Pro-0813 | 40 | hybrid | nvlink5 | infiniband_ndr | 126 | 307.17 us | 325.6 tok/s | 3,255.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x40-nvl72-tensor | DeepSeek-V4-Pro-0813 | 40 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.48 us | 335.0 tok/s | 3,350.3 tok/s | 122 x all_reduce span 40 on nvlink5_nvl72 (traversals 2.0) = 298.48 us |
| DSV4-Pro/b200_sxm-x40-expert | DeepSeek-V4-Pro-0813 | 40 | expert | nvlink5 | infiniband_ndr | 244 | 546.73 us | 182.9 tok/s | 1,829.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.91 us |
| DSV4-Pro/b200_sxm-x40-nvl72-expert | DeepSeek-V4-Pro-0813 | 40 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.18 us | 224.6 tok/s | 2,246.3 tok/s | 122 x all_reduce span 40 on nvlink5_nvl72 (traversals 2.0) = 298.48 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.69 us |
| DSV4-Pro/b200_sxm-x58-pipeline | DeepSeek-V4-Pro-0813 | 58 | pipeline | nvlink5 | infiniband_ndr | 57 | 77.01 us | 1,298.5 tok/s | 12,984.7 tok/s | 50 x point_to_point span 2 on nvlink5 (traversals 1.0) = 60.80 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x58-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5 | infiniband_ndr | 244 | 885.04 us | 113.0 tok/s | 1,129.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 587.14 us |
| DSV4-Pro/b200_sxm-x58-hybrid | DeepSeek-V4-Pro-0813 | 58 | hybrid | nvlink5 | infiniband_ndr | 129 | 314.12 us | 318.4 tok/s | 3,183.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x58-nvl72-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.53 us | 335.0 tok/s | 3,349.8 tok/s | 122 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 298.53 us |
| DSV4-Pro/b200_sxm-x58-expert | DeepSeek-V4-Pro-0813 | 58 | expert | nvlink5 | infiniband_ndr | 244 | 544.81 us | 183.6 tok/s | 1,835.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.53 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 251.28 us |
| DSV4-Pro/b200_sxm-x58-nvl72-expert | DeepSeek-V4-Pro-0813 | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.13 us | 224.7 tok/s | 2,246.5 tok/s | 122 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 298.53 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.60 us |
| DSV4-Pro/b200_sxm-x76-pipeline | DeepSeek-V4-Pro-0813 | 76 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x76-tensor | DeepSeek-V4-Pro-0813 | 76 | tensor | nvlink5 | infiniband_ndr | 244 | 887.67 us | 112.7 tok/s | 1,126.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 589.77 us |
| DSV4-Pro/b200_sxm-x76-hybrid | DeepSeek-V4-Pro-0813 | 76 | hybrid | nvlink5 | infiniband_ndr | 131 | 318.75 us | 313.7 tok/s | 3,137.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| DSV4-Pro/b200_sxm-x76-nvl72-tensor | DeepSeek-V4-Pro-0813 | 76 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x76-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 76 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x76-expert | DeepSeek-V4-Pro-0813 | 76 | expert | nvlink5 | infiniband_ndr | 244 | 543.79 us | 183.9 tok/s | 1,839.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.37 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.42 us |
| DSV4-Pro/b200_sxm-x76-nvl72-expert | DeepSeek-V4-Pro-0813 | 76 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.97 us | 182.2 tok/s | 1,821.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.42 us |
| DSV4-Pro/b200_sxm-x80-pipeline | DeepSeek-V4-Pro-0813 | 80 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x80-tensor | DeepSeek-V4-Pro-0813 | 80 | tensor | nvlink5 | infiniband_ndr | 244 | 887.67 us | 112.7 tok/s | 1,126.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 589.77 us |
| DSV4-Pro/b200_sxm-x80-hybrid | DeepSeek-V4-Pro-0813 | 80 | hybrid | nvlink5 | infiniband_ndr | 131 | 318.75 us | 313.7 tok/s | 3,137.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| DSV4-Pro/b200_sxm-x80-nvl72-tensor | DeepSeek-V4-Pro-0813 | 80 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x80-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 80 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x80-expert | DeepSeek-V4-Pro-0813 | 80 | expert | nvlink5 | infiniband_ndr | 244 | 543.59 us | 184.0 tok/s | 1,839.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.31 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.28 us |
| DSV4-Pro/b200_sxm-x80-nvl72-expert | DeepSeek-V4-Pro-0813 | 80 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.83 us | 182.2 tok/s | 1,822.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.28 us |
| DSV4-Pro/b200_sxm-x82-pipeline | DeepSeek-V4-Pro-0813 | 82 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x82-tensor | DeepSeek-V4-Pro-0813 | 82 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x82-hybrid | DeepSeek-V4-Pro-0813 | 82 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x82-nvl72-tensor | DeepSeek-V4-Pro-0813 | 82 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x82-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 82 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x82-expert | DeepSeek-V4-Pro-0813 | 82 | expert | nvlink5 | infiniband_ndr | 244 | 543.53 us | 184.0 tok/s | 1,839.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.31 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.22 us |
| DSV4-Pro/b200_sxm-x82-nvl72-expert | DeepSeek-V4-Pro-0813 | 82 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.77 us | 182.2 tok/s | 1,822.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.22 us |
| DSV4-Pro/b200_sxm-x87-pipeline | DeepSeek-V4-Pro-0813 | 87 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x87-tensor | DeepSeek-V4-Pro-0813 | 87 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x87-hybrid | DeepSeek-V4-Pro-0813 | 87 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x87-nvl72-tensor | DeepSeek-V4-Pro-0813 | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x87-expert | DeepSeek-V4-Pro-0813 | 87 | expert | nvlink5 | infiniband_ndr | 244 | 543.38 us | 184.0 tok/s | 1,840.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.31 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.07 us |
| DSV4-Pro/b200_sxm-x87-nvl72-expert | DeepSeek-V4-Pro-0813 | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.62 us | 182.3 tok/s | 1,822.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.07 us |
| DSV4-Pro/b200_sxm-x94-pipeline | DeepSeek-V4-Pro-0813 | 94 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x94-tensor | DeepSeek-V4-Pro-0813 | 94 | tensor | nvlink5 | infiniband_ndr | 244 | 889.42 us | 112.4 tok/s | 1,124.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 591.51 us |
| DSV4-Pro/b200_sxm-x94-hybrid | DeepSeek-V4-Pro-0813 | 94 | hybrid | nvlink5 | infiniband_ndr | 133 | 323.39 us | 309.2 tok/s | 3,092.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| DSV4-Pro/b200_sxm-x94-nvl72-tensor | DeepSeek-V4-Pro-0813 | 94 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x94-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 94 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x94-expert | DeepSeek-V4-Pro-0813 | 94 | expert | nvlink5 | infiniband_ndr | 244 | 543.16 us | 184.1 tok/s | 1,841.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.26 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.89 us |
| DSV4-Pro/b200_sxm-x94-nvl72-expert | DeepSeek-V4-Pro-0813 | 94 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.44 us | 182.3 tok/s | 1,823.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.89 us |
| DSV4-Pro/b200_sxm-x111-pipeline | DeepSeek-V4-Pro-0813 | 111 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x111-tensor | DeepSeek-V4-Pro-0813 | 111 | tensor | nvlink5 | infiniband_ndr | 244 | 890.67 us | 112.3 tok/s | 1,122.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 592.76 us |
| DSV4-Pro/b200_sxm-x111-hybrid | DeepSeek-V4-Pro-0813 | 111 | hybrid | nvlink5 | infiniband_ndr | 135 | 328.02 us | 304.9 tok/s | 3,048.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.12 us |
| DSV4-Pro/b200_sxm-x111-nvl72-tensor | DeepSeek-V4-Pro-0813 | 111 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x111-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 111 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x111-expert | DeepSeek-V4-Pro-0813 | 111 | expert | nvlink5 | infiniband_ndr | 244 | 542.74 us | 184.2 tok/s | 1,842.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.19 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.55 us |
| DSV4-Pro/b200_sxm-x111-nvl72-expert | DeepSeek-V4-Pro-0813 | 111 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.10 us | 182.4 tok/s | 1,824.5 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.55 us |
| DSV4-Pro/b200_sxm-x112-pipeline | DeepSeek-V4-Pro-0813 | 112 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x112-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink5 | infiniband_ndr | 244 | 890.67 us | 112.3 tok/s | 1,122.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 592.76 us |
| DSV4-Pro/b200_sxm-x112-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink5 | infiniband_ndr | 135 | 328.02 us | 304.9 tok/s | 3,048.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.12 us |
| DSV4-Pro/b200_sxm-x112-nvl72-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x112-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x112-expert | DeepSeek-V4-Pro-0813 | 112 | expert | nvlink5 | infiniband_ndr | 244 | 542.70 us | 184.3 tok/s | 1,842.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.16 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.53 us |
| DSV4-Pro/b200_sxm-x112-nvl72-expert | DeepSeek-V4-Pro-0813 | 112 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.08 us | 182.5 tok/s | 1,824.5 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.53 us |
| DSV4-Pro/b200_sxm-x113-pipeline | DeepSeek-V4-Pro-0813 | 113 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x113-tensor | DeepSeek-V4-Pro-0813 | 113 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x113-hybrid | DeepSeek-V4-Pro-0813 | 113 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x113-nvl72-tensor | DeepSeek-V4-Pro-0813 | 113 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x113-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 113 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x113-expert | DeepSeek-V4-Pro-0813 | 113 | expert | nvlink5 | infiniband_ndr | 244 | 542.68 us | 184.3 tok/s | 1,842.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.16 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.52 us |
| DSV4-Pro/b200_sxm-x113-nvl72-expert | DeepSeek-V4-Pro-0813 | 113 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.07 us | 182.5 tok/s | 1,824.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.52 us |
| DSV4-Pro/b200_sxm-x116-pipeline | DeepSeek-V4-Pro-0813 | 116 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x116-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x116-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x116-nvl72-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x116-expert | DeepSeek-V4-Pro-0813 | 116 | expert | nvlink5 | infiniband_ndr | 244 | 542.63 us | 184.3 tok/s | 1,842.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.16 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.47 us |
| DSV4-Pro/b200_sxm-x116-nvl72-expert | DeepSeek-V4-Pro-0813 | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.02 us | 182.5 tok/s | 1,824.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.47 us |
| DSV4-Pro/b200_sxm-x125-pipeline | DeepSeek-V4-Pro-0813 | 125 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x125-tensor | DeepSeek-V4-Pro-0813 | 125 | tensor | nvlink5 | infiniband_ndr | 244 | 891.60 us | 112.2 tok/s | 1,121.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 593.70 us |
| DSV4-Pro/b200_sxm-x125-hybrid | DeepSeek-V4-Pro-0813 | 125 | hybrid | nvlink5 | infiniband_ndr | 137 | 332.65 us | 300.6 tok/s | 3,006.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 34.75 us |
| DSV4-Pro/b200_sxm-x125-nvl72-tensor | DeepSeek-V4-Pro-0813 | 125 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x125-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 125 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x125-expert | DeepSeek-V4-Pro-0813 | 125 | expert | nvlink5 | infiniband_ndr | 244 | 542.48 us | 184.3 tok/s | 1,843.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.14 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.34 us |
| DSV4-Pro/b200_sxm-x125-nvl72-expert | DeepSeek-V4-Pro-0813 | 125 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.89 us | 182.5 tok/s | 1,825.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.34 us |
| DSV4-Pro/b200_sxm-x144-pipeline | DeepSeek-V4-Pro-0813 | 144 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x144-tensor | DeepSeek-V4-Pro-0813 | 144 | tensor | nvlink5 | infiniband_ndr | 244 | 892.33 us | 112.1 tok/s | 1,120.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 18 on infiniband_ndr (traversals 2.0) = 594.43 us |
| DSV4-Pro/b200_sxm-x144-hybrid | DeepSeek-V4-Pro-0813 | 144 | hybrid | nvlink5 | infiniband_ndr | 139 | 337.29 us | 296.5 tok/s | 2,964.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 39.38 us |
| DSV4-Pro/b200_sxm-x144-nvl72-tensor | DeepSeek-V4-Pro-0813 | 144 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x144-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 144 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x144-expert | DeepSeek-V4-Pro-0813 | 144 | expert | nvlink5 | infiniband_ndr | 244 | 542.20 us | 184.4 tok/s | 1,844.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.12 us |
| DSV4-Pro/b200_sxm-x144-nvl72-expert | DeepSeek-V4-Pro-0813 | 144 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.79 us | 183.6 tok/s | 1,835.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.12 us |
| DSV4-Pro/b200_sxm-x146-pipeline | DeepSeek-V4-Pro-0813 | 146 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x146-tensor | DeepSeek-V4-Pro-0813 | 146 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x146-hybrid | DeepSeek-V4-Pro-0813 | 146 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x146-nvl72-tensor | DeepSeek-V4-Pro-0813 | 146 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x146-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 146 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x146-expert | DeepSeek-V4-Pro-0813 | 146 | expert | nvlink5 | infiniband_ndr | 244 | 542.18 us | 184.4 tok/s | 1,844.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.10 us |
| DSV4-Pro/b200_sxm-x146-nvl72-expert | DeepSeek-V4-Pro-0813 | 146 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.77 us | 183.6 tok/s | 1,835.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.10 us |
| DSV4-Pro/b200_sxm-x150-pipeline | DeepSeek-V4-Pro-0813 | 150 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x150-tensor | DeepSeek-V4-Pro-0813 | 150 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x150-hybrid | DeepSeek-V4-Pro-0813 | 150 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x150-nvl72-tensor | DeepSeek-V4-Pro-0813 | 150 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x150-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 150 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x150-expert | DeepSeek-V4-Pro-0813 | 150 | expert | nvlink5 | infiniband_ndr | 244 | 542.14 us | 184.5 tok/s | 1,844.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.06 us |
| DSV4-Pro/b200_sxm-x150-nvl72-expert | DeepSeek-V4-Pro-0813 | 150 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.73 us | 183.6 tok/s | 1,835.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.06 us |
| DSV4-Pro/b200_sxm-x170-pipeline | DeepSeek-V4-Pro-0813 | 170 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x170-tensor | DeepSeek-V4-Pro-0813 | 170 | tensor | nvlink5 | infiniband_ndr | 244 | 893.39 us | 111.9 tok/s | 1,119.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 595.49 us |
| DSV4-Pro/b200_sxm-x170-hybrid | DeepSeek-V4-Pro-0813 | 170 | hybrid | nvlink5 | infiniband_ndr | 143 | 346.55 us | 288.6 tok/s | 2,885.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| DSV4-Pro/b200_sxm-x170-nvl72-tensor | DeepSeek-V4-Pro-0813 | 170 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x170-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 170 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x170-expert | DeepSeek-V4-Pro-0813 | 170 | expert | nvlink5 | infiniband_ndr | 244 | 541.94 us | 184.5 tok/s | 1,845.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.04 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.89 us |
| DSV4-Pro/b200_sxm-x170-nvl72-expert | DeepSeek-V4-Pro-0813 | 170 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.57 us | 183.6 tok/s | 1,836.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.89 us |
| DSV4-Pro/b200_sxm-x171-pipeline | DeepSeek-V4-Pro-0813 | 171 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x171-tensor | DeepSeek-V4-Pro-0813 | 171 | tensor | nvlink5 | infiniband_ndr | 244 | 893.39 us | 111.9 tok/s | 1,119.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 595.49 us |
| DSV4-Pro/b200_sxm-x171-hybrid | DeepSeek-V4-Pro-0813 | 171 | hybrid | nvlink5 | infiniband_ndr | 143 | 346.55 us | 288.6 tok/s | 2,885.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| DSV4-Pro/b200_sxm-x171-nvl72-tensor | DeepSeek-V4-Pro-0813 | 171 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x171-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 171 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x171-expert | DeepSeek-V4-Pro-0813 | 171 | expert | nvlink5 | infiniband_ndr | 244 | 541.93 us | 184.5 tok/s | 1,845.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.04 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.89 us |
| DSV4-Pro/b200_sxm-x171-nvl72-expert | DeepSeek-V4-Pro-0813 | 171 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.56 us | 183.6 tok/s | 1,836.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.89 us |
| DSV4-Pro/b200_sxm-x173-pipeline | DeepSeek-V4-Pro-0813 | 173 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x173-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5 | infiniband_ndr | 244 | 893.39 us | 111.9 tok/s | 1,119.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 595.49 us |
| DSV4-Pro/b200_sxm-x173-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5 | infiniband_ndr | 143 | 346.55 us | 288.6 tok/s | 2,885.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| DSV4-Pro/b200_sxm-x173-nvl72-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x173-expert | DeepSeek-V4-Pro-0813 | 173 | expert | nvlink5 | infiniband_ndr | 244 | 541.92 us | 184.5 tok/s | 1,845.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.04 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.87 us |
| DSV4-Pro/b200_sxm-x173-nvl72-expert | DeepSeek-V4-Pro-0813 | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.55 us | 183.6 tok/s | 1,836.4 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.87 us |
| DSV4-Pro/b200_sxm-x203-pipeline | DeepSeek-V4-Pro-0813 | 203 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x203-tensor | DeepSeek-V4-Pro-0813 | 203 | tensor | nvlink5 | infiniband_ndr | 244 | 894.12 us | 111.8 tok/s | 1,118.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 26 on infiniband_ndr (traversals 2.0) = 596.22 us |
| DSV4-Pro/b200_sxm-x203-hybrid | DeepSeek-V4-Pro-0813 | 203 | hybrid | nvlink5 | infiniband_ndr | 147 | 355.82 us | 281.0 tok/s | 2,810.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 25 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 57.92 us |
| DSV4-Pro/b200_sxm-x203-nvl72-tensor | DeepSeek-V4-Pro-0813 | 203 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x203-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 203 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x203-expert | DeepSeek-V4-Pro-0813 | 203 | expert | nvlink5 | infiniband_ndr | 244 | 541.70 us | 184.6 tok/s | 1,846.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.00 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.69 us |
| DSV4-Pro/b200_sxm-x203-nvl72-expert | DeepSeek-V4-Pro-0813 | 203 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.37 us | 183.7 tok/s | 1,837.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.69 us |
| DSV4-Pro/b200_sxm-x231-pipeline | DeepSeek-V4-Pro-0813 | 231 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x231-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5 | infiniband_ndr | 244 | 894.54 us | 111.8 tok/s | 1,117.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 596.64 us |
| DSV4-Pro/b200_sxm-x231-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5 | infiniband_ndr | 150 | 362.77 us | 275.7 tok/s | 2,756.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 64.87 us |
| DSV4-Pro/b200_sxm-x231-nvl72-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 872.57 us | 114.6 tok/s | 1,146.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 125 | 305.50 us | 327.3 tok/s | 3,273.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x231-expert | DeepSeek-V4-Pro-0813 | 231 | expert | nvlink5 | infiniband_ndr | 244 | 541.55 us | 184.7 tok/s | 1,846.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.98 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.57 us |
| DSV4-Pro/b200_sxm-x231-nvl72-expert | DeepSeek-V4-Pro-0813 | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 543.28 us | 184.1 tok/s | 1,840.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.72 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.57 us |
| DSV4-Pro/b200_sxm-x255-pipeline | DeepSeek-V4-Pro-0813 | 255 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x255-tensor | DeepSeek-V4-Pro-0813 | 255 | tensor | nvlink5 | infiniband_ndr | 244 | 894.88 us | 111.7 tok/s | 1,117.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 32 on infiniband_ndr (traversals 2.0) = 596.98 us |
| DSV4-Pro/b200_sxm-x255-hybrid | DeepSeek-V4-Pro-0813 | 255 | hybrid | nvlink5 | infiniband_ndr | 153 | 369.72 us | 270.5 tok/s | 2,704.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 31 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 71.82 us |
| DSV4-Pro/b200_sxm-x255-nvl72-tensor | DeepSeek-V4-Pro-0813 | 255 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 872.57 us | 114.6 tok/s | 1,146.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x255-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 255 | hybrid | nvlink5_nvl72 | infiniband_ndr | 125 | 305.50 us | 327.3 tok/s | 3,273.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x255-expert | DeepSeek-V4-Pro-0813 | 255 | expert | nvlink5 | infiniband_ndr | 244 | 541.45 us | 184.7 tok/s | 1,846.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.96 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.48 us |
| DSV4-Pro/b200_sxm-x255-nvl72-expert | DeepSeek-V4-Pro-0813 | 255 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 543.20 us | 184.1 tok/s | 1,840.9 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.72 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.48 us |
| DSV4-Pro/b200_sxm-x347-pipeline | DeepSeek-V4-Pro-0813 | 347 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x347-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5 | infiniband_ndr | 244 | 895.78 us | 111.6 tok/s | 1,116.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 597.87 us |
| DSV4-Pro/b200_sxm-x347-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5 | infiniband_ndr | 165 | 397.52 us | 251.6 tok/s | 2,515.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 99.62 us |
| DSV4-Pro/b200_sxm-x347-nvl72-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 877.82 us | 113.9 tok/s | 1,139.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 126 | 307.82 us | 324.9 tok/s | 3,248.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x347-expert | DeepSeek-V4-Pro-0813 | 347 | expert | nvlink5 | infiniband_ndr | 244 | 541.18 us | 184.8 tok/s | 1,847.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.92 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.26 us |
| DSV4-Pro/b200_sxm-x347-nvl72-expert | DeepSeek-V4-Pro-0813 | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 542.50 us | 184.3 tok/s | 1,843.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.24 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.26 us |
| DSV4-Pro/b200_sxm-x1358-pipeline | DeepSeek-V4-Pro-0813 | 1358 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x1358-tensor | DeepSeek-V4-Pro-0813 | 1358 | tensor | nvlink5 | infiniband_ndr | 244 | 1,392.86 us | 71.8 tok/s | 717.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 170 on infiniband_ndr (traversals 4.0) = 1,094.96 us |
| DSV4-Pro/b200_sxm-x1358-hybrid | DeepSeek-V4-Pro-0813 | 1358 | hybrid | nvlink5 | infiniband_ndr | 182 | 436.90 us | 228.9 tok/s | 2,288.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 60 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 139.00 us |
| DSV4-Pro/b200_sxm-x1358-nvl72-tensor | DeepSeek-V4-Pro-0813 | 1358 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 893.29 us | 111.9 tok/s | 1,119.5 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x1358-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 1358 | hybrid | nvlink5_nvl72 | infiniband_ndr | 140 | 340.25 us | 293.9 tok/s | 2,939.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x1358-expert | DeepSeek-V4-Pro-0813 | 1358 | expert | nvlink5 | infiniband_ndr | 244 | 540.64 us | 185.0 tok/s | 1,849.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.83 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 247.81 us |
| DSV4-Pro/b200_sxm-x1358-nvl72-expert | DeepSeek-V4-Pro-0813 | 1358 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 540.93 us | 184.9 tok/s | 1,848.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 293.12 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 247.81 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | array | array | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x7-romfill | 5,705 | 10,396.9 | 1.822 | 10,396.9 (5,705) | 4,904.9 (46,225) | 0.47x | layer_fixed_latency |
| Qwen3-8B | 2 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 9,479.5 | 0.237 | 9,479.5 (39,935) | 4,545.7 (277,350) | 0.48x | layer_fixed_latency |
| Qwen3-8B | 4 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill | 39,935 | 9,479.5 | 0.237 | 9,479.5 (39,935) | 4,545.7 (277,350) | 0.48x | layer_fixed_latency |
| Qwen3-8B | 8 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill | 92,095 | 9,685.1 | 0.105 | 9,685.1 (92,095) | 4,545.7 (277,350) | 0.47x | layer_fixed_latency |
| Qwen3-8B | 16 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 9,672.8 | 0.035 | 9,672.8 (277,100) | 4,521.9 (554,700) | 0.47x | layer_fixed_latency |
| Qwen3-8B | 32 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 8,789.7 | 0.032 | 8,789.7 (277,100) | 3,937.8 (554,700) | 0.45x | layer_fixed_latency |
| Qwen3-8B | 64 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 7,163.6 | 0.026 | 7,163.6 (277,100) | 3,112.9 (554,700) | 0.43x | layer_fixed_latency |
| Qwen3-8B | 256 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 3,148.4 | 0.011 | 3,148.4 (277,100) | 1,209.8 (554,700) | 0.38x | thermal |
| Qwen3-8B | 1024 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 801.0 | 0.003 | 801.0 (277,100) | 330.9 (554,700) | 0.41x | thermal |
| Qwen3-8B | 4096 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 201.1 | 0.001 | 201.1 (277,100) | 84.0 (554,700) | 0.42x | thermal |
| DeepSeek-V4-Flash-0731 | 1 | array | array | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x42 | 34,230 | 3,247.3 | 0.095 | 3,247.3 (34,230) | 2,786.2 (46,225) | 0.86x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 2 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 3,354.3 | 0.073 | 3,354.3 (45,640) | 2,542.2 (323,575) | 0.76x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 4 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 3,354.3 | 0.073 | 3,354.3 (45,640) | 2,542.2 (323,575) | 0.76x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 8 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 3,354.3 | 0.073 | 3,354.3 (45,640) | 2,542.2 (323,575) | 0.76x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 16 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56 | 45,640 | 3,273.4 | 0.072 | 3,273.4 (45,640) | 2,542.2 (323,575) | 0.78x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x70 | 57,050 | 3,117.2 | 0.055 | 3,117.2 (57,050) | 2,542.2 (323,575) | 0.82x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 64 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x224-romfill | 182,560 | 3,169.5 | 0.017 | 3,169.5 (182,560) | 2,438.1 (369,800) | 0.77x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 256 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 2,536.0 | 0.009 | 2,536.0 (277,100) | 2,071.6 (554,700) | 0.82x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 1024 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 1,134.8 | 0.004 | 1,134.8 (277,100) | 1,018.1 (554,700) | 0.90x | compute |
| DeepSeek-V4-Flash-0731 | 4096 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 344.7 | 0.001 | 344.7 (277,100) | 295.8 (554,700) | 0.86x | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x5 | 231,125 | 1,509.5 | 0.007 | 1,421.6 (200,490) | 1,509.5 (231,125) | 1.06x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 2 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,491.0 | 0.005 | 1,491.0 (325,185) | 1,156.1 (2,172,575) | 0.78x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 4 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,491.0 | 0.005 | 1,491.0 (325,185) | 1,156.1 (2,172,575) | 0.78x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 8 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,491.0 | 0.005 | 1,491.0 (325,185) | 1,156.1 (2,172,575) | 0.78x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 16 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,491.0 | 0.005 | 1,491.0 (325,185) | 1,156.1 (2,172,575) | 0.78x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 32 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,491.0 | 0.005 | 1,491.0 (325,185) | 1,156.1 (2,172,575) | 0.78x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 64 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399 | 325,185 | 1,491.0 | 0.005 | 1,491.0 (325,185) | 1,156.1 (2,172,575) | 0.78x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 256 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47 | 2,172,575 | 1,038.8 | 0.000 | 959.9 (325,185) | 1,038.8 (2,172,575) | 1.08x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 1024 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47 | 2,172,575 | 551.7 | 0.000 | 339.9 (325,185) | 551.7 (2,172,575) | 1.62x | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 168.6 | 0.000 | 92.1 (325,185) | 168.6 (2,172,575) | 1.83x | kv_read |

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
| DeepSeek-V4-Flash-0731 | 256 | 574.9 MB | 98.1 mm2 | 17.65 mm2 (18.0%) | 25,105 mm2 | 4,519 mm2 | 28,467 mm2 = 34.9 reticles |
| DeepSeek-V4-Pro-0813 | 384 | 2,140.8 MB | 365.2 mm2 | 65.73 mm2 (18.0%) | 140,230 mm2 | 25,241 mm2 | 152,286 mm2 = 186.9 reticles |

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
| Qwen3-8B | 1 | sram | 28,188.0 | 28,122.6 | 28,122.6 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 28,188.0 | 28,122.6 | 28,122.6 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 28,188.0 | 28,122.6 | 28,122.6 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 41,580.0 | 28,122.6 | 28,122.6 | 1.48x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 68,921.9 | 28,122.6 | 28,122.6 | 2.45x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 114,665.5 | 28,122.6 | 28,122.6 | 4.08x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 171,204.8 | 28,216.6 | 28,216.6 | 6.07x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 392,900.4 | 25,989.1 | 25,989.1 | 15.12x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 1024 | sram | 710,400.6 | 26,071.0 | 26,071.0 | 27.25x | 1.00x | thermal | weight_read | weight_read |
| Qwen3-8B | 4096 | sram | 710,419.1 | 26,101.7 | 26,101.7 | 27.22x | 1.00x | thermal | weight_read | weight_read |
| Qwen3-8B | 1 | rom | 796,701.8 | 167,681.2 | 167,681.2 | 4.75x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 796,701.8 | 167,681.2 | 167,681.2 | 4.75x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 796,701.8 | 167,681.2 | 167,681.2 | 4.75x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 796,701.8 | 167,681.2 | 167,681.2 | 4.75x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 796,701.8 | 167,681.2 | 167,681.2 | 4.75x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 796,701.8 | 167,681.2 | 167,681.2 | 4.75x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 796,701.8 | 167,681.2 | 167,681.2 | 4.75x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 805,998.1 | 167,681.2 | 167,681.2 | 4.81x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 1024 | rom | 820,186.7 | 171,146.5 | 171,146.5 | 4.79x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 4096 | rom | 823,812.2 | 172,477.8 | 172,477.8 | 4.78x | 1.00x | thermal | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 360,794.6 | 27,425.1 | 27,425.1 | 13.16x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 360,794.6 | 27,425.1 | 27,425.1 | 13.16x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 360,794.6 | 27,425.1 | 27,425.1 | 13.16x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 360,794.6 | 27,425.1 | 27,425.1 | 13.16x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 360,794.6 | 27,425.1 | 28,883.0 | 13.16x | 1.05x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 360,794.6 | 27,425.1 | 43,111.5 | 13.16x | 1.57x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 360,794.6 | 26,113.2 | 62,447.6 | 13.82x | 2.39x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 487,964.5 | 26,113.2 | 140,110.3 | 18.69x | 5.37x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 884,492.3 | 26,113.2 | 262,497.4 | 33.87x | 10.05x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 1,411,894.1 | 26,113.2 | 395,396.8 | 54.07x | 15.14x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 942,094.9 | 568,961.1 | 568,961.1 | 1.66x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 942,094.9 | 568,961.1 | 568,961.1 | 1.66x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 942,094.9 | 568,961.1 | 568,961.1 | 1.66x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 942,094.9 | 568,961.1 | 568,961.1 | 1.66x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 942,094.9 | 568,961.1 | 568,961.1 | 1.66x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 942,094.9 | 568,961.1 | 568,961.1 | 1.66x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 942,094.9 | 568,961.1 | 568,961.1 | 1.66x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 942,094.9 | 568,961.1 | 568,961.1 | 1.66x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 1,162,029.6 | 661,439.6 | 672,882.4 | 1.76x | 1.02x | compute | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 1,339,135.2 | 717,024.8 | 727,412.6 | 1.87x | 1.01x | compute | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 545,366.8 | 26,113.2 | 26,113.2 | 20.88x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 545,366.8 | 26,113.2 | 26,113.2 | 20.88x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 545,366.8 | 26,113.2 | 26,113.2 | 20.88x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 545,366.8 | 26,113.2 | 26,113.2 | 20.88x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 545,366.8 | 26,113.2 | 26,113.2 | 20.88x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 545,366.8 | 26,113.2 | 26,113.2 | 20.88x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 545,366.8 | 26,113.2 | 33,966.4 | 20.88x | 1.30x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 545,366.8 | 26,113.2 | 78,015.4 | 20.88x | 2.99x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1024 | sram | 564,961.9 | 26,113.2 | 171,893.2 | 21.64x | 6.58x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4096 | sram | 690,483.5 | 26,113.2 | 355,983.3 | 26.44x | 13.63x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 665,645.4 | 670,802.4 | 670,802.4 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 665,645.4 | 670,802.4 | 670,802.4 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 665,645.4 | 670,802.4 | 670,802.4 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 665,645.4 | 670,802.4 | 670,802.4 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 665,645.4 | 670,802.4 | 670,802.4 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 665,645.4 | 670,802.4 | 670,802.4 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 665,645.4 | 670,802.4 | 670,802.4 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 665,645.4 | 670,802.4 | 670,802.4 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | rom | 665,645.4 | 670,802.4 | 670,802.4 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | rom | 683,452.3 | 689,288.5 | 687,733.3 | 0.99x | 1.00x | kv_read | kv_read | kv_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,188.0 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 28.26x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,122.6 | 0.608 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 5.95x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,122.6 | 0.608 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 5.95x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,188.0 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 28.26x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,122.6 | 0.608 | weight_read | 1.00x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 5.95x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,122.6 | 0.608 | weight_read | 1.00x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 5.95x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 28,188.0 | 0.051 | weight_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 28.26x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,122.6 | 0.608 | weight_read | 1.00x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 5.95x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,122.6 | 0.608 | weight_read | 1.00x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 5.95x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x62 | 50,530 | 1.00 | 1.00 | 41,580.0 | 0.823 | layer_fixed_latency | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 19.16x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,122.6 | 0.608 | weight_read | 0.68x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 4.03x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,122.6 | 0.608 | weight_read | 0.68x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 4.03x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x62 | 50,530 | 1.00 | 1.00 | 68,921.9 | 1.364 | weight_read | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 11.56x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,122.6 | 0.608 | weight_read | 0.41x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 2.43x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,122.6 | 0.608 | weight_read | 0.41x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 2.43x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x62 | 50,530 | 1.00 | 1.00 | 114,665.5 | 2.269 | kv_read | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 6.95x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,122.6 | 0.608 | weight_read | 0.25x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 1.46x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,122.6 | 0.608 | weight_read | 0.25x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 1.46x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x98 | 79,870 | 1.00 | 1.00 | 171,204.8 | 2.144 | weight_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 4.65x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,216.6 | 0.610 | weight_read | 0.16x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 0.98x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.12 | 28,216.6 | 0.610 | weight_read | 0.16x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 0.98x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x196 | 159,740 | 1.00 | 1.00 | 392,900.4 | 2.460 | weight_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 69.67 | 1.00 | 805,998.1 | 2.909 | thermal | 2.05x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 25,989.1 | 0.094 | weight_read | 0.07x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 0.43x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 25,989.1 | 0.094 | weight_read | 0.07x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 1.00 | 167,681.2 | 0.605 | kv_read | 0.43x |
| Qwen3-8B | 1024 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 710,400.6 | 2.564 | thermal | 1.00x |
| Qwen3-8B | 1024 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 69.67 | 1.00 | 820,186.7 | 2.960 | thermal | 1.15x |
| Qwen3-8B | 1024 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 3.00 | 26,071.0 | 0.094 | weight_read | 0.04x |
| Qwen3-8B | 1024 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 3.00 | 171,146.5 | 0.617 | kv_read | 0.24x |
| Qwen3-8B | 1024 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 3.00 | 26,071.0 | 0.094 | weight_read | 0.04x |
| Qwen3-8B | 1024 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 3.00 | 171,146.5 | 0.617 | kv_read | 0.24x |
| Qwen3-8B | 4096 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 710,419.1 | 2.564 | thermal | 1.00x |
| Qwen3-8B | 4096 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 69.67 | 1.00 | 823,812.2 | 2.973 | thermal | 1.16x |
| Qwen3-8B | 4096 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 12.01 | 26,101.7 | 0.094 | weight_read | 0.04x |
| Qwen3-8B | 4096 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 250.39 | 12.01 | 172,477.8 | 0.622 | kv_read | 0.24x |
| Qwen3-8B | 4096 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 12.01 | 26,101.7 | 0.094 | weight_read | 0.04x |
| Qwen3-8B | 4096 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 250.39 | 12.01 | 172,477.8 | 0.622 | kv_read | 0.24x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 360,794.6 | 0.650 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 942,094.9 | 1.698 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,425.1 | 0.593 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,425.1 | 0.593 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 360,794.6 | 0.650 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 942,094.9 | 1.698 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,425.1 | 0.593 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,425.1 | 0.593 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 360,794.6 | 0.650 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 942,094.9 | 1.698 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,425.1 | 0.593 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,425.1 | 0.593 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 360,794.6 | 0.650 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 942,094.9 | 1.698 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,425.1 | 0.593 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,425.1 | 0.593 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 360,794.6 | 0.650 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 942,094.9 | 1.698 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,425.1 | 0.593 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56-perregion | 45,640 | 1.00 | 1.19 | 28,883.0 | 0.633 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 360,794.6 | 0.650 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 942,094.9 | 1.698 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,425.1 | 0.593 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56-perregion | 45,640 | 1.00 | 1.69 | 43,111.5 | 0.945 | weight_read | 0.12x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 360,794.6 | 0.650 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 942,094.9 | 1.698 | kv_read | 2.61x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x56-perregion | 45,640 | 1.00 | 2.23 | 62,447.6 | 1.368 | weight_read | 0.17x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.58x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x224 | 182,560 | 1.00 | 1.00 | 487,964.5 | 2.673 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 942,094.9 | 1.698 | kv_read | 1.93x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,113.2 | 0.081 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.17x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 4.31 | 140,110.3 | 0.433 | weight_read | 0.29x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.00 | 568,961.1 | 1.758 | weight_read | 1.17x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 884,492.3 | 3.192 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.84 | 1.00 | 1,162,029.6 | 4.194 | compute | 1.31x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56-perstream | 45,640 | 1.00 | 18.29 | 26,113.2 | 0.572 | weight_read | 0.03x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 2.57 | 661,439.6 | 2.044 | weight_read | 0.75x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 6.57 | 262,497.4 | 0.811 | weight_read | 0.30x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 1.25 | 672,882.4 | 2.080 | kv_read | 0.76x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 1,411,894.1 | 5.095 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.84 | 1.00 | 1,339,135.2 | 4.833 | compute | 0.95x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56-perstream | 45,640 | 1.00 | 73.14 | 26,113.2 | 0.572 | weight_read | 0.02x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 28.68 | 10.29 | 717,024.8 | 2.216 | weight_read | 0.51x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 15.99 | 395,396.8 | 1.222 | weight_read | 0.28x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 28.68 | 2.33 | 727,412.6 | 2.248 | kv_read | 0.52x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 545,366.8 | 0.251 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 665,645.4 | 0.306 | kv_read | 1.22x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 545,366.8 | 0.251 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 665,645.4 | 0.306 | kv_read | 1.22x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 545,366.8 | 0.251 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 665,645.4 | 0.306 | kv_read | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 545,366.8 | 0.251 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 665,645.4 | 0.306 | kv_read | 1.22x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 545,366.8 | 0.251 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 665,645.4 | 0.306 | kv_read | 1.22x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 545,366.8 | 0.251 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 665,645.4 | 0.306 | kv_read | 1.22x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 545,366.8 | 0.251 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 665,645.4 | 0.306 | kv_read | 1.22x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399-perregion | 325,185 | 1.00 | 1.18 | 33,966.4 | 0.104 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 545,366.8 | 0.251 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 665,645.4 | 0.306 | kv_read | 1.22x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47-perregion | 2,172,575 | 1.00 | 2.18 | 78,015.4 | 0.036 | weight_read | 0.14x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.23x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47 | 2,172,575 | 1.00 | 1.00 | 564,961.9 | 0.260 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 665,645.4 | 0.306 | kv_read | 1.18x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream | 2,172,575 | 1.00 | 1.00 | 26,113.2 | 0.012 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.19x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47-perregion | 2,172,575 | 1.00 | 4.02 | 171,893.2 | 0.079 | weight_read | 0.30x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.00 | 670,802.4 | 0.309 | kv_read | 1.19x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47 | 2,172,575 | 1.00 | 1.00 | 690,483.5 | 0.318 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-romfill | 2,172,575 | 10.71 | 1.00 | 683,452.3 | 0.315 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399-perstream | 325,185 | 1.00 | 10.27 | 26,113.2 | 0.080 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perstream-romfill | 2,172,575 | 35.99 | 1.54 | 689,288.5 | 0.317 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x47-perregion | 2,172,575 | 1.00 | 5.80 | 355,983.3 | 0.164 | weight_read | 0.52x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x47-perregion-romfill | 2,172,575 | 35.99 | 1.05 | 687,733.3 | 0.317 | kv_read | 1.00x |

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
| Qwen3-8B | 1 | 2 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 2 | 4 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4 | 4 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 64 | 57 | 1.12 | 1.123 | 1.123 | 1.00x |
| Qwen3-8B | 256 | 49 | 5.22 | 5.224 | 5.224 | 1.00x |
| Qwen3-8B | 1024 | 49 | 20.90 | 20.898 | 20.898 | 1.00x |
| Qwen3-8B | 4096 | 49 | 83.59 | 83.592 | 83.592 | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | 15 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 1.14 | 1.002 | 1.017 | 1.02x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 4.57 | 1.043 | 1.686 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1024 | 56 | 18.29 | 1.218 | 3.075 | 2.52x |
| DeepSeek-V4-Flash-0731 | 4096 | 56 | 73.14 | 2.082 | 6.293 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 78 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 399 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 399 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 399 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 399 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | 399 | 2.57 | 1.012 | 1.177 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4096 | 399 | 10.27 | 1.075 | 2.150 | 2.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 2 | 8 | 6.36 | 3.68 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 8 | 7.64 | 4.38 | 1.74x |
| DeepSeek-V4-Flash-0731 | 8 | 8 | 7.98 | 5.03 | 1.59x |
| DeepSeek-V4-Flash-0731 | 16 | 8 | 8.00 | 5.58 | 1.43x |
| DeepSeek-V4-Flash-0731 | 32 | 8 | 8.00 | 6.01 | 1.33x |
| DeepSeek-V4-Flash-0731 | 64 | 8 | 8.00 | 6.29 | 1.27x |
| DeepSeek-V4-Flash-0731 | 256 | 8 | 8.00 | 6.45 | 1.24x |
| DeepSeek-V4-Flash-0731 | 1 | 10 | 4.69 | 3.22 | 1.45x |
| DeepSeek-V4-Flash-0731 | 2 | 10 | 7.13 | 4.05 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 10 | 9.13 | 4.92 | 1.86x |
| DeepSeek-V4-Flash-0731 | 8 | 10 | 9.91 | 5.76 | 1.72x |
| DeepSeek-V4-Flash-0731 | 16 | 10 | 10.00 | 6.50 | 1.54x |
| DeepSeek-V4-Flash-0731 | 32 | 10 | 10.00 | 7.09 | 1.41x |
| DeepSeek-V4-Flash-0731 | 64 | 10 | 10.00 | 7.48 | 1.34x |
| DeepSeek-V4-Flash-0731 | 256 | 10 | 10.00 | 7.71 | 1.30x |
| DeepSeek-V4-Flash-0731 | 1024 | 10 | 10.00 | 7.71 | 1.30x |
| DeepSeek-V4-Flash-0731 | 1 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4-Flash-0731 | 2 | 15 | 8.38 | 4.73 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 15 | 11.97 | 5.97 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 15 | 14.29 | 7.25 | 1.97x |
| DeepSeek-V4-Flash-0731 | 16 | 15 | 14.94 | 8.45 | 1.77x |
| DeepSeek-V4-Flash-0731 | 32 | 15 | 15.00 | 9.44 | 1.59x |
| DeepSeek-V4-Flash-0731 | 64 | 15 | 15.00 | 10.12 | 1.48x |
| DeepSeek-V4-Flash-0731 | 256 | 15 | 15.00 | 10.53 | 1.42x |
| DeepSeek-V4-Flash-0731 | 1024 | 15 | 15.00 | 10.54 | 1.42x |
| DeepSeek-V4-Flash-0731 | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 8.86 | 5.03 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 13.21 | 6.47 | 2.04x |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 16.56 | 7.99 | 2.07x |
| DeepSeek-V4-Flash-0731 | 16 | 18 | 17.82 | 9.44 | 1.89x |
| DeepSeek-V4-Flash-0731 | 32 | 18 | 17.99 | 10.67 | 1.69x |
| DeepSeek-V4-Flash-0731 | 64 | 18 | 18.00 | 11.53 | 1.56x |
| DeepSeek-V4-Flash-0731 | 256 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 1024 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 2 | 19 | 8.99 | 5.12 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 19 | 13.57 | 6.62 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 19 | 17.26 | 8.21 | 2.10x |
| DeepSeek-V4-Flash-0731 | 16 | 19 | 18.76 | 9.75 | 1.92x |
| DeepSeek-V4-Flash-0731 | 32 | 19 | 18.99 | 11.05 | 1.72x |
| DeepSeek-V4-Flash-0731 | 64 | 19 | 19.00 | 11.97 | 1.59x |
| DeepSeek-V4-Flash-0731 | 256 | 19 | 19.00 | 12.53 | 1.52x |
| DeepSeek-V4-Flash-0731 | 1024 | 19 | 19.00 | 12.53 | 1.52x |
| DeepSeek-V4-Flash-0731 | 1 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 2 | 21 | 9.23 | 5.29 | 1.74x |
| DeepSeek-V4-Flash-0731 | 4 | 21 | 14.22 | 6.90 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 21 | 18.57 | 8.63 | 2.15x |
| DeepSeek-V4-Flash-0731 | 16 | 21 | 20.59 | 10.33 | 1.99x |
| DeepSeek-V4-Flash-0731 | 32 | 21 | 20.97 | 11.79 | 1.78x |
| DeepSeek-V4-Flash-0731 | 64 | 21 | 21.00 | 12.82 | 1.64x |
| DeepSeek-V4-Flash-0731 | 256 | 21 | 21.00 | 13.46 | 1.56x |
| DeepSeek-V4-Flash-0731 | 1024 | 21 | 21.00 | 13.46 | 1.56x |
| DeepSeek-V4-Flash-0731 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 22 | 9.33 | 5.36 | 1.74x |
| DeepSeek-V4-Flash-0731 | 4 | 22 | 14.51 | 7.03 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 22 | 19.19 | 8.83 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 22 | 21.49 | 10.61 | 2.03x |
| DeepSeek-V4-Flash-0731 | 32 | 22 | 21.96 | 12.14 | 1.81x |
| DeepSeek-V4-Flash-0731 | 64 | 22 | 22.00 | 13.24 | 1.66x |
| DeepSeek-V4-Flash-0731 | 256 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 1024 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 1 | 23 | 5.38 | 4.06 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 23 | 9.42 | 5.44 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 23 | 14.79 | 7.16 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 23 | 19.78 | 9.03 | 2.19x |
| DeepSeek-V4-Flash-0731 | 16 | 23 | 22.37 | 10.88 | 2.06x |
| DeepSeek-V4-Flash-0731 | 32 | 23 | 22.95 | 12.49 | 1.84x |
| DeepSeek-V4-Flash-0731 | 64 | 23 | 23.00 | 13.64 | 1.69x |
| DeepSeek-V4-Flash-0731 | 256 | 23 | 23.00 | 14.35 | 1.60x |
| DeepSeek-V4-Flash-0731 | 1024 | 23 | 23.00 | 14.35 | 1.60x |
| DeepSeek-V4-Flash-0731 | 1 | 24 | 5.41 | 4.10 | 1.32x |
| DeepSeek-V4-Flash-0731 | 2 | 24 | 9.51 | 5.51 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 24 | 15.05 | 7.28 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 24 | 20.35 | 9.21 | 2.21x |
| DeepSeek-V4-Flash-0731 | 16 | 24 | 23.23 | 11.14 | 2.09x |
| DeepSeek-V4-Flash-0731 | 32 | 24 | 23.93 | 12.82 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 24 | 24.00 | 14.03 | 1.71x |
| DeepSeek-V4-Flash-0731 | 256 | 24 | 24.00 | 14.78 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1024 | 24 | 24.00 | 14.79 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 2 | 28 | 9.81 | 5.76 | 1.70x |
| DeepSeek-V4-Flash-0731 | 4 | 28 | 15.94 | 7.73 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 28 | 22.40 | 9.90 | 2.26x |
| DeepSeek-V4-Flash-0731 | 16 | 28 | 26.52 | 12.12 | 2.19x |
| DeepSeek-V4-Flash-0731 | 32 | 28 | 27.80 | 14.09 | 1.97x |
| DeepSeek-V4-Flash-0731 | 64 | 28 | 27.98 | 15.53 | 1.80x |
| DeepSeek-V4-Flash-0731 | 256 | 28 | 28.00 | 16.42 | 1.70x |
| DeepSeek-V4-Flash-0731 | 1024 | 28 | 28.00 | 16.43 | 1.70x |
| DeepSeek-V4-Flash-0731 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 29 | 9.87 | 5.82 | 1.70x |
| DeepSeek-V4-Flash-0731 | 4 | 29 | 16.14 | 7.83 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 29 | 22.86 | 10.06 | 2.27x |
| DeepSeek-V4-Flash-0731 | 16 | 29 | 27.30 | 12.35 | 2.21x |
| DeepSeek-V4-Flash-0731 | 32 | 29 | 28.76 | 14.39 | 2.00x |
| DeepSeek-V4-Flash-0731 | 64 | 29 | 28.97 | 15.88 | 1.82x |
| DeepSeek-V4-Flash-0731 | 256 | 29 | 29.00 | 16.82 | 1.72x |
| DeepSeek-V4-Flash-0731 | 1024 | 29 | 29.00 | 16.82 | 1.72x |
| DeepSeek-V4-Flash-0731 | 1 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 2 | 31 | 9.99 | 5.93 | 1.68x |
| DeepSeek-V4-Flash-0731 | 4 | 31 | 16.50 | 8.03 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 31 | 23.73 | 10.37 | 2.29x |
| DeepSeek-V4-Flash-0731 | 16 | 31 | 28.81 | 12.79 | 2.25x |
| DeepSeek-V4-Flash-0731 | 32 | 31 | 30.64 | 14.97 | 2.05x |
| DeepSeek-V4-Flash-0731 | 64 | 31 | 30.96 | 16.57 | 1.87x |
| DeepSeek-V4-Flash-0731 | 256 | 31 | 30.99 | 17.58 | 1.76x |
| DeepSeek-V4-Flash-0731 | 1024 | 31 | 30.99 | 17.59 | 1.76x |
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
| DeepSeek-V4-Flash-0731 | 1 | 57 | 5.74 | 4.89 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 57 | 10.79 | 6.99 | 1.54x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 19.18 | 9.81 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 30.95 | 13.28 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 43.37 | 17.16 | 2.53x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 51.88 | 20.90 | 2.48x |
| DeepSeek-V4-Flash-0731 | 64 | 57 | 55.34 | 23.81 | 2.32x |
| DeepSeek-V4-Flash-0731 | 256 | 57 | 56.38 | 25.71 | 2.19x |
| DeepSeek-V4-Flash-0731 | 1024 | 57 | 56.39 | 25.73 | 2.19x |
| DeepSeek-V4-Flash-0731 | 4096 | 57 | 56.39 | 25.73 | 2.19x |
| DeepSeek-V4-Flash-0731 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 58 | 10.81 | 7.02 | 1.54x |
| DeepSeek-V4-Flash-0731 | 4 | 58 | 19.24 | 9.86 | 1.95x |
| DeepSeek-V4-Flash-0731 | 8 | 58 | 31.13 | 13.37 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 58 | 43.78 | 17.30 | 2.53x |
| DeepSeek-V4-Flash-0731 | 32 | 58 | 52.57 | 21.09 | 2.49x |
| DeepSeek-V4-Flash-0731 | 64 | 58 | 56.21 | 24.04 | 2.34x |
| DeepSeek-V4-Flash-0731 | 256 | 58 | 57.32 | 25.97 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1024 | 58 | 57.32 | 25.99 | 2.21x |
| DeepSeek-V4-Flash-0731 | 4096 | 58 | 57.32 | 25.99 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 86 | 11.14 | 7.76 | 1.44x |
| DeepSeek-V4-Flash-0731 | 4 | 86 | 20.41 | 10.92 | 1.87x |
| DeepSeek-V4-Flash-0731 | 8 | 86 | 34.74 | 15.37 | 2.26x |
| DeepSeek-V4-Flash-0731 | 16 | 86 | 52.59 | 20.42 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 86 | 68.50 | 25.50 | 2.69x |
| DeepSeek-V4-Flash-0731 | 64 | 86 | 77.70 | 29.61 | 2.62x |
| DeepSeek-V4-Flash-0731 | 256 | 86 | 81.66 | 32.36 | 2.52x |
| DeepSeek-V4-Flash-0731 | 1024 | 86 | 81.69 | 32.38 | 2.52x |
| DeepSeek-V4-Flash-0731 | 4096 | 86 | 81.69 | 32.38 | 2.52x |
| DeepSeek-V4-Flash-0731 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 87 | 11.15 | 7.78 | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | 87 | 20.44 | 10.95 | 1.87x |
| DeepSeek-V4-Flash-0731 | 8 | 87 | 34.83 | 15.44 | 2.26x |
| DeepSeek-V4-Flash-0731 | 16 | 87 | 52.83 | 20.51 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 87 | 68.97 | 25.63 | 2.69x |
| DeepSeek-V4-Flash-0731 | 64 | 87 | 78.37 | 29.78 | 2.63x |
| DeepSeek-V4-Flash-0731 | 256 | 87 | 82.46 | 32.55 | 2.53x |
| DeepSeek-V4-Flash-0731 | 1024 | 87 | 82.49 | 32.58 | 2.53x |
| DeepSeek-V4-Flash-0731 | 4096 | 87 | 82.49 | 32.58 | 2.53x |
| DeepSeek-V4-Flash-0731 | 1 | 114 | 5.87 | 5.36 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 114 | 11.31 | 8.30 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 114 | 21.05 | 11.66 | 1.80x |
| DeepSeek-V4-Flash-0731 | 8 | 114 | 36.80 | 16.88 | 2.18x |
| DeepSeek-V4-Flash-0731 | 16 | 114 | 58.08 | 22.74 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 114 | 79.65 | 28.87 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 114 | 94.41 | 33.96 | 2.78x |
| DeepSeek-V4-Flash-0731 | 256 | 114 | 101.99 | 37.41 | 2.73x |
| DeepSeek-V4-Flash-0731 | 1024 | 114 | 102.05 | 37.44 | 2.73x |
| DeepSeek-V4-Flash-0731 | 4096 | 114 | 102.05 | 37.44 | 2.73x |
| DeepSeek-V4-Flash-0731 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 2 | 116 | 11.32 | 8.33 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 116 | 21.08 | 11.71 | 1.80x |
| DeepSeek-V4-Flash-0731 | 8 | 116 | 36.91 | 16.98 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 116 | 58.39 | 22.88 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 116 | 80.31 | 29.09 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 116 | 95.45 | 34.23 | 2.79x |
| DeepSeek-V4-Flash-0731 | 256 | 116 | 103.29 | 37.73 | 2.74x |
| DeepSeek-V4-Flash-0731 | 1024 | 116 | 103.36 | 37.77 | 2.74x |
| DeepSeek-V4-Flash-0731 | 4096 | 116 | 103.36 | 37.77 | 2.74x |
| DeepSeek-V4-Flash-0731 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 2 | 173 | 11.49 | 9.06 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 173 | 21.74 | 12.85 | 1.69x |
| DeepSeek-V4-Flash-0731 | 8 | 173 | 39.14 | 19.00 | 2.06x |
| DeepSeek-V4-Flash-0731 | 16 | 173 | 64.73 | 26.15 | 2.48x |
| DeepSeek-V4-Flash-0731 | 32 | 173 | 94.43 | 34.13 | 2.77x |
| DeepSeek-V4-Flash-0731 | 64 | 173 | 118.70 | 40.88 | 2.90x |
| DeepSeek-V4-Flash-0731 | 256 | 173 | 133.64 | 45.54 | 2.93x |
| DeepSeek-V4-Flash-0731 | 1024 | 173 | 133.78 | 45.59 | 2.93x |
| DeepSeek-V4-Flash-0731 | 4096 | 173 | 133.78 | 45.59 | 2.93x |
| DeepSeek-V4-Flash-0731 | 1 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4-Flash-0731 | 2 | 202 | 11.55 | 9.33 | 1.24x |
| DeepSeek-V4-Flash-0731 | 4 | 202 | 21.94 | 13.34 | 1.64x |
| DeepSeek-V4-Flash-0731 | 8 | 202 | 39.82 | 19.70 | 2.02x |
| DeepSeek-V4-Flash-0731 | 16 | 202 | 66.76 | 27.49 | 2.43x |
| DeepSeek-V4-Flash-0731 | 32 | 202 | 99.22 | 36.20 | 2.74x |
| DeepSeek-V4-Flash-0731 | 64 | 202 | 127.09 | 43.55 | 2.92x |
| DeepSeek-V4-Flash-0731 | 256 | 202 | 145.13 | 48.74 | 2.98x |
| DeepSeek-V4-Flash-0731 | 1024 | 202 | 145.30 | 48.79 | 2.98x |
| DeepSeek-V4-Flash-0731 | 4096 | 202 | 145.30 | 48.79 | 2.98x |
| DeepSeek-V4-Flash-0731 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 231 | 11.58 | 9.55 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 231 | 22.09 | 13.78 | 1.60x |
| DeepSeek-V4-Flash-0731 | 8 | 231 | 40.34 | 20.26 | 1.99x |
| DeepSeek-V4-Flash-0731 | 16 | 231 | 68.33 | 28.71 | 2.38x |
| DeepSeek-V4-Flash-0731 | 32 | 231 | 103.04 | 37.98 | 2.71x |
| DeepSeek-V4-Flash-0731 | 64 | 231 | 133.95 | 45.87 | 2.92x |
| DeepSeek-V4-Flash-0731 | 256 | 231 | 154.72 | 51.61 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 231 | 154.92 | 51.66 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 231 | 154.92 | 51.66 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 347 | 11.68 | 10.15 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 347 | 22.44 | 15.21 | 1.48x |
| DeepSeek-V4-Flash-0731 | 8 | 347 | 41.59 | 21.88 | 1.90x |
| DeepSeek-V4-Flash-0731 | 16 | 347 | 72.20 | 32.56 | 2.22x |
| DeepSeek-V4-Flash-0731 | 32 | 347 | 112.75 | 43.11 | 2.62x |
| DeepSeek-V4-Flash-0731 | 64 | 347 | 152.11 | 53.42 | 2.85x |
| DeepSeek-V4-Flash-0731 | 256 | 347 | 180.96 | 60.40 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 347 | 181.25 | 60.47 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 347 | 181.25 | 60.47 | 3.00x |
| DeepSeek-V4-Pro-0813 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 2 | 29 | 9.90 | 5.83 | 1.70x |
| DeepSeek-V4-Pro-0813 | 4 | 29 | 16.26 | 7.87 | 2.07x |
| DeepSeek-V4-Pro-0813 | 8 | 29 | 23.12 | 10.16 | 2.27x |
| DeepSeek-V4-Pro-0813 | 16 | 29 | 27.56 | 12.57 | 2.19x |
| DeepSeek-V4-Pro-0813 | 32 | 29 | 28.86 | 14.82 | 1.95x |
| DeepSeek-V4-Pro-0813 | 64 | 29 | 28.99 | 16.64 | 1.74x |
| DeepSeek-V4-Pro-0813 | 256 | 29 | 29.00 | 18.25 | 1.59x |
| DeepSeek-V4-Pro-0813 | 1 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4-Pro-0813 | 2 | 40 | 10.41 | 6.38 | 1.63x |
| DeepSeek-V4-Pro-0813 | 4 | 40 | 17.91 | 8.83 | 2.03x |
| DeepSeek-V4-Pro-0813 | 8 | 40 | 27.35 | 11.70 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 40 | 35.41 | 14.84 | 2.39x |
| DeepSeek-V4-Pro-0813 | 32 | 40 | 39.15 | 17.91 | 2.19x |
| DeepSeek-V4-Pro-0813 | 64 | 40 | 39.92 | 20.48 | 1.95x |
| DeepSeek-V4-Pro-0813 | 256 | 40 | 40.00 | 22.81 | 1.75x |
| DeepSeek-V4-Pro-0813 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4-Pro-0813 | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4-Pro-0813 | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4-Pro-0813 | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4-Pro-0813 | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4-Pro-0813 | 1 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4-Pro-0813 | 2 | 76 | 11.09 | 7.54 | 1.47x |
| DeepSeek-V4-Pro-0813 | 4 | 76 | 20.29 | 10.66 | 1.90x |
| DeepSeek-V4-Pro-0813 | 8 | 76 | 34.38 | 14.92 | 2.30x |
| DeepSeek-V4-Pro-0813 | 16 | 76 | 51.52 | 19.89 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 76 | 65.85 | 25.12 | 2.62x |
| DeepSeek-V4-Pro-0813 | 64 | 76 | 72.99 | 29.79 | 2.45x |
| DeepSeek-V4-Pro-0813 | 256 | 76 | 75.49 | 34.28 | 2.20x |
| DeepSeek-V4-Pro-0813 | 1024 | 76 | 75.53 | 34.47 | 2.19x |
| DeepSeek-V4-Pro-0813 | 1 | 80 | 5.82 | 5.14 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 80 | 11.13 | 7.64 | 1.46x |
| DeepSeek-V4-Pro-0813 | 4 | 80 | 20.43 | 10.80 | 1.89x |
| DeepSeek-V4-Pro-0813 | 8 | 80 | 34.84 | 15.19 | 2.29x |
| DeepSeek-V4-Pro-0813 | 16 | 80 | 52.72 | 20.32 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 80 | 68.18 | 25.75 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 80 | 76.28 | 30.63 | 2.49x |
| DeepSeek-V4-Pro-0813 | 256 | 80 | 79.30 | 35.34 | 2.24x |
| DeepSeek-V4-Pro-0813 | 1024 | 80 | 79.36 | 35.53 | 2.23x |
| DeepSeek-V4-Pro-0813 | 1 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 82 | 11.15 | 7.68 | 1.45x |
| DeepSeek-V4-Pro-0813 | 4 | 82 | 20.50 | 10.86 | 1.89x |
| DeepSeek-V4-Pro-0813 | 8 | 82 | 35.06 | 15.32 | 2.29x |
| DeepSeek-V4-Pro-0813 | 16 | 82 | 53.29 | 20.53 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 82 | 69.30 | 26.05 | 2.66x |
| DeepSeek-V4-Pro-0813 | 64 | 82 | 77.88 | 31.04 | 2.51x |
| DeepSeek-V4-Pro-0813 | 256 | 82 | 81.20 | 35.85 | 2.26x |
| DeepSeek-V4-Pro-0813 | 1024 | 82 | 81.26 | 36.05 | 2.25x |
| DeepSeek-V4-Pro-0813 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 87 | 11.19 | 7.80 | 1.44x |
| DeepSeek-V4-Pro-0813 | 4 | 87 | 20.65 | 11.02 | 1.87x |
| DeepSeek-V4-Pro-0813 | 8 | 87 | 35.56 | 15.63 | 2.27x |
| DeepSeek-V4-Pro-0813 | 16 | 87 | 54.63 | 21.03 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 87 | 71.99 | 26.79 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 87 | 81.81 | 32.02 | 2.55x |
| DeepSeek-V4-Pro-0813 | 256 | 87 | 85.89 | 37.11 | 2.31x |
| DeepSeek-V4-Pro-0813 | 1024 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4-Pro-0813 | 1 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 94 | 11.24 | 7.94 | 1.41x |
| DeepSeek-V4-Pro-0813 | 4 | 94 | 20.85 | 11.23 | 1.86x |
| DeepSeek-V4-Pro-0813 | 8 | 94 | 36.19 | 16.05 | 2.25x |
| DeepSeek-V4-Pro-0813 | 16 | 94 | 56.34 | 21.70 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 94 | 75.50 | 27.77 | 2.72x |
| DeepSeek-V4-Pro-0813 | 64 | 94 | 87.07 | 33.34 | 2.61x |
| DeepSeek-V4-Pro-0813 | 256 | 94 | 92.34 | 38.79 | 2.38x |
| DeepSeek-V4-Pro-0813 | 1024 | 94 | 92.45 | 39.02 | 2.37x |
| DeepSeek-V4-Pro-0813 | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 111 | 11.34 | 8.26 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 111 | 21.22 | 11.67 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 111 | 37.44 | 16.97 | 2.21x |
| DeepSeek-V4-Pro-0813 | 16 | 111 | 59.81 | 23.14 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 111 | 82.95 | 29.94 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 111 | 98.78 | 36.26 | 2.72x |
| DeepSeek-V4-Pro-0813 | 256 | 111 | 107.35 | 42.56 | 2.52x |
| DeepSeek-V4-Pro-0813 | 1024 | 111 | 107.56 | 42.82 | 2.51x |
| DeepSeek-V4-Pro-0813 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 112 | 11.34 | 8.28 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 112 | 21.24 | 11.69 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 112 | 37.50 | 17.02 | 2.20x |
| DeepSeek-V4-Pro-0813 | 16 | 112 | 59.99 | 23.22 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 112 | 83.35 | 30.06 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 112 | 99.43 | 36.43 | 2.73x |
| DeepSeek-V4-Pro-0813 | 256 | 112 | 108.20 | 42.76 | 2.53x |
| DeepSeek-V4-Pro-0813 | 1024 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4-Pro-0813 | 1 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 113 | 11.35 | 8.30 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 113 | 21.26 | 11.72 | 1.81x |
| DeepSeek-V4-Pro-0813 | 8 | 113 | 37.56 | 17.07 | 2.20x |
| DeepSeek-V4-Pro-0813 | 16 | 113 | 60.17 | 23.29 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 113 | 83.74 | 30.18 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 113 | 100.07 | 36.59 | 2.74x |
| DeepSeek-V4-Pro-0813 | 256 | 113 | 109.05 | 42.97 | 2.54x |
| DeepSeek-V4-Pro-0813 | 1024 | 113 | 109.28 | 43.24 | 2.53x |
| DeepSeek-V4-Pro-0813 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 116 | 11.36 | 8.35 | 1.36x |
| DeepSeek-V4-Pro-0813 | 4 | 116 | 21.31 | 11.79 | 1.81x |
| DeepSeek-V4-Pro-0813 | 8 | 116 | 37.74 | 17.21 | 2.19x |
| DeepSeek-V4-Pro-0813 | 16 | 116 | 60.68 | 23.52 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 116 | 84.89 | 30.52 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 116 | 101.95 | 37.06 | 2.75x |
| DeepSeek-V4-Pro-0813 | 256 | 116 | 111.57 | 43.59 | 2.56x |
| DeepSeek-V4-Pro-0813 | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4-Pro-0813 | 1 | 125 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 125 | 11.40 | 8.49 | 1.34x |
| DeepSeek-V4-Pro-0813 | 4 | 125 | 21.45 | 11.99 | 1.79x |
| DeepSeek-V4-Pro-0813 | 8 | 125 | 38.23 | 17.62 | 2.17x |
| DeepSeek-V4-Pro-0813 | 16 | 125 | 62.11 | 24.16 | 2.57x |
| DeepSeek-V4-Pro-0813 | 32 | 125 | 88.13 | 31.52 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 125 | 107.37 | 38.43 | 2.79x |
| DeepSeek-V4-Pro-0813 | 256 | 125 | 118.96 | 45.37 | 2.62x |
| DeepSeek-V4-Pro-0813 | 1024 | 125 | 119.28 | 45.67 | 2.61x |
| DeepSeek-V4-Pro-0813 | 1 | 144 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 144 | 11.47 | 8.75 | 1.31x |
| DeepSeek-V4-Pro-0813 | 4 | 144 | 21.70 | 12.39 | 1.75x |
| DeepSeek-V4-Pro-0813 | 8 | 144 | 39.10 | 18.38 | 2.13x |
| DeepSeek-V4-Pro-0813 | 16 | 144 | 64.66 | 25.37 | 2.55x |
| DeepSeek-V4-Pro-0813 | 32 | 144 | 94.08 | 33.43 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 144 | 117.67 | 41.09 | 2.86x |
| DeepSeek-V4-Pro-0813 | 256 | 144 | 133.60 | 48.85 | 2.73x |
| DeepSeek-V4-Pro-0813 | 1024 | 144 | 134.09 | 49.19 | 2.73x |
| DeepSeek-V4-Pro-0813 | 1 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 146 | 11.47 | 8.78 | 1.31x |
| DeepSeek-V4-Pro-0813 | 4 | 146 | 21.73 | 12.43 | 1.75x |
| DeepSeek-V4-Pro-0813 | 8 | 146 | 39.17 | 18.45 | 2.12x |
| DeepSeek-V4-Pro-0813 | 16 | 146 | 64.89 | 25.48 | 2.55x |
| DeepSeek-V4-Pro-0813 | 32 | 146 | 94.64 | 33.61 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 146 | 118.68 | 41.35 | 2.87x |
| DeepSeek-V4-Pro-0813 | 256 | 146 | 135.07 | 49.20 | 2.75x |
| DeepSeek-V4-Pro-0813 | 1024 | 146 | 135.57 | 49.54 | 2.74x |
| DeepSeek-V4-Pro-0813 | 1 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 150 | 11.48 | 8.83 | 1.30x |
| DeepSeek-V4-Pro-0813 | 4 | 150 | 21.77 | 12.51 | 1.74x |
| DeepSeek-V4-Pro-0813 | 8 | 150 | 39.33 | 18.59 | 2.12x |
| DeepSeek-V4-Pro-0813 | 16 | 150 | 65.35 | 25.71 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 150 | 95.74 | 33.98 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 150 | 120.64 | 41.87 | 2.88x |
| DeepSeek-V4-Pro-0813 | 256 | 150 | 137.97 | 49.89 | 2.77x |
| DeepSeek-V4-Pro-0813 | 1024 | 150 | 138.50 | 50.23 | 2.76x |
| DeepSeek-V4-Pro-0813 | 1 | 170 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 170 | 11.53 | 9.05 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 170 | 21.96 | 12.88 | 1.70x |
| DeepSeek-V4-Pro-0813 | 8 | 170 | 39.99 | 19.23 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 170 | 67.36 | 26.78 | 2.52x |
| DeepSeek-V4-Pro-0813 | 32 | 170 | 100.66 | 35.70 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 170 | 129.67 | 44.29 | 2.93x |
| DeepSeek-V4-Pro-0813 | 256 | 170 | 151.63 | 53.12 | 2.85x |
| DeepSeek-V4-Pro-0813 | 1024 | 170 | 152.36 | 53.50 | 2.85x |
| DeepSeek-V4-Pro-0813 | 1 | 171 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 171 | 11.53 | 9.06 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 171 | 21.97 | 12.90 | 1.70x |
| DeepSeek-V4-Pro-0813 | 8 | 171 | 40.02 | 19.25 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 171 | 67.45 | 26.83 | 2.51x |
| DeepSeek-V4-Pro-0813 | 32 | 171 | 100.89 | 35.78 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 171 | 130.09 | 44.40 | 2.93x |
| DeepSeek-V4-Pro-0813 | 256 | 171 | 152.28 | 53.27 | 2.86x |
| DeepSeek-V4-Pro-0813 | 1024 | 171 | 153.02 | 53.65 | 2.85x |
| DeepSeek-V4-Pro-0813 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 173 | 11.54 | 9.09 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 173 | 21.98 | 12.94 | 1.70x |
| DeepSeek-V4-Pro-0813 | 8 | 173 | 40.08 | 19.31 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 173 | 67.63 | 26.93 | 2.51x |
| DeepSeek-V4-Pro-0813 | 32 | 173 | 101.33 | 35.95 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 173 | 130.91 | 44.63 | 2.93x |
| DeepSeek-V4-Pro-0813 | 256 | 173 | 153.57 | 53.58 | 2.87x |
| DeepSeek-V4-Pro-0813 | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4-Pro-0813 | 1 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 203 | 11.59 | 9.36 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 203 | 22.19 | 13.44 | 1.65x |
| DeepSeek-V4-Pro-0813 | 8 | 203 | 40.82 | 20.06 | 2.03x |
| DeepSeek-V4-Pro-0813 | 16 | 203 | 69.94 | 28.35 | 2.47x |
| DeepSeek-V4-Pro-0813 | 32 | 203 | 107.17 | 38.24 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 203 | 142.11 | 47.84 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 203 | 171.48 | 57.86 | 2.96x |
| DeepSeek-V4-Pro-0813 | 1024 | 203 | 172.53 | 58.30 | 2.96x |
| DeepSeek-V4-Pro-0813 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 231 | 11.63 | 9.58 | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | 231 | 22.34 | 13.86 | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | 231 | 41.34 | 20.63 | 2.00x |
| DeepSeek-V4-Pro-0813 | 16 | 231 | 71.61 | 29.55 | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | 231 | 111.55 | 40.16 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 231 | 150.80 | 50.51 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 231 | 186.03 | 61.46 | 3.03x |
| DeepSeek-V4-Pro-0813 | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 255 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 255 | 11.65 | 9.73 | 1.20x |
| DeepSeek-V4-Pro-0813 | 4 | 255 | 22.44 | 14.20 | 1.58x |
| DeepSeek-V4-Pro-0813 | 8 | 255 | 41.71 | 21.04 | 1.98x |
| DeepSeek-V4-Pro-0813 | 16 | 255 | 72.78 | 30.51 | 2.39x |
| DeepSeek-V4-Pro-0813 | 32 | 255 | 114.67 | 41.62 | 2.76x |
| DeepSeek-V4-Pro-0813 | 64 | 255 | 157.18 | 52.56 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 255 | 197.07 | 64.26 | 3.07x |
| DeepSeek-V4-Pro-0813 | 1024 | 255 | 198.60 | 64.78 | 3.07x |
| DeepSeek-V4-Pro-0813 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 347 | 11.72 | 10.18 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 347 | 22.70 | 15.30 | 1.48x |
| DeepSeek-V4-Pro-0813 | 8 | 347 | 42.66 | 22.28 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 347 | 75.90 | 33.59 | 2.26x |
| DeepSeek-V4-Pro-0813 | 32 | 347 | 123.23 | 45.96 | 2.68x |
| DeepSeek-V4-Pro-0813 | 64 | 347 | 175.33 | 59.00 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 347 | 230.16 | 73.28 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 347 | 232.44 | 73.90 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 347 | 232.44 | 73.90 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 1358 | 5.99 | 5.95 | 1.01x |
| DeepSeek-V4-Pro-0813 | 2 | 1358 | 11.86 | 11.38 | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | 1358 | 23.25 | 19.94 | 1.17x |
| DeepSeek-V4-Pro-0813 | 8 | 1358 | 44.72 | 29.80 | 1.50x |
| DeepSeek-V4-Pro-0813 | 16 | 1358 | 82.92 | 43.33 | 1.91x |
| DeepSeek-V4-Pro-0813 | 32 | 1358 | 143.86 | 67.35 | 2.14x |
| DeepSeek-V4-Pro-0813 | 64 | 1358 | 223.28 | 89.36 | 2.50x |
| DeepSeek-V4-Pro-0813 | 256 | 1358 | 329.44 | 116.81 | 2.82x |
| DeepSeek-V4-Pro-0813 | 1024 | 1358 | 334.59 | 118.22 | 2.83x |
| DeepSeek-V4-Pro-0813 | 4096 | 1358 | 334.59 | 118.22 | 2.83x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 890.50 | 54.1% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 1,259.70 | 47.8% |
| gpu | Qwen3-8B | 1 | 566.80 | 71.9% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 269.02 | 90.8% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 452.54 | 69.7% |
| rom | Qwen3-8B | 1 | 74.77 | 83.8% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| Qwen3-8B | sram | interleaved | 128 B | 1.00x |
| Qwen3-8B | hbm | interleaved | 32 B | 1.00x |
| DeepSeek-V4-Flash-0731 | sram | interleaved | 128 B | 1.00x |
| DeepSeek-V4-Flash-0731 | hbm | interleaved | 32 B | 1.00x |
| DeepSeek-V4-Pro-0813 | sram | interleaved | 128 B | 1.00x |
| DeepSeek-V4-Pro-0813 | hbm | interleaved | 32 B | 1.00x |

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
| Qwen3-8B | 1 | 2 | 90.60% | 16.81 | 9.27 |
| Qwen3-8B | 2 | 4 | 22.50% | 8.35 | 9.27 |
| Qwen3-8B | 4 | 4 | 22.50% | 8.35 | 9.27 |
| Qwen3-8B | 8 | 1 | 1.08% | 5.71 | 9.27 |
| Qwen3-8B | 16 | 1 | 1.08% | 5.71 | 9.27 |
| Qwen3-8B | 32 | 1 | 1.08% | 5.71 | 9.27 |
| Qwen3-8B | 64 | 1 | 1.21% | 6.42 | 9.27 |
| DeepSeek-V4-Flash-0731 | 1 | 15 | 50.49% | 16.14 | 2.13 |
| DeepSeek-V4-Flash-0731 | 2 | 1 | 1.59% | 1.93 | 2.13 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 1.59% | 1.93 | 2.13 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 1.59% | 1.93 | 2.13 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 1.59% | 1.93 | 2.13 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 1.59% | 1.93 | 2.13 |
| DeepSeek-V4-Pro-0813 | 1 | 78 | 97.47% | 157.92 | 2.08 |
| DeepSeek-V4-Pro-0813 | 2 | 2 | 12.07% | 28.59 | 2.08 |
| DeepSeek-V4-Pro-0813 | 4 | 2 | 12.07% | 28.59 | 2.08 |
| DeepSeek-V4-Pro-0813 | 8 | 2 | 12.07% | 28.59 | 2.08 |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 555.3 | 27,209.7 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 555.3 | 27,209.7 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 555.3 | 27,209.7 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 555.3 | 27,209.7 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 555.3 | 27,209.7 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 555.3 | 27,209.7 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 554.3 | 35,475.5 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 403.0 | 103,179.3 |
| Qwen3-8B | 1024 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 101.3 | 103,705.0 |
| Qwen3-8B | 4096 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 25.4 | 103,837.3 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,592.4 | 145,176.0 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,592.4 | 145,176.0 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,592.4 | 145,176.0 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,592.4 | 145,176.0 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,592.4 | 145,176.0 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,592.4 | 145,176.0 |
| DeepSeek-V4-Flash-0731 | 64 | 2.67% | 11.7 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 2,435.9 | 155,900.0 |
| DeepSeek-V4-Flash-0731 | 256 | 10.27% | 22.9 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 888.8 | 227,539.1 |
| DeepSeek-V4-Flash-0731 | 1024 | 35.19% | 59.6 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 247.1 | 253,032.8 |
| DeepSeek-V4-Flash-0731 | 4096 | 82.35% | 129.0 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 63.1 | 258,510.1 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 747.8 | 298,372.2 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 747.8 | 298,372.2 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 747.8 | 298,372.2 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 747.8 | 298,372.2 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 747.8 | 298,372.2 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 747.8 | 298,372.2 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 747.8 | 298,372.2 |
| DeepSeek-V4-Pro-0813 | 256 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 747.8 | 298,372.2 |
| DeepSeek-V4-Pro-0813 | 1024 | 3.96% | 59.4 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 339.9 | 348,028.1 |
| DeepSeek-V4-Pro-0813 | 4096 | 14.93% | 149.5 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 92.1 | 377,103.5 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 282 |
| gpu | kv_read | 105 |
| gpu | layer_fixed_latency | 684 |
| gpu | link_latency | 2004 |
| gpu | thermal | 72 |
| gpu | weight_read | 803 |
| rom | compute | 309 |
| rom | infeasible | 6481 |
| rom | kv_read | 287 |
| rom | layer_fixed_latency | 1106 |
| rom | link_latency | 1947 |
| rom | thermal | 461 |
| rom | weight_read | 1159 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 282 |
| rom | CAPACITY | 6481 |

## Mechanical consistency audit

**FAIL** over 290,056 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x16', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x57', 'Qwen3-8B', 1)
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
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x5', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x8', 'Qwen3-8B', 1)

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

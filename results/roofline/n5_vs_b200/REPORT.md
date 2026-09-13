# Area-constrained roofline: n5_vs_b200

> Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 527x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 1 device. On the GPU side the correction reaches 272x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 8 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Qwen3-8B takes 5 x 815 mm2 (4,075 mm2, array, KV in SRAM) at 4,941 tok/s per user and 1,213 tok/s per 1,000 mm2, holding 1 session, against 3 copies of one unified HBM die at the same silicon: 5.0x per user. DeepSeek-V4-Flash-0731 takes 30 x 815 mm2 (24,450 mm2, array, KV in SRAM) at 2,627 tok/s per user and 107 tok/s per 1,000 mm2, holding 1 session, against 15 copies of one unified HBM die at the same silicon: 1.8x per user. DeepSeek-V4-Pro-0813 takes 3 x 46,225 mm2 (138,675 mm2, wafer, KV in HBM) at 2,649 tok/s per user and 19 tok/s per 1,000 mm2, holding 265 sessions, against 87 copies of one unified HBM die at the same silicon: 3.5x per user. Two granularities come out of one rule, which is the point: the class is chosen per model on evidence rather than assumed. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Qwen3-8B on 3,260 mm2 of ROM silicon at 3,911 tok/s per user against 3,200 mm2 of b200_sxm-x2-tensor at 694 tok/s: **5.6x**, ROM binding on `link_latency` and the GPU on `weight_read`. It holds 335 resident sessions against the GPU cluster's 254. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 97.47x to it.** At 554,700 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 8.08 tok/s and the same silicon running tensor delivers 788 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.07x (Qwen3-8B, ROM binding on `weight_read`) to 17.24x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 20.3% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 766 to 24,586 tok/s, and its rate with every slot occupied from 23,744 to 24,586. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 31 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 896 us over NVLink, capping per-user decode at 1,116 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 1,478.2 us and cap it at 677 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 1.3x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 20 of 24 operating points and an array 4; on tokens per second per square millimetre the same points go 15 to the array and 9 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 248 of 4638 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 24.9x of aggregate throughput (Qwen3-8B). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 5.64x, on DeepSeek-V4-Flash-0731 at batch 256, where the busiest region carries 2.92x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 42 of 48 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 387 of 4,638 feasible points (8.3%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x16` at batch 256 on 13,040 mm2, throttled 1.52x from 208 to 137 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 96% kv read against 0.1% weight read. The ROM sweep is not what melts it.


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

**Recommended: `ROM-N5-native-SRAMKV-array-pipeline-x5-romfill`** -- 5 x 815 mm2 reticle dies, 4,075 mm2 total, `pipeline`-parallel, KV in SRAM, spare silicon to `rom`.

- **4,941.0 tok/s per user** (0.20 ms/token), binding on `weight_read`
- **1,212.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,941 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 396 W at 0.097 W/mm2, 80.1 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 3 copies of one unified HBM die -- `b200_sxm-x3-tensor`, 4,800 mm2, area ratio 0.8490 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 4,075 | 4,800 | 0.8490 |
| user tok/s | 4,941.0 | 978.7 | 5.05x |
| aggregate tok/s | 4,941 | 979 | 5.05x |
| resident sessions | 1 | 388 | -- |
| J/token | 0.0801 | 2.7972 | 34.9x |

**The areas do not match exactly, and the mismatch is stated rather than rounded away.** A GPU cluster is quantised in whole dies and a ROM design is not, so at 4,075 mm2 the closest whole number of 1,600 mm2 dies is 3, i.e. 4,800 mm2. The ROM side is therefore compared against 18% MORE silicon than it has, which makes the ratio CONSERVATIVE for the ROM side.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 388 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x8-tensor` at 12,800 mm2 and 2,013.6 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 | 3.46x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 | 3.46x |
| smallest feasible machine | `ROM-N5-native-HBMKV-array-tensor-x4` | 3,260 | 3,911.3 | 1,199.8 | 335 | 5.64x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-pipeline-x5-romfill` | 4,075 | 4,941.0 | 1,212.5 | 1 | 5.05x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-pipeline-x5-romfill` | 4,075 | 4,941.0 | 1,212.5 | -- | 1,212.5 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-pipeline-x6-romfill` | 4,890 | 4,990.6 | 1,020.6 | 60.9 | 1,212.5 | stop |
| `ROM-N5-native-SRAMKV-array-pipeline-x7-romfill` | 5,705 | 5,016.3 | 879.3 | 46.2 | 1,212.5 | stop |
| `ROM-N5-native-SRAMKV-array-pipeline-x8-romfill` | 6,520 | 5,027.2 | 771.0 | 35.3 | 1,212.5 | stop |
| `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 36.1 | 1,212.5 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-pipeline-x5-romfill` **<-- recommended** | 4,075 | 5 | 4,941.0 | 4,941 | 1,212.5 | 1 | `weight_read` | 396 | 80.1 | `b200_sxm-x3-tensor` | 5.05x |
| `ROM-N5-native-SRAMKV-array-pipeline-x6-romfill` | 4,890 | 6 | 4,990.6 | 4,991 | 1,020.6 | 1 | `weight_read` | 466 | 93.4 | `b200_sxm-x3-tensor` | 5.10x |
| `ROM-N5-native-SRAMKV-array-pipeline-x7-romfill` | 5,705 | 7 | 5,016.3 | 5,016 | 879.3 | 1 | `weight_read` | 536 | 106.8 | `b200_sxm-x4-tensor` | 4.07x |
| `ROM-N5-native-SRAMKV-array-pipeline-x8-romfill` | 6,520 | 8 | 5,027.2 | 5,027 | 771.0 | 1 | `weight_read` | 606 | 120.5 | `b200_sxm-x4-tensor` | 4.08x |
| `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 1 | 6,464.4 | 6,464 | 139.8 | 1 | `link_latency` | 4,016 | 621.2 | `b200_sxm-x29-hybrid` | 3.46x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 116 | densest | `ROM-N5-native-SRAMKV-array-pipeline-x5-romfill` | 4,075 | 4,941.0 | 1,212.5 | 1 |
| array | 116 | fastest | `ROM-N5-native-SRAMKV-array-pipeline-x8-romfill` | 6,520 | 5,027.2 | 771.0 | 1 |
| array | 116 | smallest | `ROM-N5-native-HBMKV-array-tensor-x4` | 3,260 | 3,911.3 | 1,199.8 | 335 |
| wafer | 80 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |
| wafer | 80 | fastest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |
| wafer | 80 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 139.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-pipeline-x8-romfill` | 6,520 | 5,027.2 | 5,027 | 1 | 606 | 120.5 | `weight_read` | `b200_sxm-x4-tensor` | 1,232.0 | 522 | 2,860.8 | 1.019 | 4.08x | 23.7x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | 6,464 | 1 | 4,016 | 621.2 | `link_latency` | `b200_sxm-x29-hybrid` | 1,866.3 | 3,875 | 3,084.4 | 0.996 | 3.46x | 5.0x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x57-romfill` | 46,455 | 4,191.8 | 33,534 | 4,777 | 9,556 | 285.0 | `link_latency` | `b200_sxm-x29-hybrid` | 1,866.3 | 3,875 | 3,084.4 | 1.001 | 2.25x | 10.8x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 6,464.4 | -- | 1 | -- | 621.2 | -- | -- | -- | -- | -- | 1.005 | 1.54x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hybrid-x16-romfill` | 13,040 | 4,528.6 | 9,057 | 1,341 | 2,634 | 290.8 | `link_latency` | `b200_sxm-x8-tensor` | 1,917.0 | 1,059 | 1,658.7 | 1.019 | 2.36x | 5.7x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,400.8 | 10,802 | 1,441 | 9,676 | 895.8 | `link_latency` | `b200_sxm-x58-hybrid` | 1,836.2 | 7,764 | 3,106.7 | 0.996 | 2.94x | 3.5x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x113-romfill` | 92,095 | 3,973.8 | 59,607 | 9,471 | 18,005 | 302.1 | `link_latency` | `b200_sxm-x58-hybrid` | 1,836.2 | 7,764 | 3,106.7 | 0.992 | 2.16x | 10.3x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,400.8 | -- | 1,441 | -- | 895.8 | -- | -- | -- | -- | -- | 0.996 | 1.36x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hybrid-x57-romfill` | 46,455 | 4,191.8 | 33,534 | 4,777 | 9,556 | 285.0 | `link_latency` | `b200_sxm-x29-hybrid` | 1,866.3 | 3,875 | 3,084.4 | 1.001 | 2.25x | 10.8x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 5,121.2 | 20,485 | 2,883 | 19,199 | 937.3 | `link_latency` | `b200_sxm-x116-hybrid` | 1,858.0 | 15,543 | 3,181.6 | 0.996 | 2.76x | 3.4x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 3,560.3 | 103,249 | 19,026 | 33,916 | 328.5 | `link_latency` | `b200_sxm-x116-hybrid` | 1,858.0 | 15,543 | 3,181.6 | 0.997 | 1.92x | 9.7x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 5,121.2 | -- | 2,883 | -- | 937.3 | -- | -- | -- | -- | -- | 1.001 | 1.44x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hybrid-x57-romfill` | 46,455 | 4,191.8 | 33,534 | 4,777 | 9,556 | 285.0 | `link_latency` | `b200_sxm-x29-hybrid` | 1,773.8 | 3,875 | 1,643.7 | 1.001 | 2.36x | 5.8x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 4,640.7 | 37,125 | 5,766 | 37,873 | 1,020.1 | `link_latency` | `b200_sxm-x231-hybrid` | 1,787.5 | 30,965 | 3,284.6 | 1.001 | 2.60x | 3.2x |
| 16 | array | `ROM-N5-native-HBMKV-array-hybrid-x113-romfill` | 92,095 | 3,928.4 | 62,854 | 9,471 | 18,431 | 293.2 | `link_latency` | `b200_sxm-x58-hybrid` | 1,744.6 | 7,764 | 1,655.6 | 0.992 | 2.25x | 5.6x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,040.9 | 64,655 | 8,650 | 57,959 | 896.4 | `link_latency` | `b200_sxm-x347-hybrid` | 1,730.2 | 46,522 | 3,320.3 | 0.999 | 2.34x | 3.7x |
| 32 | array | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 3,503.0 | 112,096 | 19,026 | 35,076 | 312.9 | `link_latency` | `b200_sxm-x116-hybrid` | 1,754.1 | 15,543 | 1,602.0 | 0.997 | 2.00x | 5.1x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,395.4 | 108,653 | 8,650 | 63,730 | 586.5 | `link_latency` | `b200_sxm-x347-hybrid` | 1,730.2 | 46,522 | 3,320.3 | 0.999 | 1.96x | 5.7x |
| 64 | array | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 277,100 | 3,145.5 | 201,312 | 28,498 | 56,867 | 282.5 | `link_latency` | `b200_sxm-x173-hybrid` | 1,657.6 | 23,187 | 1,250.4 | 1.001 | 1.90x | 4.4x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,573.2 | 164,688 | 8,650 | 71,079 | 431.6 | `link_latency` | `b200_sxm-x347-hybrid` | 1,688.9 | 46,522 | 2,350.8 | 0.999 | 1.52x | 5.4x |
| 256 | array | `ROM-N5-native-HBMKV-array-pipeline-x340-romfill` | 277,100 | 2,343.2 | 796,702 | 28,498 | 138,550 | 173.9 | `thermal` | `b200_sxm-x173-hybrid` | 1,169.3 | 23,187 | 471.2 | 1.001 | 2.00x | 2.7x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,049.1 | 268,569 | 8,650 | 117,162 | 436.2 | `kv_read` | `b200_sxm-x347-hybrid` | 1,374.0 | 46,522 | 751.1 | 0.999 | 0.76x | 1.7x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-pipeline-x5-romfill` | 4,075 | array | SRAM | 1 |
| 2 | `ROM-N5-native-HBMKV-array-tensor-x4` | 3,260 | array | HBM | 335 |
| 4 | `ROM-N5-native-HBMKV-array-pipeline-x4` | 3,260 | array | HBM | 335 |
| 8-256 | `ROM-N5-native-HBMKV-array-tensor-x4` | 3,260 | array | HBM | 335 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Flash-0731 at 200,000 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hybrid-x30`** -- 30 x 815 mm2 reticle dies, 24,450 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **2,627.4 tok/s per user** (0.38 ms/token), binding on `link_latency`
- **107.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 2,627 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 1,517 W at 0.062 W/mm2, 577.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 15 copies of one unified HBM die -- `b200_sxm-x15-hybrid`, 24,000 mm2, area ratio 1.0188 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 24,450 | 24,000 | 1.0188 |
| user tok/s | 2,627.4 | 1,465.1 | 1.79x |
| aggregate tok/s | 2,627 | 2,930 | 0.90x |
| resident sessions | 1 | 1,637 | -- |
| J/token | 0.5773 | 3.0092 | 5.2x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 1,637 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x16-hybrid` at 25,600 mm2 and 1,499.3 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,850.6 | 104.9 | 1 | 3.73x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,850.6 | 104.9 | 1 | 3.73x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hybrid-x29` | 23,635 | 2,450.3 | 103.7 | 1 | 1.67x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hybrid-x30` | 24,450 | 2,627.4 | 107.5 | 1 | 1.79x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hybrid-x30` | 24,450 | 2,627.4 | 107.5 | -- | 107.5 | ACCEPT |
| `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,850.6 | 104.9 | 102.1 | 107.5 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hybrid-x30` **<-- recommended** | 24,450 | 30 | 2,627.4 | 2,627 | 107.5 | 1 | `link_latency` | 1,517 | 577.3 | `b200_sxm-x15-hybrid` | 1.79x |
| `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 1 | 4,850.6 | 4,851 | 104.9 | 1 | `link_latency` | 3,960 | 816.3 | `b200_sxm-x29-tensor` | 3.73x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 144 | densest | `ROM-N5-native-SRAMKV-array-hybrid-x30` | 24,450 | 2,627.4 | 107.5 | 1 |
| array | 144 | fastest | `ROM-N5-native-SRAMKV-array-hybrid-x30` | 24,450 | 2,627.4 | 107.5 | 1 |
| array | 144 | smallest | `ROM-N5-native-SRAMKV-array-hybrid-x29` | 23,635 | 2,450.3 | 103.7 | 1 |
| wafer | 80 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,850.6 | 104.9 | 1 |
| wafer | 80 | fastest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,850.6 | 104.9 | 1 |
| wafer | 80 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,850.6 | 104.9 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hybrid-x30` | 24,450 | 2,627.4 | 2,627 | 1 | 1,517 | 577.3 | `link_latency` | `b200_sxm-x15-hybrid` | 1,465.1 | 1,637 | 3,009.2 | 1.019 | 1.79x | 5.2x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,850.6 | 4,851 | 1 | 3,960 | 816.3 | `link_latency` | `b200_sxm-x29-tensor` | 1,300.7 | 3,279 | 9,028.4 | 0.996 | 3.73x | 11.1x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hybrid-x56-romfill` | 45,640 | 2,191.5 | 2,191 | 1 | 3,893 | 1,776.3 | `link_latency` | `b200_sxm-x29-tensor` | 1,300.7 | 3,279 | 9,028.4 | 0.984 | 1.68x | 5.1x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,850.6 | -- | 1 | -- | 816.3 | -- | -- | -- | -- | -- | 0.987 | 2.21x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hybrid-x32` | 26,080 | 2,627.4 | 10,509 | 2,345 | 2,404 | 228.8 | `link_latency` | `b200_sxm-x16-hybrid` | 1,499.3 | 1,755 | 3,085.1 | 1.019 | 1.75x | 13.5x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | 4,849.3 | 9,699 | 630 | 4,465 | 460.4 | `link_latency` | `b200_sxm-x29-tensor` | 1,161.6 | 3,279 | 5,177.1 | 0.996 | 4.17x | 11.2x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x58-romfill` | 47,270 | 2,004.8 | 16,038 | 4,250 | 5,684 | 354.4 | `weight_read` | `b200_sxm-x30-tensor` | 1,166.0 | 3,396 | 5,311.0 | 0.985 | 1.72x | 15.0x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | 4,849.3 | -- | 630 | -- | 460.4 | -- | -- | -- | -- | -- | 1.023 | 2.42x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hybrid-x32` | 26,080 | 2,627.4 | 10,509 | 2,345 | 2,404 | 228.8 | `link_latency` | `b200_sxm-x16-hybrid` | 1,215.6 | 1,755 | 1,955.8 | 1.019 | 2.16x | 8.5x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | 4,744.7 | 18,979 | 630 | 4,803 | 253.1 | `link_latency` | `b200_sxm-x29-hybrid` | 1,116.3 | 3,279 | 3,491.2 | 0.996 | 4.25x | 13.8x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x58-romfill` | 47,270 | 2,004.8 | 16,038 | 4,250 | 5,684 | 354.4 | `weight_read` | `b200_sxm-x30-hybrid` | 1,128.3 | 3,396 | 3,544.7 | 0.985 | 1.78x | 10.0x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | 4,744.7 | -- | 630 | -- | 253.1 | -- | -- | -- | -- | -- | 1.023 | 2.37x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hybrid-x37` | 30,155 | 2,365.6 | 18,925 | 2,711 | 3,375 | 178.3 | `link_latency` | `b200_sxm-x19-hybrid` | 856.3 | 2,106 | 1,669.7 | 0.992 | 2.76x | 9.4x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,553.2 | 36,426 | 1,260 | 9,549 | 262.1 | `link_latency` | `b200_sxm-x58-tensor` | 832.4 | 6,679 | 3,524.5 | 0.996 | 5.47x | 13.4x |
| 8 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x116-romfill` | 94,540 | 2,009.0 | 30,135 | 8,500 | 11,292 | 374.7 | `link_latency` | `b200_sxm-x59-tensor` | 834.0 | 6,797 | 3,571.1 | 1.001 | 2.41x | 9.5x |
| 8 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,553.2 | -- | 1,260 | -- | 262.1 | -- | -- | -- | -- | -- | 1.023 | 2.27x wafer/array | -- |
| 16 | array | `ROM-N5-native-HBMKV-array-hybrid-x37` | 30,155 | 2,341.6 | 37,465 | 2,711 | 4,050 | 108.1 | `link_latency` | `b200_sxm-x19-hybrid` | 633.5 | 2,106 | 1,190.7 | 0.992 | 3.70x | 11.0x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,346.7 | 69,546 | 2,520 | 18,975 | 272.8 | `link_latency` | `b200_sxm-x116-tensor` | 639.9 | 13,480 | 4,362.6 | 0.996 | 6.79x | 16.0x |
| 16 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 1,902.9 | 55,185 | 16,635 | 21,950 | 397.7 | `link_latency` | `b200_sxm-x116-tensor` | 639.9 | 13,480 | 4,362.6 | 0.997 | 2.97x | 11.0x |
| 16 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,346.7 | -- | 2,520 | -- | 272.8 | -- | -- | -- | -- | -- | 1.001 | 2.28x wafer/array | -- |
| 32 | array | `ROM-N5-native-HBMKV-array-hybrid-x44` | 35,860 | 2,109.5 | 67,505 | 3,224 | 6,070 | 89.9 | `link_latency` | `b200_sxm-x22-hybrid` | 482.7 | 2,458 | 936.0 | 1.019 | 4.37x | 10.4x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 3,985.1 | 127,523 | 5,041 | 37,521 | 294.2 | `link_latency` | `b200_sxm-x231-tensor` | 440.6 | 26,964 | 6,060.6 | 1.001 | 9.05x | 20.6x |
| 64 | array | `ROM-N5-native-HBMKV-array-hybrid-x87-romfill` | 70,905 | 1,994.8 | 127,667 | 6,375 | 12,291 | 96.3 | `link_latency` | `b200_sxm-x44-hybrid` | 360.3 | 5,038 | 1,105.6 | 1.007 | 5.54x | 11.5x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,511.7 | 224,746 | 7,562 | 57,483 | 255.8 | `link_latency` | `b200_sxm-x347-tensor` | 271.2 | 40,565 | 7,244.5 | 0.999 | 12.95x | 28.3x |
| 256 | array | `ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 1,731.6 | 443,291 | 16,635 | 36,048 | 81.3 | `link_latency` | `b200_sxm-x116-hybrid` | 184.7 | 13,480 | 1,245.5 | 0.997 | 9.38x | 15.3x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,271.5 | 581,510 | 7,562 | 70,339 | 121.0 | `link_latency` | `b200_sxm-x347-hybrid` | 131.8 | 40,565 | 4,124.0 | 0.999 | 17.24x | 34.1x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hybrid-x30` | 24,450 | array | SRAM | 1 |
| 2-4 | `ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 46,225 | wafer | HBM | 630 |
| 8 | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 46,225 | wafer | HBM | 630 |
| 16 | `ROM-N5-native-HBMKV-array-hybrid-x37` | 30,155 | array | HBM | 2,711 |
| 32-64 | `ROM-N5-native-HBMKV-array-hybrid-x44` | 35,860 | array | HBM | 3,224 |
| 256 | `ROM-N5-native-HBMKV-array-hybrid-x87` | 70,905 | array | HBM | 6,375 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

### DeepSeek-V4-Pro-0813 at 1,000,000 tokens

**Recommended: `ROM-N5-native-HBMKV-wafer-hybrid-x3`** -- 3 x 46,225 mm2 wafers, 138,675 mm2 total, `hybrid`-parallel, KV in HBM, spare silicon to `sram`.

- **2,648.8 tok/s per user** (0.38 ms/token), binding on `link_latency`
- **19.1 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 7,946 tok/s aggregate with every slot full, over 265 resident sessions (fill limited by `pipeline_slots`)
- 10,554 W at 0.076 W/mm2, 1,328.1 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 87 copies of one unified HBM die -- `b200_sxm-x87-tensor`, 139,200 mm2, area ratio 0.9962 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 138,675 | 139,200 | 0.9962 |
| user tok/s | 2,648.8 | 746.8 | 3.55x |
| aggregate tok/s | 7,946 | 747 | 10.64x |
| resident sessions | 265 | 1,339 | -- |
| J/token | 1.3281 | 45.2422 | 34.1x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 265 sessions against one that holds 1,339 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x347-tensor` at 555,200 mm2 and 787.5 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 19.1 | 1 | 3.55x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 19.1 | 1 | 3.55x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-tensor-x155` | 126,325 | 1,036.7 | 8.2 | 1 | 1.40x |
| **after -- this report's rule** | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 19.1 | 265 | 3.55x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-HBMKV-wafer-hybrid-x3` **<-- recommended** | 138,675 | 3 | 2,648.8 | 7,946 | 19.1 | 265 | `link_latency` | 10,554 | 1,328.1 | `b200_sxm-x87-tensor` | 3.55x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 96 | densest | `ROM-N5-native-SRAMKV-array-tensor-x155` | 126,325 | 1,036.7 | 8.2 | 1 |
| array | 96 | fastest | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 277,100 | 1,062.3 | 3.8 | 1 |
| array | 96 | smallest | `ROM-N5-native-SRAMKV-array-tensor-x155` | 126,325 | 1,036.7 | 8.2 | 1 |
| wafer | 60 | densest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 19.1 | 1 |
| wafer | 60 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 19.1 | 1 |
| wafer | 60 | smallest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 19.1 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 277,100 | 1,062.3 | 1,062 | 1 | 23,561 | 22,179.4 | `link_latency` | `b200_sxm-x173-tensor` | 773.0 | 2,752 | 82,849.4 | 1.001 | 1.37x | 3.7x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 2,649 | 1 | 7,914 | 2,987.8 | `link_latency` | `b200_sxm-x87-tensor` | 746.8 | 1,339 | 45,242.2 | 0.996 | 3.55x | 15.1x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-tensor-x170` | 138,550 | 1,053.4 | 1,053 | 1 | 8,532 | 8,099.2 | `link_latency` | `b200_sxm-x87-tensor` | 746.8 | 1,339 | 45,242.2 | 0.995 | 1.41x | 5.6x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | -- | 1 | -- | 2,987.8 | -- | -- | -- | -- | -- | 0.999 | 2.51x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 277,100 | 951.6 | 1,903 | 3,492 | 30,143 | 15,838.2 | `link_latency` | `b200_sxm-x173-tensor` | 677.0 | 2,752 | 47,770.6 | 1.001 | 1.41x | 3.0x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 7,946 | 265 | 10,554 | 1,328.1 | `link_latency` | `b200_sxm-x87-tensor` | 638.3 | 1,339 | 26,879.0 | 0.996 | 4.15x | 20.2x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-tensor-x170` | 138,550 | 925.9 | 1,852 | 1,746 | 10,986 | 5,933.0 | `link_latency` | `b200_sxm-x87-tensor` | 638.3 | 1,339 | 26,879.0 | 0.995 | 1.45x | 4.5x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | -- | 265 | -- | 1,328.1 | -- | -- | -- | -- | -- | 0.999 | 2.86x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hybrid-x167` | 136,105 | 843.5 | 17,713 | 1,715 | 14,658 | 827.5 | `compute` | `b200_sxm-x85-tensor` | 505.3 | 1,306 | 17,008.9 | 1.001 | 1.67x | 20.6x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,648.3 | 10,593 | 265 | 11,209 | 1,058.1 | `link_latency` | `b200_sxm-x87-tensor` | 506.7 | 1,339 | 17,314.2 | 0.996 | 5.23x | 16.4x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x167` | 136,105 | 843.5 | 17,713 | 1,715 | 14,658 | 827.5 | `compute` | `b200_sxm-x85-tensor` | 505.3 | 1,306 | 17,008.9 | 1.001 | 1.67x | 20.6x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,648.3 | -- | 265 | -- | 1,058.1 | -- | -- | -- | -- | -- | 0.981 | 3.14x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hybrid-x167` | 136,105 | 843.5 | 17,713 | 1,715 | 14,658 | 827.5 | `compute` | `b200_sxm-x85-tensor` | 376.1 | 1,306 | 11,777.8 | 1.001 | 2.24x | 14.2x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,374.1 | 18,993 | 353 | 20,125 | 1,059.6 | `link_latency` | `b200_sxm-x116-tensor` | 390.3 | 1,816 | 14,895.6 | 0.996 | 6.08x | 14.1x |
| 8 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x227` | 185,005 | 670.7 | 19,451 | 2,331 | 23,033 | 1,184.2 | `weight_read` | `b200_sxm-x116-tensor` | 390.3 | 1,816 | 14,895.6 | 0.997 | 1.72x | 12.6x |
| 8 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,374.1 | -- | 353 | -- | 1,059.6 | -- | -- | -- | -- | -- | 1.001 | 3.54x wafer/array | -- |
| 16 | array | `ROM-N5-native-HBMKV-array-hybrid-x167` | 136,105 | 843.5 | 17,713 | 1,715 | 14,658 | 827.5 | `compute` | `b200_sxm-x85-tensor` | 257.5 | 1,306 | 8,855.2 | 1.001 | 3.28x | 10.7x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 2,233.4 | 35,734 | 530 | 33,559 | 939.1 | `link_latency` | `b200_sxm-x173-tensor` | 278.2 | 2,752 | 15,246.7 | 1.002 | 8.03x | 16.2x |
| 16 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 277,100 | 587.9 | 25,280 | 3,492 | 36,135 | 1,429.4 | `weight_read` | `b200_sxm-x173-tensor` | 278.2 | 2,752 | 15,246.7 | 1.001 | 2.11x | 10.7x |
| 16 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 2,233.4 | -- | 530 | -- | 939.1 | -- | -- | -- | -- | -- | 0.999 | 3.80x wafer/array | -- |
| 32 | array | `ROM-N5-native-HBMKV-array-hybrid-x193` | 157,295 | 750.8 | 24,027 | 1,982 | 19,667 | 818.5 | `weight_read` | `b200_sxm-x98-tensor` | 166.8 | 1,520 | 7,839.4 | 1.003 | 4.50x | 9.6x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,086.5 | 66,767 | 1,060 | 65,939 | 987.6 | `link_latency` | `b200_sxm-x347-tensor` | 185.6 | 5,612 | 21,874.1 | 0.999 | 11.24x | 22.1x |
| 64 | array | `ROM-N5-native-HBMKV-array-hybrid-x193` | 157,295 | 742.3 | 47,507 | 1,982 | 25,478 | 536.3 | `weight_read` | `b200_sxm-x98-tensor` | 100.4 | 1,520 | 6,493.9 | 1.003 | 7.39x | 12.1x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,535.9 | 98,296 | 1,060 | 73,683 | 749.6 | `kv_read` | `b200_sxm-x347-tensor` | 109.5 | 5,612 | 18,507.2 | 0.999 | 14.03x | 24.7x |
| 256 | array | `ROM-N5-native-HBMKV-array-hybrid-x308-romfill` | 251,020 | 561.1 | 143,641 | 3,164 | 62,604 | 435.8 | `weight_read` | `b200_sxm-x157-hybrid` | 47.1 | 2,489 | 6,263.0 | 0.999 | 11.91x | 14.4x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 594.5 | 152,199 | 1,060 | 107,593 | 706.9 | `kv_read` | `b200_sxm-x347-hybrid` | 36.1 | 5,612 | 15,201.7 | 0.999 | 16.48x | 21.5x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-32 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | wafer | HBM | 265 |
| 64 | `ROM-N5-native-HBMKV-array-hybrid-x193` | 157,295 | array | HBM | 1,982 |
| 256 | `ROM-N5-native-HBMKV-array-hybrid-x231` | 188,265 | array | HBM | 2,373 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 31, 32, 37, 44, 57, 58, 87, 113, 116, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 31, 32, 37, 44, 57, 58, 87, 113, 116, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 29, 30, 35, 42, 56, 57, 84, 112, 113, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 29, 30, 35, 42, 56, 57, 84, 112, 113, 170, 227, 340 |
| DeepSeek-V4-Pro-0813 | HBM | rom | 163, 167, 170, 193, 227, 231, 308, 340 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 163, 167, 170, 193, 227, 231, 308, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 155, 159, 170, 184, 221, 227, 294, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 155, 159, 170, 184, 221, 227, 294, 340 |
| Qwen3-8B | HBM | rom | 4, 5, 6, 8, 12, 16, 57, 113, 170, 227, 340 |
| Qwen3-8B | HBM | sram | 4, 5, 6, 7, 8, 12, 16, 57, 113, 170, 227, 340 |
| Qwen3-8B | SRAM | rom | 5, 6, 7, 8, 12, 16, 57, 113, 170, 227, 340 |
| Qwen3-8B | SRAM | sram | 5, 6, 8, 12, 16, 57, 113, 170, 227, 340 |

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

- **387 of 4,638 feasible points (8.3%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 102, rom 285.
- By area class: large array (5,000-40,000 mm2) 147, small array (1,600-5,000 mm2) 141, wafer (>=40,000 mm2) 99.
- By KV store: hbm 387.
- By batch: B=1 36, B=2 36, B=4 36, B=8 38, B=16 55, B=32 60, B=64 62, B=256 64.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 47% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 256.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 232 | 27 | 66.2% | 100.0% | 0.625 | 53% |
| gpu | small array (1,600-5,000 mm2) | 30 | 19 | 100.0% | 100.0% | 0.625 | 35% |
| gpu | wafer (>=40,000 mm2) | 1,008 | 56 | 44.6% | 100.0% | 0.625 | 79% |
| rom | large array (5,000-40,000 mm2) | 446 | 120 | 28.5% | 100.0% | 0.500 | 64% |
| rom | small array (1,600-5,000 mm2) | 176 | 122 | 100.0% | 100.0% | 0.500 | 21% |
| rom | wafer (>=40,000 mm2) | 2,746 | 43 | 24.1% | 100.0% | 0.500 | 88% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x16` | Qwen3-8B | 256 | 13,040 | hbm | 1.525x | 6,520.0 / 6,520.0 W | 29% | 136.6 | 208.2 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x16` | Qwen3-8B | 64 | 13,040 | hbm | 1.510x | 6,520.0 / 6,520.0 W | 29% | 542.7 | 819.7 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x12` | Qwen3-8B | 256 | 9,780 | hbm | 1.503x | 4,890.0 / 4,890.0 W | 28% | 104.1 | 156.5 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x12` | Qwen3-8B | 64 | 9,780 | hbm | 1.496x | 4,890.0 / 4,890.0 W | 28% | 414.3 | 619.9 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x12` | Qwen3-8B | 32 | 9,780 | hbm | 1.487x | 4,890.0 / 4,890.0 W | 28% | 823.2 | 1,224.0 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x8` | Qwen3-8B | 256 | 6,520 | hbm | 1.460x | 3,260.0 / 3,260.0 W | 26% | 71.6 | 104.6 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x8` | Qwen3-8B | 64 | 6,520 | hbm | 1.458x | 3,260.0 / 3,260.0 W | 26% | 285.5 | 416.3 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x8` | Qwen3-8B | 32 | 6,520 | hbm | 1.456x | 3,260.0 / 3,260.0 W | 26% | 568.4 | 827.4 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x16` | Qwen3-8B | 32 | 13,040 | hbm | 1.455x | 6,520.0 / 6,520.0 W | 29% | 1,075.9 | 1,565.1 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x8` | Qwen3-8B | 16 | 6,520 | hbm | 1.450x | 3,260.0 / 3,260.0 W | 26% | 1,126.9 | 1,634.1 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x7` | Qwen3-8B | 256 | 5,705 | hbm | 1.442x | 2,852.5 / 2,852.5 W | 25% | 63.5 | 91.5 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x7` | Qwen3-8B | 64 | 5,705 | hbm | 1.441x | 2,852.5 / 2,852.5 W | 25% | 253.1 | 364.7 |

The worst point's dynamic energy is kv read 95.8%, arithmetic 3.8%, operand delivery 0.4%, weight read 0.1%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | `DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 0.816345 | 3,959.8 | link_latency | `DSV4-Flash/b200_sxm-x29-tensor` | 9.028370 | 11,743.4 | link_latency | 11.06x |
| DeepSeek-V4-Flash-0731 | 2 | 46,225 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 0.460382 | 4,465.1 | link_latency | `DSV4-Flash/b200_sxm-x29-tensor` | 5.177135 | 12,027.6 | link_latency | 11.25x |
| DeepSeek-V4-Flash-0731 | 4 | 46,225 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 0.253051 | 4,802.6 | link_latency | `DSV4-Flash/b200_sxm-x29-hybrid` | 3.491156 | 15,588.9 | weight_read | 13.80x |
| DeepSeek-V4-Flash-0731 | 8 | 92,450 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 0.262137 | 9,548.5 | link_latency | `DSV4-Flash/b200_sxm-x58-tensor` | 3.524473 | 23,471.1 | link_latency | 13.45x |
| DeepSeek-V4-Flash-0731 | 16 | 138,675 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 0.219160 | 14,786.7 | link_latency | `DSV4-Flash/b200_sxm-x87-tensor` | 3.418539 | 34,442.2 | link_latency | 15.60x |
| DeepSeek-V4-Flash-0731 | 32 | 277,350 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 0.231363 | 29,261.3 | link_latency | `DSV4-Flash/b200_sxm-x173-tensor` | 4.666353 | 65,070.6 | link_latency | 20.17x |
| DeepSeek-V4-Flash-0731 | 64 | 369,800 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 0.184752 | 40,923.9 | link_latency | `DSV4-Flash/b200_sxm-x231-tensor` | 4.938935 | 85,042.9 | link_latency | 26.73x |
| DeepSeek-V4-Flash-0731 | 256 | 554,700 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.120960 | 70,339.5 | link_latency | `DSV4-Flash/b200_sxm-x347-hybrid` | 4.124001 | 139,114.9 | weight_read | 34.09x |
| DeepSeek-V4-Pro-0813 | 1 | 138,675 | `DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 2.987811 | 7,914.0 | link_latency | `DSV4-Pro/b200_sxm-x87-tensor` | 45.242201 | 33,786.5 | link_latency | 15.14x |
| DeepSeek-V4-Pro-0813 | 2 | 138,675 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3` | 1.328101 | 10,553.5 | link_latency | `DSV4-Pro/b200_sxm-x87-tensor` | 26.878953 | 34,313.3 | link_latency | 20.24x |
| DeepSeek-V4-Pro-0813 | 4 | 138,675 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3` | 1.058118 | 11,209.0 | link_latency | `DSV4-Pro/b200_sxm-x87-tensor` | 17.314194 | 35,090.3 | link_latency | 16.36x |
| DeepSeek-V4-Pro-0813 | 8 | 138,675 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3` | 0.710761 | 13,162.8 | link_latency | `DSV4-Pro/b200_sxm-x87-tensor` | 11.974175 | 36,159.7 | link_latency | 16.85x |
| DeepSeek-V4-Pro-0813 | 16 | 277,350 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 0.939123 | 33,559.1 | link_latency | `DSV4-Pro/b200_sxm-x173-tensor` | 15.246703 | 67,864.5 | link_latency | 16.24x |
| DeepSeek-V4-Pro-0813 | 32 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.987598 | 65,939.4 | link_latency | `DSV4-Pro/b200_sxm-x347-tensor` | 21.874066 | 129,944.0 | link_latency | 22.15x |
| DeepSeek-V4-Pro-0813 | 64 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.749607 | 73,683.4 | kv_read | `DSV4-Pro/b200_sxm-x347-tensor` | 18.507217 | 129,648.4 | link_latency | 24.69x |
| DeepSeek-V4-Pro-0813 | 256 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12` | 0.706923 | 107,593.2 | kv_read | `DSV4-Pro/b200_sxm-x347-hybrid` | 15.201699 | 140,364.9 | weight_read | 21.50x |
| Qwen3-8B | 1 | 46,225 | `Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 0.621238 | 4,015.9 | link_latency | `Qwen3-8B/b200_sxm-x29-hybrid` | 3.084395 | 23,025.0 | weight_read | 4.96x |
| Qwen3-8B | 2 | 92,450 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 0.895804 | 9,676.0 | link_latency | `Qwen3-8B/b200_sxm-x58-hybrid` | 3.106690 | 45,635.6 | weight_read | 3.47x |
| Qwen3-8B | 4 | 138,675 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 0.756054 | 14,985.3 | link_latency | `Qwen3-8B/b200_sxm-x87-hybrid` | 3.170363 | 66,783.2 | weight_read | 4.19x |
| Qwen3-8B | 8 | 277,350 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 0.802850 | 29,594.0 | link_latency | `Qwen3-8B/b200_sxm-x173-hybrid` | 3.233627 | 129,776.2 | weight_read | 4.03x |
| Qwen3-8B | 16 | 92,095 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x113-romfill` | 0.293229 | 18,430.7 | link_latency | `Qwen3-8B/b200_sxm-x58-hybrid` | 1.655644 | 46,215.5 | weight_read | 5.65x |
| Qwen3-8B | 32 | 138,550 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x170-romfill` | 0.267720 | 29,964.6 | link_latency | `Qwen3-8B/b200_sxm-x87-hybrid` | 1.225409 | 68,361.8 | weight_read | 4.58x |
| Qwen3-8B | 64 | 185,005 | `Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x227-romfill` | 0.237610 | 45,464.6 | link_latency | `Qwen3-8B/b200_sxm-x116-hybrid` | 0.905091 | 91,933.1 | weight_read | 3.81x |
| Qwen3-8B | 256 | 277,100 | `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x340-romfill` | 0.173904 | 138,550.0 | thermal | `Qwen3-8B/b200_sxm-x173-hybrid` | 0.471247 | 141,058.9 | link_latency | 2.71x |

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
| Qwen3-8B | 1 | 46,225 | 48,855.6 | wafer-pipeline | 6,464.4 | wafer-tensor | 7.56x | 7,406.7 | pipeline | 1,866.3 | hybrid | 3.97x | 6.60x | 3.46x | 0.53x |
| Qwen3-8B | 2 | 92,450 | 46,513.8 | wafer-pipeline | 5,845.1 | wafer-hybrid | 7.96x | 10,054.5 | pipeline | 1,836.2 | hybrid | 5.48x | 4.63x | 3.18x | 0.69x |
| Qwen3-8B | 3 | 138,675 | 46,513.8 | wafer-pipeline | 5,363.6 | wafer-hybrid | 8.67x | 11,830.5 | pipeline | 1,915.0 | hybrid | 6.18x | 3.93x | 2.80x | 0.71x |
| Qwen3-8B | 4 | 184,900 | 50,339.1 | wafer-pipeline | 5,121.2 | wafer-hybrid | 9.83x | 12,976.6 | pipeline | 1,892.4 | tensor | 6.86x | 3.88x | 2.71x | 0.70x |
| Qwen3-8B | 6 | 277,350 | 58,910.9 | wafer-pipeline | 4,869.1 | wafer-hybrid | 12.10x | 14,350.7 | pipeline | 1,915.6 | tensor | 7.49x | 4.11x | 2.54x | 0.62x |
| Qwen3-8B | 8 | 369,800 | 64,393.4 | wafer-pipeline | 4,640.7 | wafer-hybrid | 13.88x | 15,171.6 | pipeline | 1,927.7 | tensor | 7.87x | 4.24x | 2.41x | 0.57x |
| Qwen3-8B | 12 | 554,700 | 71,001.1 | wafer-pipeline | 4,242.6 | wafer-hybrid | 16.74x | 16,089.4 | pipeline | 1,939.8 | tensor | 8.29x | 4.41x | 2.19x | 0.50x |
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 21,805.7 | wafer-pipeline | 4,850.6 | wafer-tensor | 4.50x | 4,623.3 | pipeline | 1,300.7 | tensor | 3.55x | 4.72x | 3.73x | 0.79x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 30,080.1 | wafer-pipeline | 4,668.5 | wafer-hybrid | 6.44x | 5,048.4 | pipeline | 1,356.9 | tensor | 3.72x | 5.96x | 3.44x | 0.58x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 35,679.1 | wafer-pipeline | 4,561.9 | wafer-hybrid | 7.82x | 5,409.9 | pipeline | 1,379.0 | tensor | 3.92x | 6.60x | 3.31x | 0.50x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 39,330.9 | wafer-pipeline | 4,459.6 | wafer-hybrid | 8.82x | 5,617.2 | pipeline | 1,390.1 | tensor | 4.04x | 7.00x | 3.21x | 0.46x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 43,807.7 | wafer-pipeline | 4,267.6 | wafer-hybrid | 10.27x | 5,843.4 | pipeline | 1,401.8 | tensor | 4.17x | 7.50x | 3.04x | 0.41x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 46,448.0 | wafer-pipeline | 4,091.3 | wafer-hybrid | 11.35x | 5,968.4 | pipeline | 1,407.9 | tensor | 4.24x | 7.78x | 2.91x | 0.37x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 49,424.4 | wafer-pipeline | 3,778.9 | wafer-hybrid | 13.08x | 6,100.0 | pipeline | 1,414.1 | tensor | 4.31x | 8.10x | 2.67x | 0.33x |
| DeepSeek-V4-Pro-0813 | 3 | 138,675 | 14,625.7 | wafer-pipeline | 2,648.8 | wafer-hybrid | 5.52x | 1,882.9 | pipeline | 746.8 | tensor | 2.52x | 7.77x | 3.55x | 0.46x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 14,625.7 | wafer-pipeline | 2,375.7 | wafer-hybrid | 6.16x | 1,975.6 | pipeline | 759.5 | tensor | 2.60x | 7.40x | 3.13x | 0.42x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 17,217.2 | wafer-pipeline | 2,242.4 | wafer-hybrid | 7.68x | 2,079.1 | pipeline | 773.0 | tensor | 2.69x | 8.28x | 2.90x | 0.35x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 19,599.7 | wafer-pipeline | 2,194.6 | wafer-hybrid | 8.93x | 2,137.3 | pipeline | 780.2 | tensor | 2.74x | 9.17x | 2.81x | 0.31x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 22,726.9 | wafer-pipeline | 2,102.7 | wafer-hybrid | 10.81x | 2,199.4 | pipeline | 787.5 | tensor | 2.79x | 10.33x | 2.67x | 0.26x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.26x to 0.79x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 6,464.4 | 6,464.4 | link_latency | Qwen3-8B/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 181.10 | 1,866.3 | 7,465.0 | weight_read | 3.46x | 0.87x | 17.15x | 3.46x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4 | 3,260 | 3,911.3 | 3,911.3 | link_latency | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 173.78 | 693.6 | 693.6 | weight_read | 5.64x | 5.64x | 10.38x | 5.64x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 5,400.8 | 10,801.5 | link_latency | Qwen3-8B/b200_sxm-x58-hybrid | 92,800 | 1.00x | hybrid | 189.88 | 1,836.2 | 14,689.5 | weight_read | 2.94x | 0.74x | 14.33x | 2.94x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4 | 3,260 | 3,014.6 | 6,029.2 | link_latency | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 174.77 | 651.0 | 1,302.1 | weight_read | 4.63x | 4.63x | 8.00x | 4.63x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 5,121.2 | 20,484.6 | link_latency | Qwen3-8B/b200_sxm-x116-hybrid | 185,600 | 1.00x | hybrid | 205.23 | 1,858.0 | 27,869.6 | weight_read | 2.76x | 0.74x | 13.58x | 2.76x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | 3,260 | 2,415.6 | 9,662.4 | thermal | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 176.73 | 579.9 | 2,319.7 | weight_read | 4.17x | 4.17x | 6.90x | 4.17x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 4,640.7 | 37,125.2 | link_latency | Qwen3-8B/b200_sxm-x231-hybrid | 369,600 | 1.00x | hybrid | 235.95 | 1,787.5 | 51,838.8 | weight_read | 2.60x | 0.72x | 12.31x | 2.60x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4 | 3,260 | 1,245.2 | 9,961.7 | thermal | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 180.66 | 475.9 | 3,807.4 | weight_read | 2.62x | 2.62x | 4.06x | 2.62x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,040.9 | 64,654.9 | link_latency | Qwen3-8B/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 251.30 | 1,730.2 | 76,129.6 | weight_read | 2.34x | 0.85x | 10.72x | 2.41x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4 | 3,260 | 624.0 | 9,983.7 | thermal | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 188.53 | 350.3 | 5,604.6 | kv_read | 1.78x | 1.78x | 2.54x | 1.78x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x227-romfill | 185,005 | 3,503.0 | 112,095.8 | link_latency | Qwen3-8B/b200_sxm-x116-hybrid | 185,600 | 1.00x | hybrid | 209.78 | 1,754.1 | 56,131.2 | weight_read | 2.00x | 2.00x | 9.29x | 2.00x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4 | 3,260 | 312.3 | 9,994.8 | thermal | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 204.26 | 223.4 | 7,149.8 | thermal | 1.40x | 1.40x | 1.78x | 1.40x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x340-romfill | 277,100 | 3,145.5 | 201,312.0 | link_latency | Qwen3-8B/b200_sxm-x173-hybrid | 276,800 | 1.00x | hybrid | 230.44 | 1,657.6 | 106,085.4 | weight_read | 1.90x | 1.90x | 8.34x | 1.90x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4 | 3,260 | 156.3 | 10,000.4 | thermal | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 235.71 | 129.4 | 8,283.1 | thermal | 1.21x | 1.21x | 1.40x | 1.21x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 2,343.2 | 796,701.8 | thermal | Qwen3-8B/b200_sxm-x173-hybrid | 276,800 | 1.00x | hybrid | 275.48 | 1,169.3 | 299,331.0 | link_latency | 2.00x | 2.66x | 6.44x | 2.00x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4 | 3,260 | 39.1 | 10,004.5 | thermal | Qwen3-8B/b200_sxm-x2-pipeline | 3,200 | 1.02x | pipeline | 2.37 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 4,850.6 | 4,850.6 | link_latency | DSV4-Flash/b200_sxm-x29-tensor | 46,400 | 1.00x | tensor | 589.32 | 1,300.7 | 1,300.7 | link_latency | 3.73x | 3.73x | 23.74x | 3.73x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x29 | 23,635 | 2,450.3 | 2,450.3 | link_latency | DSV4-Flash/b200_sxm-x15-hybrid | 24,000 | 0.98x | hybrid | 210.65 | 1,465.1 | 2,930.1 | weight_read | 1.67x | 0.84x | 8.52x | 1.67x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,849.3 | 9,698.6 | link_latency | DSV4-Flash/b200_sxm-x29-tensor | 46,400 | 1.00x | tensor | 623.08 | 1,161.6 | 2,323.2 | link_latency | 4.17x | 4.17x | 23.74x | 4.17x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x31 | 25,265 | 2,569.2 | 10,276.6 | link_latency | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 210.65 | 1,499.3 | 2,998.5 | weight_read | 1.71x | 3.43x | 9.21x | 1.71x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,744.7 | 18,978.9 | link_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 215.04 | 1,116.3 | 4,465.3 | weight_read | 4.25x | 4.25x | 23.23x | 4.25x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x31 | 25,265 | 2,569.2 | 10,276.6 | link_latency | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 212.87 | 1,215.6 | 4,862.4 | weight_read | 2.11x | 2.11x | 9.21x | 2.11x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,553.2 | 36,425.7 | link_latency | DSV4-Flash/b200_sxm-x58-tensor | 92,800 | 1.00x | tensor | 867.89 | 832.4 | 6,659.5 | link_latency | 5.47x | 5.47x | 34.64x | 5.47x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x31 | 25,265 | 1,806.4 | 14,451.3 | compute | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 217.30 | 932.2 | 7,457.3 | weight_read | 1.94x | 1.94x | 6.47x | 1.94x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,346.7 | 69,546.4 | link_latency | DSV4-Flash/b200_sxm-x116-tensor | 185,600 | 1.00x | tensor | 1,219.68 | 639.9 | 10,239.2 | link_latency | 6.79x | 6.79x | 55.72x | 6.79x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x31 | 25,265 | 1,133.4 | 18,134.8 | compute | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 226.18 | 674.4 | 10,790.8 | weight_read | 1.68x | 1.68x | 4.06x | 1.68x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,985.1 | 127,522.6 | link_latency | DSV4-Flash/b200_sxm-x231-tensor | 369,600 | 1.00x | tensor | 1,927.33 | 440.6 | 14,098.5 | link_latency | 9.05x | 9.05x | 91.82x | 9.05x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x31 | 25,265 | 742.9 | 23,772.8 | compute | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 243.93 | 468.3 | 14,984.9 | weight_read | 1.59x | 1.59x | 3.57x | 1.59x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,511.7 | 224,746.4 | link_latency | DSV4-Flash/b200_sxm-x347-tensor | 555,200 | 1.00x | tensor | 3,330.91 | 271.2 | 17,354.7 | link_latency | 12.95x | 12.95x | 117.02x | 12.95x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x31 | 25,265 | 378.6 | 24,230.8 | compute | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 279.43 | 323.9 | 20,729.8 | weight_read | 1.17x | 1.17x | 2.57x | 1.17x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,271.5 | 581,509.9 | link_latency | DSV4-Flash/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 343.65 | 131.8 | 33,733.0 | weight_read | 17.24x | 17.24x | 75.69x | 17.25x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x31 | 25,265 | 96.0 | 24,586.0 | compute | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 492.42 | 185.8 | 47,567.7 | weight_read | 0.52x | 0.52x | 1.45x | 0.52x |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x3 | 138,675 | 2,648.8 | 2,648.8 | link_latency | DSV4-Pro/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 888.62 | 746.8 | 746.8 | link_latency | 3.55x | 3.55x | 100.00x | 3.55x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x155 | 126,325 | 1,036.7 | 1,036.7 | link_latency | DSV4-Pro/b200_sxm-x79-tensor | 126,400 | 1.00x | tensor | 887.67 | 741.8 | 741.8 | link_latency | 1.40x | 1.40x | 36.37x | 1.40x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,648.8 | 7,946.3 | link_latency | DSV4-Pro/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 989.12 | 638.3 | 1,276.6 | link_latency | 4.15x | 6.22x | 100.00x | 4.15x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x163 | 132,845 | 885.8 | 1,771.7 | link_latency | DSV4-Pro/b200_sxm-x83-tensor | 132,800 | 1.00x | tensor | 989.12 | 634.8 | 1,269.7 | link_latency | 1.40x | 1.40x | 32.26x | 1.40x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,648.3 | 10,593.3 | link_latency | DSV4-Pro/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 1,190.12 | 506.7 | 2,026.7 | link_latency | 5.23x | 5.23x | 99.99x | 5.23x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x163 | 132,845 | 688.7 | 2,754.8 | link_latency | DSV4-Pro/b200_sxm-x83-tensor | 132,800 | 1.00x | tensor | 1,190.12 | 503.8 | 2,015.3 | link_latency | 1.37x | 1.37x | 25.08x | 1.37x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,374.1 | 18,992.9 | link_latency | DSV4-Pro/b200_sxm-x116-tensor | 185,600 | 1.00x | tensor | 1,612.48 | 390.3 | 3,122.8 | link_latency | 6.08x | 6.08x | 112.57x | 6.08x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x163 | 132,845 | 645.6 | 13,556.7 | compute | DSV4-Pro/b200_sxm-x83-tensor | 132,800 | 1.00x | tensor | 1,592.13 | 374.7 | 2,997.7 | link_latency | 1.72x | 4.52x | 23.51x | 1.72x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 2,233.4 | 35,734.5 | link_latency | DSV4-Pro/b200_sxm-x173-tensor | 276,800 | 1.00x | tensor | 2,472.45 | 278.2 | 4,451.1 | link_latency | 8.03x | 8.03x | 148.09x | 8.03x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x163 | 132,845 | 645.6 | 13,556.7 | compute | DSV4-Pro/b200_sxm-x83-tensor | 132,800 | 1.00x | tensor | 2,396.13 | 256.5 | 4,103.6 | link_latency | 2.52x | 3.30x | 23.51x | 2.52x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,086.5 | 66,767.4 | link_latency | DSV4-Pro/b200_sxm-x347-tensor | 555,200 | 1.00x | tensor | 4,233.10 | 185.6 | 5,940.6 | link_latency | 11.24x | 11.24x | 258.24x | 11.24x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x163 | 132,845 | 459.4 | 14,701.8 | compute | DSV4-Pro/b200_sxm-x83-tensor | 132,800 | 1.00x | tensor | 4,004.15 | 163.4 | 5,229.3 | link_latency | 2.81x | 2.81x | 16.73x | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,535.9 | 98,296.0 | kv_read | DSV4-Pro/b200_sxm-x347-tensor | 555,200 | 1.00x | tensor | 7,678.09 | 109.5 | 7,005.3 | link_latency | 14.03x | 14.03x | 190.09x | 14.03x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x163 | 132,845 | 249.9 | 15,991.2 | compute | DSV4-Pro/b200_sxm-x83-tensor | 132,800 | 1.00x | tensor | 7,220.17 | 98.7 | 6,318.3 | link_latency | 2.53x | 2.53x | 9.10x | 2.53x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 594.5 | 152,199.3 | kv_read | DSV4-Pro/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 481.50 | 36.1 | 9,233.5 | weight_read | 16.48x | 16.48x | 73.58x | 16.48x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x163 | 132,845 | 68.6 | 17,567.3 | compute | DSV4-Pro/b200_sxm-x83-hybrid | 132,800 | 1.00x | hybrid | 498.55 | 49.5 | 12,662.3 | weight_read | 1.39x | 1.39x | 3.97x | 1.39x |

## The headline is a band, and each side's share of it is reported apart

Every hop latency in this model states a range, and the ratio moves inside it.
This table re-runs the whole study at both ends of those ranges three ways:
the **wafer fabric** alone (`on_wafer_n5`, `inter_wafer`), which no GPU design touches; the
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
| DeepSeek-V4-Flash-0731 | 23,635 | 1.67x | 1.67x → 1.67x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 24,450 | 1.79x | 1.79x → 1.79x | 2.03x → 1.22x | 2.03x → 1.22x | 1.7x |
| DeepSeek-V4-Flash-0731 | 25,265 | 1.71x | 1.71x → 1.71x | 1.92x → 1.20x | 1.92x → 1.20x | 1.6x |
| DeepSeek-V4-Flash-0731 | 26,080 | 1.75x | 1.75x → 1.75x | — | — | 1.0x |
| DeepSeek-V4-Flash-0731 | 28,525 | 1.92x | 1.92x → 1.92x | 2.09x → 1.31x | 2.09x → 1.31x | 1.6x |
| DeepSeek-V4-Flash-0731 | 30,155 | 1.90x | 1.90x → 1.90x | 2.07x → 1.30x | 2.07x → 1.30x | 1.6x |
| DeepSeek-V4-Flash-0731 | 34,230 | 1.72x | 1.72x → 1.72x | 1.82x → 1.22x | 1.82x → 1.22x | 1.5x |
| DeepSeek-V4-Flash-0731 | 35,860 | 1.71x | 1.71x → 1.71x | 1.81x → 1.21x | 1.81x → 1.21x | 1.5x |
| DeepSeek-V4-Flash-0731 | 45,640 | 1.68x | 1.68x → 1.68x | 1.79x → 1.29x | 1.79x → 1.29x | 1.4x |
| DeepSeek-V4-Flash-0731 | 46,225 | 3.73x | 5.49x → 2.07x | 3.20x → 8.22x | 4.72x → 4.56x | 2.7x |
| DeepSeek-V4-Flash-0731 | 46,455 | 1.58x | 1.58x → 1.58x | 1.66x → 1.24x | 1.66x → 1.24x | 1.3x |
| DeepSeek-V4-Flash-0731 | 47,270 | 1.54x | 1.54x → 1.54x | 1.60x → 1.22x | 1.60x → 1.22x | 1.3x |
| DeepSeek-V4-Flash-0731 | 68,460 | 1.58x | 1.58x → 1.58x | 1.65x → 1.37x | 1.65x → 1.37x | 1.2x |
| DeepSeek-V4-Flash-0731 | 70,905 | 1.55x | 1.55x → 1.55x | 1.61x → 1.35x | 1.61x → 1.35x | 1.2x |
| DeepSeek-V4-Flash-0731 | 91,280 | 1.57x | 1.57x → 1.57x | 1.64x → 1.47x | 1.64x → 1.47x | 1.1x |
| DeepSeek-V4-Flash-0731 | 92,095 | 1.51x | 1.51x → 1.51x | 1.58x → 1.43x | 1.58x → 1.43x | 1.1x |
| DeepSeek-V4-Flash-0731 | 92,450 | 3.44x | 5.12x → 1.92x | 2.93x → 10.06x | 4.37x → 5.60x | 3.4x |
| DeepSeek-V4-Flash-0731 | 94,540 | 1.48x | 1.48x → 1.48x | 1.53x → 1.42x | 1.53x → 1.42x | 1.1x |
| DeepSeek-V4-Flash-0731 | 138,550 | 1.46x | 1.46x → 1.46x | 1.52x → 1.49x | 1.52x → 1.49x | 1.0x |
| DeepSeek-V4-Flash-0731 | 138,675 | 3.31x | 5.00x → 1.84x | 2.81x → 11.25x | 4.25x → 6.25x | 4.0x |
| DeepSeek-V4-Flash-0731 | 184,900 | 3.21x | 4.93x → 1.78x | 2.72x → 13.02x | 4.18x → 7.21x | 4.8x |
| DeepSeek-V4-Flash-0731 | 185,005 | 1.42x | 1.42x → 1.42x | 1.46x → 1.62x | 1.46x → 1.62x | 1.1x |
| DeepSeek-V4-Flash-0731 | 277,100 | 1.33x | 1.33x → 1.33x | 1.36x → 1.77x | 1.36x → 1.77x | 1.3x |
| DeepSeek-V4-Flash-0731 | 277,350 | 3.04x | 4.82x → 1.68x | 2.58x → 15.76x | 4.09x → 8.69x | 6.1x |
| DeepSeek-V4-Flash-0731 | 369,800 | 2.91x | 4.73x → 1.60x | 2.46x → 18.27x | 4.01x → 10.03x | 7.4x |
| DeepSeek-V4-Flash-0731 | 554,700 | 2.67x | 4.58x → 1.46x | 2.26x → 18.45x | 3.88x → 10.06x | 8.2x |
| DeepSeek-V4-Pro-0813 | 126,325 | 1.40x | 1.40x → 1.40x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 129,585 | 1.42x | 1.42x → 1.42x | 1.50x → 2.52x | 1.50x → 2.52x | 1.7x |
| DeepSeek-V4-Pro-0813 | 132,845 | 1.39x | 1.39x → 1.39x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 136,105 | 1.41x | 1.41x → 1.41x | 1.49x → 2.42x | 1.49x → 2.42x | 1.6x |
| DeepSeek-V4-Pro-0813 | 138,550 | 1.41x | 1.41x → 1.41x | 1.49x → 2.37x | 1.49x → 2.37x | 1.6x |
| DeepSeek-V4-Pro-0813 | 138,675 | 3.55x | 4.86x → 2.15x | 3.14x → 16.82x | 4.30x → 10.20x | 5.4x |
| DeepSeek-V4-Pro-0813 | 149,960 | 1.40x | 1.40x → 1.40x | 1.48x → 2.45x | 1.48x → 2.45x | 1.7x |
| DeepSeek-V4-Pro-0813 | 157,295 | 1.40x | 1.40x → 1.40x | 1.48x → 2.49x | 1.48x → 2.49x | 1.7x |
| DeepSeek-V4-Pro-0813 | 180,115 | 1.39x | 1.39x → 1.39x | 1.46x → 2.38x | 1.46x → 2.38x | 1.6x |
| DeepSeek-V4-Pro-0813 | 184,900 | 3.13x | 4.18x → 1.96x | 2.76x → 17.20x | 3.69x → 10.79x | 6.2x |
| DeepSeek-V4-Pro-0813 | 185,005 | 1.39x | 1.39x → 1.39x | 1.46x → 2.34x | 1.46x → 2.34x | 1.6x |
| DeepSeek-V4-Pro-0813 | 188,265 | 1.38x | 1.38x → 1.38x | 1.46x → 2.34x | 1.46x → 2.34x | 1.6x |
| DeepSeek-V4-Pro-0813 | 239,610 | 1.38x | 1.38x → 1.38x | 1.45x → 2.14x | 1.45x → 2.14x | 1.5x |
| DeepSeek-V4-Pro-0813 | 251,020 | 1.37x | 1.37x → 1.37x | 1.44x → 2.06x | 1.44x → 2.06x | 1.4x |
| DeepSeek-V4-Pro-0813 | 277,100 | 1.37x | 1.37x → 1.37x | 1.45x → 2.06x | 1.45x → 2.06x | 1.4x |
| DeepSeek-V4-Pro-0813 | 277,350 | 2.90x | 3.90x → 1.83x | 2.56x → 16.18x | 3.43x → 10.22x | 6.3x |
| DeepSeek-V4-Pro-0813 | 369,800 | 2.81x | 3.84x → 1.77x | 2.48x → 15.81x | 3.38x → 9.93x | 6.4x |
| DeepSeek-V4-Pro-0813 | 554,700 | 2.67x | 3.76x → 1.66x | 2.35x → 15.12x | 3.31x → 9.40x | 6.4x |
| Qwen3-8B | 3,260 | 5.64x | 5.64x → 5.64x | 7.46x → 4.98x | 7.46x → 4.98x | 1.5x |
| Qwen3-8B | 4,075 | 5.05x | 5.05x → 5.05x | 6.45x → 7.47x | 6.45x → 7.47x | 1.2x |
| Qwen3-8B | 4,890 | 5.10x | 5.10x → 5.10x | 6.76x → 7.40x | 6.76x → 7.40x | 1.1x |
| Qwen3-8B | 5,705 | 4.07x | 4.07x → 4.07x | — | — | 1.0x |
| Qwen3-8B | 6,520 | 4.08x | 4.08x → 4.08x | 5.59x → 6.25x | 5.59x → 6.25x | 1.1x |
| Qwen3-8B | 9,780 | 2.99x | 2.99x → 2.99x | 3.75x → 4.62x | 3.75x → 4.62x | 1.2x |
| Qwen3-8B | 13,040 | 2.43x | 2.43x → 2.43x | 3.18x → 3.93x | 3.18x → 3.93x | 1.2x |
| Qwen3-8B | 46,225 | 3.46x | 5.40x → 1.83x | 3.00x → 7.85x | 4.67x → 4.14x | 3.0x |
| Qwen3-8B | 46,455 | 2.25x | 2.25x → 2.25x | 2.80x → 2.15x | 2.80x → 2.15x | 1.3x |
| Qwen3-8B | 92,095 | 2.16x | 2.16x → 2.16x | 2.57x → 2.31x | 2.57x → 2.31x | 1.1x |
| Qwen3-8B | 92,450 | 3.18x | 4.88x → 1.73x | 2.67x → 7.62x | 4.10x → 4.14x | 2.9x |
| Qwen3-8B | 138,550 | 1.96x | 1.96x → 1.96x | 2.32x → 2.38x | 2.32x → 2.38x | 1.0x |
| Qwen3-8B | 138,675 | 2.80x | 4.25x → 1.56x | 2.38x → 7.19x | 3.61x → 4.00x | 3.0x |
| Qwen3-8B | 184,900 | 2.71x | 4.13x → 1.51x | 2.24x → 7.36x | 3.42x → 4.12x | 3.3x |
| Qwen3-8B | 185,005 | 1.88x | 1.88x → 1.88x | 2.13x → 2.55x | 2.13x → 2.55x | 1.2x |
| Qwen3-8B | 277,100 | 1.76x | 1.76x → 1.76x | 1.97x → 2.81x | 1.97x → 2.81x | 1.4x |
| Qwen3-8B | 277,350 | 2.54x | 4.02x → 1.41x | 2.10x → 7.73x | 3.32x → 4.30x | 3.7x |
| Qwen3-8B | 369,800 | 2.41x | 3.93x → 1.33x | 1.99x → 8.06x | 3.24x → 4.47x | 4.1x |
| Qwen3-8B | 554,700 | 2.19x | 3.78x → 1.20x | 1.80x → 8.04x | 3.12x → 4.42x | 4.5x |

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
| `band_low` | 0.5000 | yes | 11.53 us | 1.78x | 3.48x | 4.96x |
| `stated` | 1.0000 | yes | 6.82 us | 1.79x | 3.55x | 5.05x |
| `band_high` | 2.0000 | yes | 4.46 us | 1.80x | 3.58x | 5.10x |
| `asap7_reduction_s8_g2` | 1.2874 | yes | 5.77 us | 1.80x | 3.56x | 5.07x |
| `asap7_add_bf16_sram_engine` | 0.2391 | **no** | 21.83 us | 1.75x | 3.35x | 4.77x |
| `asap7_matmul_bf16_sram_engine` | 0.0580 | **no** | 83.47 us | 1.61x | 2.78x | 3.94x |

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
| `band_low` | 0.1100 | yes | 28.139 MB/mm2 | 103.4 us | 1.46x | 3.11x | 5.05x |
| `stated` | 0.3300 | yes | 9.380 MB/mm2 | 34.5 us | 1.79x | 3.55x | 5.05x |
| `band_high` | 0.3300 | yes | 9.380 MB/mm2 | 34.5 us | 1.79x | 3.55x | 5.05x |
| `measured_ihp_sg13g2_130nm` | 0.1298 | yes | 23.854 MB/mm2 | 87.7 us | — | 3.11x | 5.05x |
| `measured_asap7_7nm_via_programmed` | 0.2500 | yes | 12.381 MB/mm2 | 45.5 us | — | 3.23x | 5.05x |
| `measured_asap7_7nm_shared_source_drain` | 0.1250 | yes | 24.762 MB/mm2 | 91.0 us | — | 3.11x | 5.05x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 8 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 8 | Link us at domain 72 | tok/s at 8 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 4 | 6,400 | 208.16 | 208.16 | 1,309.8 | 1,309.8 |
| DeepSeek-V4-Flash-0731 | 15 | 24,000 | 210.65 | 208.59 | 1,465.1 | 1,469.5 |
| DeepSeek-V4-Flash-0731 | 16 | 25,600 | 210.65 | 208.60 | 1,499.3 | 1,503.9 |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 585.80 | 208.62 | 1,239.1 | 2,326.5 |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 585.80 | 208.62 | 1,247.8 | 2,357.3 |
| DeepSeek-V4-Flash-0731 | 21 | 33,600 | 585.80 | 208.64 | 1,263.2 | 2,412.6 |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 585.80 | 208.64 | 1,270.0 | 2,437.6 |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 589.32 | 208.67 | 1,300.7 | 2,576.3 |
| DeepSeek-V4-Flash-0731 | 30 | 48,000 | 589.32 | 208.67 | 1,304.8 | 2,592.1 |
| DeepSeek-V4-Flash-0731 | 31 | 49,600 | 589.32 | 208.67 | 1,308.6 | 2,607.2 |
| DeepSeek-V4-Flash-0731 | 32 | 51,200 | 589.32 | 208.67 | 1,312.2 | 2,621.6 |
| DeepSeek-V4-Flash-0731 | 43 | 68,800 | 592.84 | 208.69 | 1,335.9 | 2,744.1 |
| DeepSeek-V4-Flash-0731 | 44 | 70,400 | 592.84 | 208.70 | 1,338.0 | 2,752.8 |
| DeepSeek-V4-Flash-0731 | 45 | 72,000 | 592.84 | 208.70 | 1,339.9 | 2,761.2 |
| DeepSeek-V4-Flash-0731 | 50 | 80,000 | 593.85 | 208.70 | 1,347.0 | 2,799.1 |
| DeepSeek-V4-Flash-0731 | 57 | 91,200 | 594.60 | 208.71 | 1,355.6 | 2,842.8 |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 594.60 | 208.71 | 1,356.9 | 2,848.3 |
| DeepSeek-V4-Flash-0731 | 59 | 94,400 | 594.60 | 208.71 | 1,358.1 | 2,853.7 |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 596.04 | 579.01 | 1,379.0 | 1,412.1 |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 597.07 | 579.01 | 1,390.1 | 1,425.9 |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 597.96 | 586.06 | 1,401.8 | 1,425.6 |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 598.43 | 589.58 | 1,407.9 | 1,425.7 |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 598.92 | 591.69 | 1,414.1 | 1,428.7 |
| DeepSeek-V4-Pro-0813 | 22 | 35,200 | 863.18 | 298.36 | 633.8 | 987.2 |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 871.93 | 298.43 | 664.0 | 1,072.4 |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 885.04 | 298.53 | 722.6 | 1,254.2 |
| DeepSeek-V4-Pro-0813 | 79 | 126,400 | 887.67 | 846.34 | 741.8 | 765.3 |
| DeepSeek-V4-Pro-0813 | 81 | 129,600 | 888.62 | 846.34 | 742.8 | 766.8 |
| DeepSeek-V4-Pro-0813 | 83 | 132,800 | 888.62 | 846.34 | 744.2 | 768.3 |
| DeepSeek-V4-Pro-0813 | 85 | 136,000 | 888.62 | 846.34 | 745.5 | 769.8 |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 888.62 | 846.34 | 746.8 | 771.1 |
| DeepSeek-V4-Pro-0813 | 94 | 150,400 | 889.42 | 846.34 | 750.5 | 775.5 |
| DeepSeek-V4-Pro-0813 | 98 | 156,800 | 890.09 | 846.34 | 752.2 | 777.8 |
| DeepSeek-V4-Pro-0813 | 113 | 180,800 | 891.16 | 846.34 | 758.3 | 785.0 |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 891.16 | 846.34 | 759.5 | 786.3 |
| DeepSeek-V4-Pro-0813 | 118 | 188,800 | 891.16 | 846.34 | 760.2 | 787.0 |
| DeepSeek-V4-Pro-0813 | 150 | 240,000 | 892.64 | 863.83 | 768.7 | 786.1 |
| DeepSeek-V4-Pro-0813 | 151 | 241,600 | 892.64 | 863.83 | 768.9 | 786.4 |
| DeepSeek-V4-Pro-0813 | 157 | 251,200 | 892.91 | 863.83 | 770.1 | 787.8 |
| DeepSeek-V4-Pro-0813 | 165 | 264,000 | 893.16 | 863.83 | 771.6 | 789.5 |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 893.39 | 863.83 | 773.0 | 791.0 |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 894.54 | 872.57 | 780.2 | 793.8 |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 895.78 | 877.82 | 787.5 | 798.8 |
| Qwen3-8B | 2 | 3,200 | 173.78 | 173.78 | 693.6 | 693.6 |
| Qwen3-8B | 3 | 4,800 | 174.11 | 174.11 | 978.7 | 978.7 |
| Qwen3-8B | 4 | 6,400 | 174.27 | 174.27 | 1,232.0 | 1,232.0 |
| Qwen3-8B | 6 | 9,600 | 174.44 | 174.44 | 1,662.1 | 1,662.1 |
| Qwen3-8B | 8 | 12,800 | 174.52 | 174.52 | 2,013.6 | 2,013.6 |
| Qwen3-8B | 29 | 46,400 | 181.10 | 174.70 | 1,866.3 | 1,888.8 |
| Qwen3-8B | 58 | 92,800 | 189.88 | 174.73 | 1,836.2 | 1,888.7 |
| Qwen3-8B | 87 | 139,200 | 196.46 | 176.93 | 1,915.0 | 1,989.4 |
| Qwen3-8B | 116 | 185,600 | 499.87 | 484.75 | 1,892.4 | 1,948.1 |
| Qwen3-8B | 173 | 276,800 | 500.62 | 490.65 | 1,915.6 | 1,952.9 |
| Qwen3-8B | 231 | 369,600 | 501.01 | 493.60 | 1,927.7 | 1,955.6 |
| Qwen3-8B | 347 | 555,200 | 501.43 | 495.37 | 1,939.8 | 1,962.9 |

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
| DeepSeek-V4-Flash-0731 | 4 | 6,400 | 457.1 | 1,309.8 | — | tensor | 208.16 | 27.3% | weight_read |
| DeepSeek-V4-Flash-0731 | 15 | 24,000 | 287.6 | 1,218.2 | 1,465.1 | hybrid | 210.65 | 30.9% | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | 25,600 | 279.1 | 1,229.8 | 1,499.3 | hybrid | 210.65 | 31.6% | weight_read |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 263.6 | 1,239.1 | 1,174.1 | tensor | 585.80 | 72.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 256.6 | 1,247.8 | 1,197.8 | tensor | 585.80 | 73.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 21 | 33,600 | 243.8 | 1,263.2 | 1,241.3 | tensor | 585.80 | 74.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 238.0 | 1,270.0 | 1,261.3 | tensor | 585.80 | 74.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 204.3 | 1,300.7 | 1,116.3 | tensor | 589.32 | 76.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 30 | 48,000 | 200.3 | 1,304.8 | 1,128.3 | tensor | 589.32 | 76.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 31 | 49,600 | 196.5 | 1,308.6 | 1,139.8 | tensor | 589.32 | 77.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | 51,200 | 192.9 | 1,312.2 | 1,150.8 | tensor | 589.32 | 77.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 43 | 68,800 | 160.5 | 1,335.9 | 915.9 | tensor | 592.84 | 79.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 44 | 70,400 | 158.1 | 1,338.0 | 921.8 | tensor | 592.84 | 79.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 45 | 72,000 | 155.9 | 1,339.9 | 927.5 | tensor | 592.84 | 79.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 50 | 80,000 | 145.4 | 1,347.0 | 842.4 | tensor | 593.85 | 80.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 57 | 91,200 | 133.0 | 1,355.6 | 780.3 | tensor | 594.60 | 80.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 131.5 | 1,356.9 | 783.7 | tensor | 594.60 | 80.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 59 | 94,400 | 129.9 | 1,358.1 | 786.9 | tensor | 594.60 | 80.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 97.8 | 1,379.0 | 654.9 | tensor | 596.04 | 82.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 78.0 | 1,390.1 | 526.2 | tensor | 597.07 | 83.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 55.9 | 1,401.8 | 394.7 | tensor | 597.96 | 83.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 43.4 | 1,407.9 | 315.8 | tensor | 598.43 | 84.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 30.0 | 1,414.1 | 220.8 | tensor | 598.92 | 84.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 22 | 35,200 | 65.0 | 633.8 | 414.7 | tensor | 863.18 | 54.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 55.8 | 664.0 | 358.6 | tensor | 871.93 | 57.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 35.7 | 722.6 | 239.2 | tensor | 885.04 | 64.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 79 | 126,400 | 28.5 | 741.8 | 209.9 | tensor | 887.67 | 65.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 81 | 129,600 | 28.0 | 742.8 | 193.1 | tensor | 888.62 | 66.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 83 | 132,800 | 27.5 | 744.2 | 194.1 | tensor | 888.62 | 66.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 85 | 136,000 | 27.0 | 745.5 | 195.1 | tensor | 888.62 | 66.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 26.5 | 746.8 | 196.1 | tensor | 888.62 | 66.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 94 | 150,400 | 24.9 | 750.5 | 183.6 | tensor | 889.42 | 66.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 98 | 156,800 | 24.1 | 752.2 | 171.7 | tensor | 890.09 | 67.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 113 | 180,800 | 21.5 | 758.3 | 153.9 | tensor | 891.16 | 67.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 21.1 | 759.5 | 154.6 | tensor | 891.16 | 67.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 118 | 188,800 | 20.8 | 760.2 | 155.1 | tensor | 891.16 | 67.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 150 | 240,000 | 17.0 | 768.7 | 128.5 | tensor | 892.64 | 68.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 151 | 241,600 | 16.9 | 768.9 | 128.7 | tensor | 892.64 | 68.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 157 | 251,200 | 16.4 | 770.1 | 123.2 | tensor | 892.91 | 68.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 165 | 264,000 | 15.7 | 771.6 | 118.3 | tensor | 893.16 | 68.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 15.1 | 773.0 | 113.8 | tensor | 893.39 | 69.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 11.7 | 780.2 | 90.1 | tensor | 894.54 | 69.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 8.1 | 787.5 | 62.1 | tensor | 895.78 | 70.5% | link_latency |
| Qwen3-8B | 2 | 3,200 | 377.0 | 693.6 | — | tensor | 173.78 | 12.1% | weight_read |
| Qwen3-8B | 3 | 4,800 | 377.0 | 978.7 | — | tensor | 174.11 | 17.0% | weight_read |
| Qwen3-8B | 4 | 6,400 | 377.0 | 1,232.0 | — | tensor | 174.27 | 21.5% | weight_read |
| Qwen3-8B | 6 | 9,600 | 377.0 | 1,662.1 | — | tensor | 174.44 | 29.0% | weight_read |
| Qwen3-8B | 8 | 12,800 | 377.0 | 2,013.6 | — | tensor | 174.52 | 35.1% | weight_read |
| Qwen3-8B | 29 | 46,400 | 377.0 | 1,703.1 | 1,866.3 | hybrid | 181.10 | 33.8% | weight_read |
| Qwen3-8B | 58 | 92,800 | 377.0 | 1,824.4 | 1,836.2 | hybrid | 189.88 | 34.9% | weight_read |
| Qwen3-8B | 87 | 139,200 | 377.0 | 1,869.8 | 1,915.0 | hybrid | 196.46 | 37.6% | weight_read |
| Qwen3-8B | 116 | 185,600 | 377.0 | 1,892.4 | 1,858.0 | tensor | 499.87 | 94.6% | link_latency |
| Qwen3-8B | 173 | 276,800 | 377.0 | 1,915.6 | 1,824.2 | tensor | 500.62 | 95.9% | link_latency |
| Qwen3-8B | 231 | 369,600 | 377.0 | 1,927.7 | 1,787.5 | tensor | 501.01 | 96.6% | link_latency |
| Qwen3-8B | 347 | 555,200 | 377.0 | 1,939.8 | 1,730.2 | tensor | 501.43 | 97.3% | link_latency |

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
| Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x5 | Qwen3-8B | 5 | pipeline | nvlink5 | infiniband_ndr | 4 | 4.84 us | 20,676.5 tok/s | 206,765.0 tok/s | 4 x point_to_point span 2 on nvlink5 (traversals 1.0) = 4.84 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer_n5 | inter_wafer | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x5 | Qwen3-8B | 5 | tensor | nvlink5 | infiniband_ndr | 72 | 174.37 us | 573.5 tok/s | 5,734.8 tok/s | 72 x all_reduce span 5 on nvlink5 (traversals 2.0) = 174.37 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer_n5 | inter_wafer | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | Qwen3-8B | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 3.63 us | 27,568.7 tok/s | 275,686.6 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.63 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer_n5 | inter_wafer | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x7 | Qwen3-8B | 7 | tensor | nvlink5 | infiniband_ndr | 72 | 174.49 us | 573.1 tok/s | 5,731.1 tok/s | 72 x all_reduce span 7 on nvlink5 (traversals 2.0) = 174.49 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer_n5 | inter_wafer | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us |
| Qwen3-8B/b200_sxm-x2-pipeline | Qwen3-8B | 2 | pipeline | nvlink5 | infiniband_ndr | 1 | 1.21 us | 82,706.0 tok/s | 827,059.9 tok/s | 1 x point_to_point span 2 on nvlink5 (traversals 1.0) = 1.21 us |
| Qwen3-8B/b200_sxm-x2-tensor | Qwen3-8B | 2 | tensor | nvlink5 | infiniband_ndr | 72 | 173.78 us | 575.4 tok/s | 5,754.3 tok/s | 72 x all_reduce span 2 on nvlink5 (traversals 2.0) = 173.78 us |
| Qwen3-8B/b200_sxm-x3-pipeline | Qwen3-8B | 3 | pipeline | nvlink5 | infiniband_ndr | 2 | 2.42 us | 41,353.0 tok/s | 413,530.0 tok/s | 2 x point_to_point span 2 on nvlink5 (traversals 1.0) = 2.42 us |
| Qwen3-8B/b200_sxm-x3-tensor | Qwen3-8B | 3 | tensor | nvlink5 | infiniband_ndr | 72 | 174.11 us | 574.3 tok/s | 5,743.5 tok/s | 72 x all_reduce span 3 on nvlink5 (traversals 2.0) = 174.11 us |
| Qwen3-8B/b200_sxm-x4-pipeline | Qwen3-8B | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 3.63 us | 27,568.7 tok/s | 275,686.6 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.63 us |
| Qwen3-8B/b200_sxm-x4-tensor | Qwen3-8B | 4 | tensor | nvlink5 | infiniband_ndr | 72 | 174.27 us | 573.8 tok/s | 5,738.1 tok/s | 72 x all_reduce span 4 on nvlink5 (traversals 2.0) = 174.27 us |
| Qwen3-8B/b200_sxm-x6-pipeline | Qwen3-8B | 6 | pipeline | nvlink5 | infiniband_ndr | 5 | 6.05 us | 16,541.2 tok/s | 165,412.0 tok/s | 5 x point_to_point span 2 on nvlink5 (traversals 1.0) = 6.05 us |
| Qwen3-8B/b200_sxm-x6-tensor | Qwen3-8B | 6 | tensor | nvlink5 | infiniband_ndr | 72 | 174.44 us | 573.3 tok/s | 5,732.7 tok/s | 72 x all_reduce span 6 on nvlink5 (traversals 2.0) = 174.44 us |
| Qwen3-8B/b200_sxm-x8-pipeline | Qwen3-8B | 8 | pipeline | nvlink5 | infiniband_ndr | 7 | 8.46 us | 11,815.1 tok/s | 118,151.4 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.46 us |
| Qwen3-8B/b200_sxm-x8-tensor | Qwen3-8B | 8 | tensor | nvlink5 | infiniband_ndr | 72 | 174.52 us | 573.0 tok/s | 5,730.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us |
| Qwen3-8B/b200_sxm-x29-pipeline | Qwen3-8B | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x29-tensor | Qwen3-8B | 29 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x29-hybrid | Qwen3-8B | 29 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x58-pipeline | Qwen3-8B | 58 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x58-tensor | Qwen3-8B | 58 | tensor | nvlink5 | infiniband_ndr | 144 | 497.81 us | 200.9 tok/s | 2,008.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 323.29 us |
| Qwen3-8B/b200_sxm-x58-hybrid | Qwen3-8B | 58 | hybrid | nvlink5 | infiniband_ndr | 79 | 189.88 us | 526.7 tok/s | 5,266.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| Qwen3-8B/b200_sxm-x87-pipeline | Qwen3-8B | 87 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x87-tensor | Qwen3-8B | 87 | tensor | nvlink5 | infiniband_ndr | 144 | 499.01 us | 200.4 tok/s | 2,004.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 324.49 us |
| Qwen3-8B/b200_sxm-x87-hybrid | Qwen3-8B | 87 | hybrid | nvlink5 | infiniband_ndr | 82 | 196.46 us | 509.0 tok/s | 5,090.1 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| Qwen3-8B/b200_sxm-x116-pipeline | Qwen3-8B | 116 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x116-tensor | Qwen3-8B | 116 | tensor | nvlink5 | infiniband_ndr | 144 | 499.87 us | 200.1 tok/s | 2,000.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 325.35 us |
| Qwen3-8B/b200_sxm-x116-hybrid | Qwen3-8B | 116 | hybrid | nvlink5 | infiniband_ndr | 86 | 205.23 us | 487.2 tok/s | 4,872.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| Qwen3-8B/b200_sxm-x173-pipeline | Qwen3-8B | 173 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x173-tensor | Qwen3-8B | 173 | tensor | nvlink5 | infiniband_ndr | 144 | 500.62 us | 199.8 tok/s | 1,997.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 326.10 us |
| Qwen3-8B/b200_sxm-x173-hybrid | Qwen3-8B | 173 | hybrid | nvlink5 | infiniband_ndr | 93 | 220.59 us | 453.3 tok/s | 4,533.3 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| Qwen3-8B/b200_sxm-x231-pipeline | Qwen3-8B | 231 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x231-tensor | Qwen3-8B | 231 | tensor | nvlink5 | infiniband_ndr | 144 | 501.01 us | 199.6 tok/s | 1,996.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 326.49 us |
| Qwen3-8B/b200_sxm-x231-hybrid | Qwen3-8B | 231 | hybrid | nvlink5 | infiniband_ndr | 100 | 235.95 us | 423.8 tok/s | 4,238.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 61.43 us |
| Qwen3-8B/b200_sxm-x347-pipeline | Qwen3-8B | 347 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x347-tensor | Qwen3-8B | 347 | tensor | nvlink5 | infiniband_ndr | 144 | 501.43 us | 199.4 tok/s | 1,994.3 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 326.91 us |
| Qwen3-8B/b200_sxm-x347-hybrid | Qwen3-8B | 347 | hybrid | nvlink5 | infiniband_ndr | 107 | 251.30 us | 397.9 tok/s | 3,979.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 35 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 76.78 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x30 | DeepSeek-V4-Flash-0731 | 30 | pipeline | nvlink5 | infiniband_ndr | 29 | 38.02 us | 2,630.3 tok/s | 26,303.2 tok/s | 26 x point_to_point span 2 on nvlink5 (traversals 1.0) = 31.44 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer_n5 | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x29 | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x30 | DeepSeek-V4-Flash-0731 | 30 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x32 | DeepSeek-V4-Flash-0731 | 32 | pipeline | nvlink5 | infiniband_ndr | 31 | 40.44 us | 2,473.0 tok/s | 24,730.2 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.85 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer_n5 | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-tensor-x31 | DeepSeek-V4-Flash-0731 | 31 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x32 | DeepSeek-V4-Flash-0731 | 32 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x4-pipeline | DeepSeek-V4-Flash-0731 | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 3.63 us | 27,568.7 tok/s | 275,686.6 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.63 us |
| DSV4-Flash/b200_sxm-x4-tensor | DeepSeek-V4-Flash-0731 | 4 | tensor | nvlink5 | infiniband_ndr | 86 | 208.16 us | 480.4 tok/s | 4,804.0 tok/s | 86 x all_reduce span 4 on nvlink5 (traversals 2.0) = 208.16 us |
| DSV4-Flash/b200_sxm-x15-pipeline | DeepSeek-V4-Flash-0731 | 15 | pipeline | nvlink5 | infiniband_ndr | 14 | 17.91 us | 5,582.8 tok/s | 55,828.0 tok/s | 13 x point_to_point span 2 on nvlink5 (traversals 1.0) = 15.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x15-tensor | DeepSeek-V4-Flash-0731 | 15 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x15-hybrid | DeepSeek-V4-Flash-0731 | 15 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x16-pipeline | DeepSeek-V4-Flash-0731 | 16 | pipeline | nvlink5 | infiniband_ndr | 15 | 19.12 us | 5,229.8 tok/s | 52,297.8 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x16-tensor | DeepSeek-V4-Flash-0731 | 16 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x16-hybrid | DeepSeek-V4-Flash-0731 | 16 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x18-pipeline | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink5 | infiniband_ndr | 17 | 22.52 us | 4,439.7 tok/s | 44,396.7 tok/s | 15 x point_to_point span 2 on nvlink5 (traversals 1.0) = 18.14 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x18-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x18-hybrid | DeepSeek-V4-Flash-0731 | 18 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink5 | infiniband_ndr | 18 | 23.73 us | 4,213.5 tok/s | 42,134.9 tok/s | 16 x point_to_point span 2 on nvlink5 (traversals 1.0) = 19.35 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x21-pipeline | DeepSeek-V4-Flash-0731 | 21 | pipeline | nvlink5 | infiniband_ndr | 20 | 26.15 us | 3,823.9 tok/s | 38,238.7 tok/s | 18 x point_to_point span 2 on nvlink5 (traversals 1.0) = 21.76 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x21-tensor | DeepSeek-V4-Flash-0731 | 21 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x21-hybrid | DeepSeek-V4-Flash-0731 | 21 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x22-pipeline | DeepSeek-V4-Flash-0731 | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 27.36 us | 3,654.9 tok/s | 36,548.9 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 22.97 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x22-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x22-hybrid | DeepSeek-V4-Flash-0731 | 22 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
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
| DSV4-Flash/b200_sxm-x43-pipeline | DeepSeek-V4-Flash-0731 | 43 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x43-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x43-hybrid | DeepSeek-V4-Flash-0731 | 43 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x44-pipeline | DeepSeek-V4-Flash-0731 | 44 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x44-tensor | DeepSeek-V4-Flash-0731 | 44 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x44-hybrid | DeepSeek-V4-Flash-0731 | 44 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x45-pipeline | DeepSeek-V4-Flash-0731 | 45 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x45-tensor | DeepSeek-V4-Flash-0731 | 45 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x45-hybrid | DeepSeek-V4-Flash-0731 | 45 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x50-pipeline | DeepSeek-V4-Flash-0731 | 50 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x50-tensor | DeepSeek-V4-Flash-0731 | 50 | tensor | nvlink5 | infiniband_ndr | 172 | 593.85 us | 168.4 tok/s | 1,683.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 385.39 us |
| DSV4-Flash/b200_sxm-x50-hybrid | DeepSeek-V4-Flash-0731 | 50 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.62 us | 451.2 tok/s | 4,512.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| DSV4-Flash/b200_sxm-x57-pipeline | DeepSeek-V4-Flash-0731 | 57 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x57-tensor | DeepSeek-V4-Flash-0731 | 57 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x57-hybrid | DeepSeek-V4-Flash-0731 | 57 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x58-pipeline | DeepSeek-V4-Flash-0731 | 58 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x58-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x58-hybrid | DeepSeek-V4-Flash-0731 | 58 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x59-pipeline | DeepSeek-V4-Flash-0731 | 59 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x59-tensor | DeepSeek-V4-Flash-0731 | 59 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x59-hybrid | DeepSeek-V4-Flash-0731 | 59 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
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
| DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x159 | DeepSeek-V4-Pro-0813 | 159 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x3 | DeepSeek-V4-Pro-0813 | 3 | pipeline | on_wafer_n5 | inter_wafer | 60 | 12.47 us | 8,018.9 tok/s | 80,188.6 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x155 | DeepSeek-V4-Pro-0813 | 155 | tensor | nvlink5 | infiniband_ndr | 244 | 892.91 us | 112.0 tok/s | 1,119.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 595.01 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x3 | DeepSeek-V4-Pro-0813 | 3 | tensor | on_wafer_n5 | inter_wafer | 244 | 1,478.17 us | 67.7 tok/s | 676.5 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 3 on inter_wafer (traversals 2.0) = 1,243.32 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hybrid-x159 | DeepSeek-V4-Pro-0813 | 159 | hybrid | nvlink5 | infiniband_ndr | 141 | 341.92 us | 292.5 tok/s | 2,924.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 19 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 44.02 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x3 | DeepSeek-V4-Pro-0813 | 3 | hybrid | on_wafer_n5 | inter_wafer | 124 | 245.04 us | 408.1 tok/s | 4,080.9 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 2 x point_to_point span 2 on inter_wafer (traversals 1.0) = 10.19 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x167 | DeepSeek-V4-Pro-0813 | 167 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3 | DeepSeek-V4-Pro-0813 | 3 | pipeline | on_wafer_n5 | inter_wafer | 60 | 12.47 us | 8,018.9 tok/s | 80,188.6 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x163 | DeepSeek-V4-Pro-0813 | 163 | tensor | nvlink5 | infiniband_ndr | 244 | 893.16 us | 112.0 tok/s | 1,119.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 21 on infiniband_ndr (traversals 2.0) = 595.26 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x3 | DeepSeek-V4-Pro-0813 | 3 | tensor | on_wafer_n5 | inter_wafer | 244 | 1,478.17 us | 67.7 tok/s | 676.5 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 3 on inter_wafer (traversals 2.0) = 1,243.32 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x167 | DeepSeek-V4-Pro-0813 | 167 | hybrid | nvlink5 | infiniband_ndr | 142 | 344.24 us | 290.5 tok/s | 2,905.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 20 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.33 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | DeepSeek-V4-Pro-0813 | 3 | hybrid | on_wafer_n5 | inter_wafer | 124 | 245.04 us | 408.1 tok/s | 4,080.9 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 2 x point_to_point span 2 on inter_wafer (traversals 1.0) = 10.19 us |
| DSV4-Pro/b200_sxm-x22-pipeline | DeepSeek-V4-Pro-0813 | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 27.74 us | 3,605.4 tok/s | 36,054.1 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 23.10 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x22-tensor | DeepSeek-V4-Pro-0813 | 22 | tensor | nvlink5 | infiniband_ndr | 244 | 863.18 us | 115.9 tok/s | 1,158.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x22-hybrid | DeepSeek-V4-Pro-0813 | 22 | hybrid | nvlink5 | infiniband_ndr | 124 | 302.53 us | 330.5 tok/s | 3,305.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x29-pipeline | DeepSeek-V4-Pro-0813 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 37.35 us | 2,677.5 tok/s | 26,774.9 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.40 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x29-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5 | infiniband_ndr | 244 | 871.93 us | 114.7 tok/s | 1,146.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x29-hybrid | DeepSeek-V4-Pro-0813 | 29 | hybrid | nvlink5 | infiniband_ndr | 125 | 304.85 us | 328.0 tok/s | 3,280.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x58-pipeline | DeepSeek-V4-Pro-0813 | 58 | pipeline | nvlink5 | infiniband_ndr | 57 | 77.01 us | 1,298.5 tok/s | 12,984.7 tok/s | 50 x point_to_point span 2 on nvlink5 (traversals 1.0) = 60.80 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x58-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5 | infiniband_ndr | 244 | 885.04 us | 113.0 tok/s | 1,129.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 587.14 us |
| DSV4-Pro/b200_sxm-x58-hybrid | DeepSeek-V4-Pro-0813 | 58 | hybrid | nvlink5 | infiniband_ndr | 129 | 314.12 us | 318.4 tok/s | 3,183.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x79-pipeline | DeepSeek-V4-Pro-0813 | 79 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x79-tensor | DeepSeek-V4-Pro-0813 | 79 | tensor | nvlink5 | infiniband_ndr | 244 | 887.67 us | 112.7 tok/s | 1,126.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 589.77 us |
| DSV4-Pro/b200_sxm-x79-hybrid | DeepSeek-V4-Pro-0813 | 79 | hybrid | nvlink5 | infiniband_ndr | 131 | 318.75 us | 313.7 tok/s | 3,137.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| DSV4-Pro/b200_sxm-x81-pipeline | DeepSeek-V4-Pro-0813 | 81 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x81-tensor | DeepSeek-V4-Pro-0813 | 81 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x81-hybrid | DeepSeek-V4-Pro-0813 | 81 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x83-pipeline | DeepSeek-V4-Pro-0813 | 83 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x83-tensor | DeepSeek-V4-Pro-0813 | 83 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x83-hybrid | DeepSeek-V4-Pro-0813 | 83 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x85-pipeline | DeepSeek-V4-Pro-0813 | 85 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x85-tensor | DeepSeek-V4-Pro-0813 | 85 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x85-hybrid | DeepSeek-V4-Pro-0813 | 85 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x87-pipeline | DeepSeek-V4-Pro-0813 | 87 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x87-tensor | DeepSeek-V4-Pro-0813 | 87 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x87-hybrid | DeepSeek-V4-Pro-0813 | 87 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x94-pipeline | DeepSeek-V4-Pro-0813 | 94 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x94-tensor | DeepSeek-V4-Pro-0813 | 94 | tensor | nvlink5 | infiniband_ndr | 244 | 889.42 us | 112.4 tok/s | 1,124.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 591.51 us |
| DSV4-Pro/b200_sxm-x94-hybrid | DeepSeek-V4-Pro-0813 | 94 | hybrid | nvlink5 | infiniband_ndr | 133 | 323.39 us | 309.2 tok/s | 3,092.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| DSV4-Pro/b200_sxm-x98-pipeline | DeepSeek-V4-Pro-0813 | 98 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x98-tensor | DeepSeek-V4-Pro-0813 | 98 | tensor | nvlink5 | infiniband_ndr | 244 | 890.09 us | 112.3 tok/s | 1,123.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 592.19 us |
| DSV4-Pro/b200_sxm-x98-hybrid | DeepSeek-V4-Pro-0813 | 98 | hybrid | nvlink5 | infiniband_ndr | 134 | 325.70 us | 307.0 tok/s | 3,070.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 27.80 us |
| DSV4-Pro/b200_sxm-x113-pipeline | DeepSeek-V4-Pro-0813 | 113 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x113-tensor | DeepSeek-V4-Pro-0813 | 113 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x113-hybrid | DeepSeek-V4-Pro-0813 | 113 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x116-pipeline | DeepSeek-V4-Pro-0813 | 116 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x116-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x116-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x118-pipeline | DeepSeek-V4-Pro-0813 | 118 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x118-tensor | DeepSeek-V4-Pro-0813 | 118 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x118-hybrid | DeepSeek-V4-Pro-0813 | 118 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x150-pipeline | DeepSeek-V4-Pro-0813 | 150 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x150-tensor | DeepSeek-V4-Pro-0813 | 150 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x150-hybrid | DeepSeek-V4-Pro-0813 | 150 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x151-pipeline | DeepSeek-V4-Pro-0813 | 151 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x151-tensor | DeepSeek-V4-Pro-0813 | 151 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x151-hybrid | DeepSeek-V4-Pro-0813 | 151 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x157-pipeline | DeepSeek-V4-Pro-0813 | 157 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x157-tensor | DeepSeek-V4-Pro-0813 | 157 | tensor | nvlink5 | infiniband_ndr | 244 | 892.91 us | 112.0 tok/s | 1,119.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 595.01 us |
| DSV4-Pro/b200_sxm-x157-hybrid | DeepSeek-V4-Pro-0813 | 157 | hybrid | nvlink5 | infiniband_ndr | 141 | 341.92 us | 292.5 tok/s | 2,924.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 19 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 44.02 us |
| DSV4-Pro/b200_sxm-x165-pipeline | DeepSeek-V4-Pro-0813 | 165 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x165-tensor | DeepSeek-V4-Pro-0813 | 165 | tensor | nvlink5 | infiniband_ndr | 244 | 893.16 us | 112.0 tok/s | 1,119.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 21 on infiniband_ndr (traversals 2.0) = 595.26 us |
| DSV4-Pro/b200_sxm-x165-hybrid | DeepSeek-V4-Pro-0813 | 165 | hybrid | nvlink5 | infiniband_ndr | 142 | 344.24 us | 290.5 tok/s | 2,905.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 20 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.33 us |
| DSV4-Pro/b200_sxm-x173-pipeline | DeepSeek-V4-Pro-0813 | 173 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x173-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5 | infiniband_ndr | 244 | 893.39 us | 111.9 tok/s | 1,119.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 595.49 us |
| DSV4-Pro/b200_sxm-x173-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5 | infiniband_ndr | 143 | 346.55 us | 288.6 tok/s | 2,885.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| DSV4-Pro/b200_sxm-x231-pipeline | DeepSeek-V4-Pro-0813 | 231 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x231-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5 | infiniband_ndr | 244 | 894.54 us | 111.8 tok/s | 1,117.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 596.64 us |
| DSV4-Pro/b200_sxm-x231-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5 | infiniband_ndr | 150 | 362.77 us | 275.7 tok/s | 2,756.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 64.87 us |
| DSV4-Pro/b200_sxm-x347-pipeline | DeepSeek-V4-Pro-0813 | 347 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x347-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5 | infiniband_ndr | 244 | 895.78 us | 111.6 tok/s | 1,116.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 597.87 us |
| DSV4-Pro/b200_sxm-x347-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5 | infiniband_ndr | 165 | 397.52 us | 251.6 tok/s | 2,515.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 99.62 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 6,464.4 | 0.140 | 4,941.0 (4,075) | 6,464.4 (46,225) | 1.31x | link_latency |
| Qwen3-8B | 2 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 5,400.8 | 0.058 | 4,528.6 (13,040) | 5,400.8 (92,450) | 1.19x | link_latency |
| Qwen3-8B | 4 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,955.1 | 0.036 | 4,191.8 (46,455) | 4,955.1 (138,675) | 1.18x | link_latency |
| Qwen3-8B | 8 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 4,607.6 | 0.017 | 4,191.8 (46,455) | 4,607.6 (277,350) | 1.10x | link_latency |
| Qwen3-8B | 16 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x113-romfill | 92,095 | 3,928.4 | 0.043 | 3,928.4 (92,095) | 3,991.1 (369,800) | 1.02x | link_latency |
| Qwen3-8B | 32 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x170-romfill | 138,550 | 3,497.7 | 0.025 | 3,497.7 (138,550) | 3,395.4 (554,700) | 0.97x | link_latency |
| Qwen3-8B | 64 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x227-romfill | 185,005 | 2,989.7 | 0.016 | 2,989.7 (185,005) | 2,573.2 (554,700) | 0.86x | link_latency |
| Qwen3-8B | 256 | array | array | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 2,343.2 | 0.008 | 2,343.2 (277,100) | 1,049.1 (554,700) | 0.45x | thermal |
| DeepSeek-V4-Flash-0731 | 1 | wafer | array | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 4,850.6 | 0.105 | 2,627.4 (24,450) | 4,850.6 (46,225) | 1.85x | link_latency |
| DeepSeek-V4-Flash-0731 | 2 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,849.3 | 0.105 | 2,569.2 (25,265) | 4,849.3 (46,225) | 1.89x | link_latency |
| DeepSeek-V4-Flash-0731 | 4 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,744.7 | 0.103 | 2,569.2 (25,265) | 4,744.7 (46,225) | 1.85x | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,553.2 | 0.049 | 2,365.6 (30,155) | 4,553.2 (92,450) | 1.92x | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,216.8 | 0.030 | 2,341.6 (30,155) | 4,216.8 (138,675) | 1.80x | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 3,952.3 | 0.014 | 2,109.5 (35,860) | 3,952.3 (277,350) | 1.87x | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,461.1 | 0.009 | 1,901.8 (46,455) | 3,461.1 (369,800) | 1.82x | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,271.5 | 0.004 | 1,731.6 (185,005) | 2,271.5 (554,700) | 1.31x | link_latency |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x3 | 138,675 | 2,648.8 | 0.019 | 1,036.7 (126,325) | 2,648.8 (138,675) | 2.55x | link_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,648.8 | 0.019 | 913.9 (136,105) | 2,648.8 (138,675) | 2.90x | link_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,648.3 | 0.019 | 843.5 (136,105) | 2,648.3 (138,675) | 3.14x | link_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,314.9 | 0.017 | 843.5 (136,105) | 2,314.9 (138,675) | 2.74x | link_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 2,233.4 | 0.008 | 843.5 (136,105) | 2,233.4 (277,350) | 2.65x | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,086.5 | 0.004 | 719.4 (138,550) | 2,086.5 (554,700) | 2.90x | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,535.9 | 0.003 | 742.3 (157,295) | 1,535.9 (554,700) | 2.07x | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 594.5 | 0.001 | 561.1 (251,020) | 594.5 (554,700) | 1.06x | kv_read |

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
| DeepSeek-V4-Pro-0813 | 384 | 2,140.8 MB | 365.2 mm2 | 65.73 mm2 (18.0%) | 140,230 mm2 | 25,241 mm2 | 152,286 mm2 = 186.9 reticles |

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
| Qwen3-8B | 1 | sram | 28,850.2 | 28,850.2 | 28,850.2 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 28,850.2 | 28,850.2 | 28,850.2 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 28,850.2 | 28,850.2 | 28,850.2 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 29,564.5 | 28,850.2 | 28,850.2 | 1.02x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 50,914.2 | 28,850.2 | 28,850.2 | 1.76x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 79,672.4 | 28,850.2 | 28,850.2 | 2.76x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 130,655.8 | 28,868.1 | 28,868.1 | 4.53x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 268,569.0 | 28,977.9 | 28,977.9 | 9.27x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 1 | rom | 796,701.8 | 31,833.3 | 31,833.3 | 25.03x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 796,701.8 | 31,833.3 | 31,833.3 | 25.03x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 796,701.8 | 31,833.3 | 31,833.3 | 25.03x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 796,701.8 | 31,833.3 | 31,833.3 | 25.03x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 796,701.8 | 31,833.3 | 31,833.3 | 25.03x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 796,701.8 | 31,833.3 | 31,833.3 | 25.03x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 796,701.8 | 31,855.1 | 31,855.1 | 25.01x | 1.00x | thermal | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 796,701.8 | 31,988.8 | 31,988.8 | 24.91x | 1.00x | thermal | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 28,756.4 | 28,756.4 | 28,756.4 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 28,756.4 | 28,756.4 | 28,756.4 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 28,756.4 | 28,756.4 | 28,756.4 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 32,843.7 | 28,756.4 | 31,812.2 | 1.14x | 1.11x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | sram | 61,545.5 | 28,756.4 | 51,744.2 | 2.14x | 1.80x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | sram | 105,265.5 | 28,756.4 | 72,647.4 | 3.66x | 2.53x | link_latency | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 183,515.2 | 28,784.4 | 91,035.2 | 6.38x | 3.16x | link_latency | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 481,621.5 | 28,956.7 | 163,173.9 | 16.63x | 5.64x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 378,264.9 | 41,182.2 | 41,182.2 | 9.19x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 378,264.9 | 41,182.2 | 41,182.2 | 9.19x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 378,264.9 | 41,182.2 | 41,182.2 | 9.19x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 378,264.9 | 41,182.2 | 41,182.2 | 9.19x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 378,264.9 | 41,182.2 | 51,744.2 | 9.19x | 1.26x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | rom | 378,264.9 | 41,182.2 | 72,647.4 | 9.19x | 1.76x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 378,264.9 | 41,182.2 | 91,035.2 | 9.19x | 2.21x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 581,509.9 | 41,909.8 | 197,269.8 | 13.88x | 4.71x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 26,083.1 | 26,053.1 | 26,053.1 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 26,083.1 | 26,053.1 | 26,053.1 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 26,083.1 | 26,053.1 | 26,053.1 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 26,083.1 | 26,053.1 | 26,053.1 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 31,465.0 | 26,053.1 | 28,943.2 | 1.21x | 1.11x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | sram | 53,646.9 | 26,053.1 | 48,310.3 | 2.06x | 1.85x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 82,836.8 | 26,053.1 | 66,763.0 | 3.18x | 2.56x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 152,199.3 | 26,053.1 | 85,274.0 | 5.84x | 3.27x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 71,184.8 | 29,915.9 | 29,915.9 | 2.38x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 71,184.8 | 29,915.9 | 29,915.9 | 2.38x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 71,184.8 | 29,915.9 | 29,915.9 | 2.38x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 71,184.8 | 29,915.9 | 29,915.9 | 2.38x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 71,184.8 | 29,915.9 | 30,927.7 | 2.38x | 1.03x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | rom | 71,184.8 | 29,915.9 | 51,776.9 | 2.38x | 1.73x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 98,296.0 | 29,915.9 | 66,763.0 | 3.29x | 2.23x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 152,199.3 | 29,915.9 | 85,274.0 | 5.09x | 2.85x | kv_read | weight_read | kv_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 27.62x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 10.43 | 1.00 | 31,833.3 | 0.689 | kv_read | 1.10x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 10.43 | 1.00 | 31,833.3 | 0.689 | kv_read | 1.10x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 27.62x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.00x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 10.43 | 1.00 | 31,833.3 | 0.689 | kv_read | 1.10x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.00x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 10.43 | 1.00 | 31,833.3 | 0.689 | kv_read | 1.10x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 27.62x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.00x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 10.43 | 1.00 | 31,833.3 | 0.689 | kv_read | 1.10x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 1.00x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 10.43 | 1.00 | 31,833.3 | 0.689 | kv_read | 1.10x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 29,564.5 | 0.213 | link_latency | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 26.95x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.98x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 10.43 | 1.00 | 31,833.3 | 0.689 | kv_read | 1.08x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.98x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 10.43 | 1.00 | 31,833.3 | 0.689 | kv_read | 1.08x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 50,914.2 | 0.275 | link_latency | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 15.65x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.57x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 10.43 | 1.00 | 31,833.3 | 0.689 | kv_read | 0.63x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.57x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 10.43 | 1.00 | 31,833.3 | 0.689 | kv_read | 0.63x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 79,672.4 | 0.287 | weight_read | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 10.00x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.36x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 10.43 | 1.00 | 31,833.3 | 0.689 | kv_read | 0.40x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,850.2 | 0.624 | weight_read | 0.36x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 10.43 | 1.00 | 31,833.3 | 0.689 | kv_read | 0.40x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 130,655.8 | 0.353 | weight_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 6.10x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,868.1 | 0.625 | weight_read | 0.22x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 10.43 | 1.12 | 31,855.1 | 0.689 | kv_read | 0.24x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.12 | 28,868.1 | 0.625 | weight_read | 0.22x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 10.43 | 1.12 | 31,855.1 | 0.689 | kv_read | 0.24x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 268,569.0 | 0.484 | kv_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x340-romfill | 277,100 | 69.67 | 1.00 | 796,701.8 | 2.875 | thermal | 2.97x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,977.9 | 0.627 | weight_read | 0.11x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 10.43 | 4.49 | 31,988.8 | 0.692 | kv_read | 0.12x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 4.49 | 28,977.9 | 0.627 | weight_read | 0.11x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 10.43 | 4.49 | 31,988.8 | 0.692 | kv_read | 0.12x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 13.15x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x98-perstream-romfill | 79,870 | 1.62 | 1.00 | 41,182.2 | 0.516 | weight_read | 1.43x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x98-perregion-romfill | 79,870 | 1.62 | 1.00 | 41,182.2 | 0.516 | weight_read | 1.43x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 13.15x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x98-perstream-romfill | 79,870 | 1.62 | 1.00 | 41,182.2 | 0.516 | weight_read | 1.43x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x98-perregion-romfill | 79,870 | 1.62 | 1.00 | 41,182.2 | 0.516 | weight_read | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 13.15x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x98-perstream-romfill | 79,870 | 1.62 | 1.00 | 41,182.2 | 0.516 | weight_read | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x98-perregion-romfill | 79,870 | 1.62 | 1.00 | 41,182.2 | 0.516 | weight_read | 1.43x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 32,843.7 | 0.711 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 11.52x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.88x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x98-perstream-romfill | 79,870 | 1.62 | 1.00 | 41,182.2 | 0.516 | weight_read | 1.25x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.13 | 31,812.2 | 0.688 | link_latency | 0.97x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x98-perregion-romfill | 79,870 | 1.62 | 1.00 | 41,182.2 | 0.516 | weight_read | 1.25x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 61,545.5 | 0.666 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 6.15x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.47x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x98-perstream-romfill | 79,870 | 1.62 | 1.00 | 41,182.2 | 0.516 | weight_read | 0.67x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.88 | 51,744.2 | 1.119 | link_latency | 0.84x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.02 | 2.88 | 51,744.2 | 1.119 | link_latency | 0.84x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 105,265.5 | 0.759 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 3.59x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.27x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x98-perstream-romfill | 79,870 | 1.62 | 1.00 | 41,182.2 | 0.516 | weight_read | 0.39x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 4.03 | 72,647.4 | 1.572 | kv_read | 0.69x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.02 | 4.03 | 72,647.4 | 1.572 | kv_read | 0.69x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 183,515.2 | 0.993 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.63 | 1.00 | 378,264.9 | 0.682 | weight_read | 2.06x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,784.4 | 0.623 | weight_read | 0.16x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x98-perstream-romfill | 79,870 | 1.62 | 1.00 | 41,182.2 | 0.516 | weight_read | 0.22x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 5.83 | 91,035.2 | 1.969 | kv_read | 0.50x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.02 | 5.83 | 91,035.2 | 1.969 | kv_read | 0.50x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 481,621.5 | 1.302 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 14.63 | 1.00 | 581,509.9 | 1.048 | link_latency | 1.21x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,956.7 | 0.626 | weight_read | 0.06x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x98-perstream-romfill | 79,870 | 1.62 | 2.61 | 41,909.8 | 0.525 | weight_read | 0.09x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x61-perregion | 49,715 | 1.00 | 4.03 | 163,173.9 | 3.282 | weight_read | 0.34x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x98-perregion-romfill | 79,870 | 1.62 | 3.18 | 197,269.8 | 2.470 | weight_read | 0.41x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 71,184.8 | 0.128 | weight_read | 2.73x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 71,184.8 | 0.128 | weight_read | 2.73x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 71,184.8 | 0.128 | weight_read | 2.73x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 71,184.8 | 0.128 | weight_read | 2.73x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 31,465.0 | 0.113 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 71,184.8 | 0.128 | weight_read | 2.26x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 0.83x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 0.95x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 1.19 | 28,943.2 | 0.104 | link_latency | 0.92x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion-romfill | 277,350 | 1.15 | 1.19 | 30,927.7 | 0.112 | link_latency | 0.98x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 53,646.9 | 0.145 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 71,184.8 | 0.128 | weight_read | 1.33x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 0.49x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 1.66 | 48,310.3 | 0.174 | weight_read | 0.90x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion-romfill | 277,350 | 1.15 | 1.66 | 51,776.9 | 0.187 | kv_read | 0.97x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 82,836.8 | 0.149 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2.73 | 1.00 | 98,296.0 | 0.177 | kv_read | 1.19x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 0.31x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 0.36x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 2.18 | 66,763.0 | 0.241 | kv_read | 0.81x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion-romfill | 277,350 | 1.15 | 2.18 | 66,763.0 | 0.241 | kv_read | 0.81x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 152,199.3 | 0.274 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2.73 | 1.00 | 152,199.3 | 0.274 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 0.17x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 0.20x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 4.02 | 85,274.0 | 0.307 | kv_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion-romfill | 277,350 | 1.15 | 4.02 | 85,274.0 | 0.307 | kv_read | 0.56x |

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
| Qwen3-8B | 1 | 6 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 64 | 57 | 1.12 | 1.123 | 1.123 | 1.00x |
| Qwen3-8B | 256 | 6 | 42.67 | 42.667 | 42.667 | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 61 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 61 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 61 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 61 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 61 | 1.05 | 1.001 | 1.004 | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | 61 | 4.20 | 1.038 | 1.611 | 1.55x |
| DeepSeek-V4-Pro-0813 | 1 | 297 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 341 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 341 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 341 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 323 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 323 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 323 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 323 | 1.00 | 1.000 | 1.000 | 1.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4-Flash-0731 | 2 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4-Flash-0731 | 8 | 4 | 3.87 | 2.62 | 1.47x |
| DeepSeek-V4-Flash-0731 | 16 | 4 | 3.99 | 2.91 | 1.37x |
| DeepSeek-V4-Flash-0731 | 32 | 4 | 4.00 | 3.15 | 1.27x |
| DeepSeek-V4-Flash-0731 | 64 | 4 | 4.00 | 3.33 | 1.20x |
| DeepSeek-V4-Flash-0731 | 256 | 4 | 4.00 | 3.55 | 1.13x |
| DeepSeek-V4-Flash-0731 | 1 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4-Flash-0731 | 2 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4-Flash-0731 | 4 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4-Flash-0731 | 8 | 15 | 5.08 | 3.63 | 1.40x |
| DeepSeek-V4-Flash-0731 | 16 | 15 | 5.35 | 3.73 | 1.44x |
| DeepSeek-V4-Flash-0731 | 32 | 15 | 8.72 | 4.84 | 1.80x |
| DeepSeek-V4-Flash-0731 | 64 | 15 | 12.26 | 6.09 | 2.01x |
| DeepSeek-V4-Flash-0731 | 256 | 15 | 14.96 | 8.55 | 1.75x |
| DeepSeek-V4-Flash-0731 | 1 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 2 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 4 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 8 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 16 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 32 | 16 | 8.56 | 4.83 | 1.77x |
| DeepSeek-V4-Flash-0731 | 64 | 16 | 12.41 | 6.15 | 2.02x |
| DeepSeek-V4-Flash-0731 | 256 | 16 | 15.91 | 8.79 | 1.81x |
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
| DeepSeek-V4-Flash-0731 | 1 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 2 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 4 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 8 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 16 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4-Flash-0731 | 32 | 21 | 7.52 | 4.73 | 1.59x |
| DeepSeek-V4-Flash-0731 | 64 | 21 | 12.21 | 6.25 | 1.95x |
| DeepSeek-V4-Flash-0731 | 256 | 21 | 20.09 | 9.68 | 2.07x |
| DeepSeek-V4-Flash-0731 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 4 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 8 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 16 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 32 | 22 | 7.31 | 4.70 | 1.55x |
| DeepSeek-V4-Flash-0731 | 64 | 22 | 12.05 | 6.25 | 1.93x |
| DeepSeek-V4-Flash-0731 | 256 | 22 | 20.76 | 9.81 | 2.12x |
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
| DeepSeek-V4-Flash-0731 | 1 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 4 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 8 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 16 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 32 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 64 | 43 | 8.11 | 5.69 | 1.43x |
| DeepSeek-V4-Flash-0731 | 256 | 43 | 23.55 | 10.61 | 2.22x |
| DeepSeek-V4-Flash-0731 | 1 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 8 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 16 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 32 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 64 | 44 | 7.96 | 5.66 | 1.41x |
| DeepSeek-V4-Flash-0731 | 256 | 44 | 23.39 | 10.61 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1 | 45 | 5.68 | 4.70 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 45 | 5.68 | 4.70 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 45 | 5.68 | 4.70 | 1.21x |
| DeepSeek-V4-Flash-0731 | 8 | 45 | 5.68 | 4.70 | 1.21x |
| DeepSeek-V4-Flash-0731 | 16 | 45 | 5.68 | 4.70 | 1.21x |
| DeepSeek-V4-Flash-0731 | 32 | 45 | 5.68 | 4.70 | 1.21x |
| DeepSeek-V4-Flash-0731 | 64 | 45 | 7.82 | 5.63 | 1.39x |
| DeepSeek-V4-Flash-0731 | 256 | 45 | 23.23 | 10.60 | 2.19x |
| DeepSeek-V4-Flash-0731 | 1 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 2 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 4 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 8 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 16 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 32 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 64 | 50 | 7.16 | 5.48 | 1.31x |
| DeepSeek-V4-Flash-0731 | 256 | 50 | 22.32 | 10.54 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1 | 57 | 5.74 | 4.89 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 57 | 5.74 | 4.89 | 1.17x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 5.74 | 4.89 | 1.17x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 5.74 | 4.89 | 1.17x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 5.74 | 4.89 | 1.17x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 5.74 | 4.89 | 1.17x |
| DeepSeek-V4-Flash-0731 | 64 | 57 | 6.40 | 5.25 | 1.22x |
| DeepSeek-V4-Flash-0731 | 256 | 57 | 20.94 | 10.37 | 2.02x |
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
| DeepSeek-V4-Pro-0813 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 2 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 4 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 8 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 16 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 32 | 22 | 7.32 | 4.70 | 1.56x |
| DeepSeek-V4-Pro-0813 | 64 | 22 | 12.11 | 6.27 | 1.93x |
| DeepSeek-V4-Pro-0813 | 256 | 22 | 20.89 | 9.93 | 2.10x |
| DeepSeek-V4-Pro-0813 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 2 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 8 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 16 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 32 | 29 | 6.01 | 4.50 | 1.34x |
| DeepSeek-V4-Pro-0813 | 64 | 29 | 10.70 | 6.10 | 1.75x |
| DeepSeek-V4-Pro-0813 | 256 | 29 | 23.96 | 10.50 | 2.28x |
| DeepSeek-V4-Pro-0813 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 2 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 4 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 8 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 16 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 32 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 64 | 58 | 6.30 | 5.21 | 1.21x |
| DeepSeek-V4-Pro-0813 | 256 | 58 | 20.96 | 10.41 | 2.01x |
| DeepSeek-V4-Pro-0813 | 1 | 79 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 79 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Pro-0813 | 4 | 79 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Pro-0813 | 8 | 79 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Pro-0813 | 16 | 79 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Pro-0813 | 32 | 79 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Pro-0813 | 64 | 79 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Pro-0813 | 256 | 79 | 17.07 | 9.61 | 1.78x |
| DeepSeek-V4-Pro-0813 | 1 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 4 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 8 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 16 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 32 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 64 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 256 | 81 | 16.75 | 9.55 | 1.75x |
| DeepSeek-V4-Pro-0813 | 1 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Pro-0813 | 4 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Pro-0813 | 8 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Pro-0813 | 16 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Pro-0813 | 32 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Pro-0813 | 64 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Pro-0813 | 256 | 83 | 16.44 | 9.49 | 1.73x |
| DeepSeek-V4-Pro-0813 | 1 | 85 | 5.83 | 5.18 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 85 | 5.83 | 5.18 | 1.12x |
| DeepSeek-V4-Pro-0813 | 4 | 85 | 5.83 | 5.18 | 1.12x |
| DeepSeek-V4-Pro-0813 | 8 | 85 | 5.83 | 5.18 | 1.12x |
| DeepSeek-V4-Pro-0813 | 16 | 85 | 5.83 | 5.18 | 1.12x |
| DeepSeek-V4-Pro-0813 | 32 | 85 | 5.83 | 5.18 | 1.12x |
| DeepSeek-V4-Pro-0813 | 64 | 85 | 5.83 | 5.18 | 1.12x |
| DeepSeek-V4-Pro-0813 | 256 | 85 | 16.14 | 9.43 | 1.71x |
| DeepSeek-V4-Pro-0813 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 4 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 8 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 16 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 32 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 64 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 256 | 87 | 15.84 | 9.37 | 1.69x |
| DeepSeek-V4-Pro-0813 | 1 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 4 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 8 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 16 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 32 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 64 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 256 | 94 | 14.89 | 9.20 | 1.62x |
| DeepSeek-V4-Pro-0813 | 1 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 4 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 8 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 16 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 32 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 64 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 256 | 98 | 14.38 | 9.12 | 1.58x |
| DeepSeek-V4-Pro-0813 | 1 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 4 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 8 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 16 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 32 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 64 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 256 | 113 | 12.74 | 8.83 | 1.44x |
| DeepSeek-V4-Pro-0813 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 4 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 8 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 16 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 32 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 64 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 256 | 116 | 12.45 | 8.77 | 1.42x |
| DeepSeek-V4-Pro-0813 | 1 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 4 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 8 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 16 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 32 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 64 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 256 | 118 | 12.27 | 8.73 | 1.41x |
| DeepSeek-V4-Pro-0813 | 1 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 150 | 9.88 | 8.05 | 1.23x |
| DeepSeek-V4-Pro-0813 | 1 | 151 | 5.90 | 5.50 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 151 | 5.90 | 5.50 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 151 | 5.90 | 5.50 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 151 | 5.90 | 5.50 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 151 | 5.90 | 5.50 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 151 | 5.90 | 5.50 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 151 | 5.90 | 5.50 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 151 | 9.82 | 8.02 | 1.22x |
| DeepSeek-V4-Pro-0813 | 1 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 157 | 9.47 | 7.88 | 1.20x |
| DeepSeek-V4-Pro-0813 | 1 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 165 | 9.04 | 7.69 | 1.18x |
| DeepSeek-V4-Pro-0813 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 4 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 8 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 16 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 32 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 64 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 256 | 173 | 8.65 | 7.49 | 1.15x |
| DeepSeek-V4-Pro-0813 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 231 | 6.56 | 6.17 | 1.06x |
| DeepSeek-V4-Pro-0813 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 347 | 5.96 | 5.77 | 1.03x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 1.9% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 1.4% |
| gpu | Qwen3-8B | 1 | 6.82 | 1.4% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 6.0% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 4.7% |
| rom | Qwen3-8B | 1 | 6.82 | 4.4% |

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
| Qwen3-8B | 1 | 6 | 93.15% | 51.84 | 9.27 |
| Qwen3-8B | 2 | 1 | 1.17% | 6.16 | 9.27 |
| Qwen3-8B | 4 | 1 | 1.17% | 6.16 | 9.27 |
| Qwen3-8B | 8 | 1 | 1.17% | 6.16 | 9.27 |
| Qwen3-8B | 16 | 1 | 1.17% | 6.16 | 9.27 |
| Qwen3-8B | 32 | 1 | 1.17% | 6.16 | 9.27 |
| Qwen3-8B | 64 | 1 | 1.31% | 6.92 | 9.27 |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 48.08% | 57.38 | 2.13 |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 48.08% | 57.38 | 2.13 |
| DeepSeek-V4-Pro-0813 | 1 | 297 | 96.87% | 597.61 | 2.08 |
| DeepSeek-V4-Pro-0813 | 2 | 6 | 10.10% | 71.55 | 2.08 |
| DeepSeek-V4-Pro-0813 | 4 | 6 | 10.10% | 71.55 | 2.08 |
| DeepSeek-V4-Pro-0813 | 8 | 6 | 10.10% | 71.55 | 2.08 |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 2,415.6 | 9,662.4 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 2,415.6 | 9,662.4 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 2,415.6 | 9,662.4 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 1,228.9 | 9,831.2 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 619.9 | 9,917.8 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 311.3 | 9,961.7 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 156.0 | 9,983.7 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 92.40% | 439.19 TB/s | 475.30 TB/s | 39.1 | 10,000.4 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 765.9 | 23,743.9 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 765.9 | 23,743.9 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 765.9 | 23,743.9 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 765.9 | 23,743.9 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 765.9 | 23,743.9 |
| DeepSeek-V4-Flash-0731 | 32 | 2.42% | 11.3 GB | 6.79% | 328.66 TB/s | 4,841.92 TB/s | 742.9 | 23,772.8 |
| DeepSeek-V4-Flash-0731 | 64 | 4.78% | 14.8 GB | 8.87% | 429.43 TB/s | 4,841.92 TB/s | 378.6 | 24,230.8 |
| DeepSeek-V4-Flash-0731 | 256 | 17.79% | 33.9 GB | 20.34% | 984.90 TB/s | 4,841.92 TB/s | 96.0 | 24,586.0 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 107.4 | 17,501.9 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 107.4 | 17,501.9 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 107.4 | 17,501.9 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 107.4 | 17,501.9 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 107.4 | 17,501.9 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 107.4 | 17,501.9 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 107.4 | 17,501.9 |
| DeepSeek-V4-Pro-0813 | 256 | 2.44% | 46.9 GB | 5.25% | 1,360.93 TB/s | 25,902.15 TB/s | 68.6 | 17,567.3 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 2 |
| gpu | kv_read | 17 |
| gpu | link_latency | 390 |
| gpu | thermal | 102 |
| gpu | weight_read | 761 |
| rom | compute | 143 |
| rom | infeasible | 2440 |
| rom | kv_read | 231 |
| rom | link_latency | 1412 |
| rom | thermal | 285 |
| rom | weight_read | 1297 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 2 |
| rom | CAPACITY | 2440 |

## Mechanical consistency audit

**PASS** over 148,996 checks.

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

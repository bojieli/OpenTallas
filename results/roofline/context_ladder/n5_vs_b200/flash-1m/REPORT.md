# Area-constrained roofline: n5_vs_b200-flash-1m

> CONTEXT-LADDER RUNG of n5_vs_b200: DeepSeek-V4-Flash-0731 at 1,000,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 1,282x (ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream, 1,872 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 34 devices. On the GPU side the correction reaches 29x (b200_sxm-x953-pipeline, 953 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 46 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Flash-0731 takes 36 x 815 mm2 (29,340 mm2, array, KV in SRAM) at 11,664 tok/s per user and 398 tok/s per 1,000 mm2, holding 1 session, against 18 copies of one unified HBM die at the same silicon: 3.9x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Flash-0731 on 29,340 mm2 of ROM silicon at 11,664 tok/s per user against 28,800 mm2 of b200_sxm-x18-nvl72-tensor at 3,028 tok/s: **3.9x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 399. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 8.25x to it.** At 227,385 mm2 on DeepSeek-V4-Flash-0731 the pipeline-only GPU delivers 483.05 tok/s and the same silicon running hybrid delivers 3,984 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.05x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 1.34x (DeepSeek-V4-Flash-0731, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 1,366 to 475,451 tok/s, and its rate with every slot occupied from 381,137 to 475,451. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 279 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 949 us over NVLink, capping per-user decode at 1,054 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 260.5 us and cap it at 3,839 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 10 operating points and an array 8; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 158 of 2695 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 28.0x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 22.12x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.04x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 10 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 288 of 2,695 feasible points (10.7%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x349` at batch 4096 on 284,435 mm2, throttled 1.57x from 226 to 144 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 96% kv read against 0.2% weight read. The ROM sweep is not what melts it.


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

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x36`** -- 36 x 815 mm2 reticle dies, 29,340 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **11,663.5 tok/s per user** (0.09 ms/token), binding on `link_latency`
- **397.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 11,664 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 1,953 W at 0.067 W/mm2, 167.5 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 18 copies of one unified HBM die -- `b200_sxm-x18-nvl72-tensor`, 28,800 mm2, area ratio 1.0188 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 29,340 | 28,800 | 1.0188 |
| user tok/s | 11,663.5 | 3,028.3 | 3.85x |
| aggregate tok/s | 11,664 | 3,028 | 1.34x |
| resident sessions | 1 | 399 | -- |
| J/token | 0.1675 | 3.4277 | 20.5x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 399 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x142-nvl72-hybrid` at 227,200 mm2 and 3,984.2 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-tensor-x52-romfill` | 42,380 | 12,076.8 | 285.0 | 1 | 3.58x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | 51,345 | 12,688.5 | 247.1 | 1 | 3.58x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | 29,340 | 11,663.5 | 397.5 | 1 | 3.85x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | 29,340 | 11,663.5 | 397.5 | 1 | 3.85x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | 29,340 | 11,663.5 | 397.5 | -- | 397.5 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x47-romfill` | 38,305 | 11,819.6 | 308.6 | 17.4 | 397.5 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x52-romfill` | 42,380 | 12,076.8 | 285.0 | 31.7 | 397.5 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x57` | 46,455 | 12,468.6 | 268.4 | 47.0 | 397.5 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x60` | 48,900 | 12,588.8 | 257.4 | 47.3 | 397.5 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | 51,345 | 12,688.5 | 247.1 | 46.6 | 397.5 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x36` **<-- recommended** | 29,340 | 36 | 11,663.5 | 11,664 | 397.5 | 1 | `link_latency` | 1,953 | 167.5 | `b200_sxm-x18-nvl72-tensor` | 3.85x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x47-romfill` | 38,305 | 47 | 11,819.6 | 11,820 | 308.6 | 1 | `link_latency` | 3,249 | 274.9 | `b200_sxm-x24-nvl72-tensor` | 3.58x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x52-romfill` | 42,380 | 52 | 12,076.8 | 12,077 | 285.0 | 1 | `link_latency` | 3,681 | 304.8 | `b200_sxm-x26-nvl72-tensor` | 3.58x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x57` | 46,455 | 57 | 12,468.6 | 12,469 | 268.4 | 1 | `link_latency` | 4,439 | 356.0 | `b200_sxm-x29-nvl72-tensor` | 3.60x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x60` | 48,900 | 60 | 12,588.8 | 12,589 | 257.4 | 1 | `link_latency` | 4,795 | 380.9 | `b200_sxm-x31-nvl72-tensor` | 3.58x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | 51,345 | 63 | 12,688.5 | 12,688 | 247.1 | 1 | `link_latency` | 5,151 | 406.0 | `b200_sxm-x32-nvl72-tensor` | 3.58x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 228 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | 29,340 | 11,663.5 | 397.5 | 1 |
| array | 228 | fastest | `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | 51,345 | 12,688.5 | 247.1 | 1 |
| array | 228 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | 29,340 | 11,663.5 | 397.5 | 1 |
| wafer | 46 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,403.4 | 116.9 | 1 |
| wafer | 46 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 5,458.3 | 59.0 | 1 |
| wafer | 46 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,403.4 | 116.9 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-tensor-x63` | 51,345 | 12,688.5 | 12,688 | 1 | 5,151 | 406.0 | `link_latency` | `b200_sxm-x32-nvl72-tensor` | 3,539.8 | 728 | 4,512.7 | 1.003 | 3.58x | 11.1x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 5,458.3 | 5,458 | 1 | 11,017 | 2,018.3 | `link_latency` | `b200_sxm-x58-nvl72-tensor` | 3,921.7 | 1,340 | 6,527.6 | 0.996 | 1.39x | 3.2x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-hybrid-x108` | 88,020 | 10,902.5 | 10,903 | 1 | 10,446 | 958.1 | `compute` | `b200_sxm-x55-nvl72-tensor` | 3,893.5 | 1,269 | 6,295.1 | 1.000 | 2.80x | 6.6x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 5,458.3 | -- | 1 | -- | 2,018.3 | -- | -- | -- | -- | -- | 0.952 | 0.50x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,320.2 | 537,214 | 4,999 | 120,271 | 2,515.4 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 3,852.3 | 4,045 | 9,213.5 | 1.001 | 1.64x | 3.7x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 4,447.5 | 146,766 | 4,173 | 160,050 | 15,379.2 | `link_latency` | `b200_sxm-x953-nvl72-hybrid` | 3,590.6 | 22,397 | 47,851.1 | 1.000 | 1.24x | 3.1x |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,320.2 | 537,214 | 4,999 | 120,271 | 1,342.0 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 3,775.7 | 4,045 | 5,153.4 | 1.001 | 1.67x | 3.8x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 4,447.5 | 146,766 | 4,173 | 160,050 | 7,773.9 | `link_latency` | `b200_sxm-x953-nvl72-hybrid` | 3,590.6 | 22,397 | 24,597.9 | 1.000 | 1.24x | 3.2x |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,320.2 | 537,214 | 4,999 | 120,271 | 755.3 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 3,500.4 | 4,045 | 2,992.3 | 1.001 | 1.81x | 4.0x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 4,447.5 | 146,766 | 4,173 | 160,050 | 3,971.3 | `link_latency` | `b200_sxm-x953-nvl72-hybrid` | 3,590.6 | 22,397 | 12,971.3 | 1.000 | 1.24x | 3.3x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,320.2 | 537,214 | 4,999 | 120,271 | 462.0 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 3,065.2 | 4,045 | 1,899.5 | 1.001 | 2.06x | 4.1x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 4,447.5 | 146,766 | 4,173 | 160,050 | 2,070.0 | `link_latency` | `b200_sxm-x953-nvl72-hybrid` | 3,562.1 | 22,397 | 7,101.9 | 1.000 | 1.25x | 3.4x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,320.2 | 537,214 | 4,999 | 120,271 | 315.3 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 2,479.7 | 4,045 | 1,330.3 | 1.001 | 2.55x | 4.2x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 4,447.5 | 146,766 | 4,173 | 160,050 | 1,119.3 | `link_latency` | `b200_sxm-x953-nvl72-hybrid` | 3,350.8 | 22,397 | 3,994.6 | 1.000 | 1.33x | 3.6x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,320.2 | 537,214 | 4,999 | 120,271 | 242.0 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 1,840.8 | 4,045 | 1,006.4 | 1.001 | 3.43x | 4.2x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 3,760.8 | 240,689 | 4,173 | 175,608 | 729.6 | `link_latency` | `b200_sxm-x953-nvl72-hybrid` | 3,001.6 | 22,397 | 2,430.4 | 1.000 | 1.25x | 3.3x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x349-romfill` | 284,435 | 2,332.0 | 597,001 | 5,131 | 130,182 | 218.1 | `compute` | `b200_sxm-x178-nvl72-hybrid` | 878.5 | 4,163 | 609.9 | 0.999 | 2.65x | 2.7x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 1,525,425 | 1,922.4 | 492,133 | 4,173 | 304,858 | 619.5 | `kv_read` | `b200_sxm-x953-nvl72-hybrid` | 1,906.5 | 22,397 | 1,192.2 | 1.000 | 1.01x | 1.9x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x349-romfill` | 284,435 | 606.4 | 620,910 | 5,131 | 134,172 | 216.1 | `compute` | `b200_sxm-x178-nvl72-hybrid` | 347.5 | 4,163 | 388.6 | 0.999 | 1.75x | 1.7x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 1,525,425 | 650.5 | 666,098 | 4,173 | 333,517 | 500.7 | `kv_read` | `b200_sxm-x953-nvl72-hybrid` | 896.9 | 22,397 | 714.6 | 1.000 | 0.73x | 1.1x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x349-romfill` | 284,435 | 152.5 | 624,807 | 5,131 | 134,375 | 215.1 | `compute` | `b200_sxm-x178-expert` | 114.1 | 4,139 | 303.0 | 0.999 | 1.34x | 1.4x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill` | 1,525,425 | 183.9 | 753,373 | 4,173 | 261,365 | 346.9 | `kv_read` | `b200_sxm-x953-expert` | 442.7 | 22,264 | 353.8 | 1.000 | 0.42x | 1.0x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x36` | 29,340 | array | SRAM | 1 |
| 2-256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 227,385 | array | HBM | 4,102 |
| 1024-4096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x279-romfill` | 227,385 | array | HBM | 4,102 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 279, 340, 349 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 279, 340, 349 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 36, 38, 40, 45, 47, 52, 57, 60, 61, 64, 90, 113, 120, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 36, 38, 40, 45, 57, 60, 63, 90, 106, 107, 108, 113, 120, 170, 227, 340 |

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

- **288 of 2,695 feasible points (10.7%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 253, rom 35.
- By area class: large array (5,000-40,000 mm2) 74, wafer (>=40,000 mm2) 214.
- By KV store: hbm 288.
- By batch: B=1 29, B=2 29, B=4 29, B=8 29, B=16 29, B=32 29, B=64 29, B=256 35, B=1024 29, B=4096 21.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 45% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 420 | 74 | 75.6% | 100.0% | 0.625 | 46% |
| gpu | wafer (>=40,000 mm2) | 1,159 | 179 | 57.0% | 100.0% | 0.625 | 61% |
| rom | large array (5,000-40,000 mm2) | 114 | 0 | 13.4% | 17.0% | 0.085 | 98% |
| rom | wafer (>=40,000 mm2) | 1,002 | 35 | 27.3% | 100.0% | 0.500 | 82% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x349` | DeepSeek-V4-Flash-0731 | 4096 | 284,435 | hbm | 1.567x | 142,217.5 / 142,217.5 W | 31% | 144.3 | 226.2 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340` | DeepSeek-V4-Flash-0731 | 4096 | 277,100 | hbm | 1.566x | 138,550.0 / 138,550.0 W | 31% | 140.7 | 220.3 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279` | DeepSeek-V4-Flash-0731 | 4096 | 227,385 | hbm | 1.558x | 113,692.5 / 113,692.5 W | 30% | 116.1 | 180.9 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279` | DeepSeek-V4-Flash-0731 | 1024 | 227,385 | hbm | 1.553x | 113,692.5 / 113,692.5 W | 30% | 462.6 | 718.3 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x349` | DeepSeek-V4-Flash-0731 | 4096 | 284,435 | hbm | 1.552x | 142,217.5 / 142,217.5 W | 31% | 144.7 | 224.6 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340` | DeepSeek-V4-Flash-0731 | 4096 | 277,100 | hbm | 1.551x | 138,550.0 / 138,550.0 W | 31% | 141.1 | 218.8 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x349` | DeepSeek-V4-Flash-0731 | 4096 | 284,435 | hbm | 1.544x | 142,217.5 / 142,217.5 W | 31% | 144.3 | 222.8 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279` | DeepSeek-V4-Flash-0731 | 4096 | 227,385 | hbm | 1.544x | 113,692.5 / 113,692.5 W | 30% | 116.4 | 179.7 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x340` | DeepSeek-V4-Flash-0731 | 4096 | 277,100 | hbm | 1.544x | 138,550.0 / 138,550.0 W | 31% | 140.7 | 217.2 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x279` | DeepSeek-V4-Flash-0731 | 4096 | 227,385 | hbm | 1.539x | 113,692.5 / 113,692.5 W | 30% | 116.1 | 178.7 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x349` | DeepSeek-V4-Flash-0731 | 1024 | 284,435 | hbm | 1.537x | 142,217.5 / 142,217.5 W | 31% | 577.2 | 887.4 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340` | DeepSeek-V4-Flash-0731 | 1024 | 277,100 | hbm | 1.537x | 138,550.0 / 138,550.0 W | 31% | 562.7 | 864.9 |

The worst point's dynamic energy is kv read 95.9%, arithmetic 3.2%, operand delivery 0.7%, weight read 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4-Flash-0731 | 1 | 42,380 | `DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x52-romfill` | 0.304814 | 3,681.2 | link_latency | `DSV4-Flash/b200_sxm-x26-nvl72-tensor` | 4.047677 | 13,644.3 | link_latency | 13.28x |
| DeepSeek-V4-Flash-0731 | 2 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 2.100436 | 98,724.5 | compute | `DSV4-Flash/b200_sxm-x142-nvl72-hybrid` | 7.589627 | 60,477.6 | link_latency | 3.61x |
| DeepSeek-V4-Flash-0731 | 4 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 1.134549 | 98,724.5 | compute | `DSV4-Flash/b200_sxm-x142-nvl72-hybrid` | 4.217702 | 63,881.4 | link_latency | 3.72x |
| DeepSeek-V4-Flash-0731 | 8 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 0.651605 | 98,724.5 | compute | `DSV4-Flash/b200_sxm-x142-nvl72-hybrid` | 2.522387 | 69,631.7 | link_latency | 3.87x |
| DeepSeek-V4-Flash-0731 | 16 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 0.410133 | 98,724.5 | compute | `DSV4-Flash/b200_sxm-x142-nvl72-hybrid` | 1.657027 | 78,146.0 | link_latency | 4.04x |
| DeepSeek-V4-Flash-0731 | 32 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 0.289397 | 98,724.5 | compute | `DSV4-Flash/b200_sxm-x142-nvl72-hybrid` | 1.192608 | 88,489.9 | link_latency | 4.12x |
| DeepSeek-V4-Flash-0731 | 64 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill` | 0.229029 | 98,724.5 | compute | `DSV4-Flash/b200_sxm-x142-nvl72-hybrid` | 0.909264 | 98,141.9 | link_latency | 3.97x |
| DeepSeek-V4-Flash-0731 | 256 | 277,100 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.217976 | 126,911.6 | compute | `DSV4-Flash/b200_sxm-x173-nvl72-hybrid` | 0.606811 | 134,116.3 | link_latency | 2.72x |
| DeepSeek-V4-Flash-0731 | 1024 | 1,525,425 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33` | 0.500702 | 333,516.8 | kv_read | `DSV4-Flash/b200_sxm-x953-nvl72-hybrid` | 0.714566 | 656,310.4 | link_latency | 1.13x |
| DeepSeek-V4-Flash-0731 | 4096 | 1,525,425 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill` | 0.346926 | 261,365.1 | kv_read | `DSV4-Flash/b200_sxm-x953-expert` | 0.353769 | 641,495.6 | kv_read | 1.02x |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 40,374.7 | wafer-pipeline | 5,403.4 | wafer-tensor | 7.47x | 8,320.1 | pipeline | 3,462.1 | tensor | 2.40x | 4.85x | 1.56x | 0.32x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 49,447.0 | wafer-pipeline | 5,458.3 | wafer-hybrid | 9.06x | 9,632.9 | pipeline | 3,921.7 | tensor | 2.46x | 5.13x | 1.39x | 0.27x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 49,463.3 | wafer-pipeline | 5,380.2 | wafer-hybrid | 9.19x | 10,832.8 | pipeline | 3,724.5 | hybrid | 2.91x | 4.57x | 1.44x | 0.32x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 50,144.2 | wafer-pipeline | 5,334.9 | wafer-hybrid | 9.40x | 11,552.4 | pipeline | 3,888.1 | hybrid | 2.97x | 4.34x | 1.37x | 0.32x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 50,204.7 | wafer-pipeline | 5,205.5 | wafer-hybrid | 9.64x | 12,364.1 | pipeline | 3,852.3 | hybrid | 3.21x | 4.06x | 1.35x | 0.33x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 50,204.7 | wafer-pipeline | 5,079.8 | wafer-hybrid | 9.88x | 12,824.6 | pipeline | 3,820.7 | hybrid | 3.36x | 3.91x | 1.33x | 0.34x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 50,204.7 | wafer-pipeline | 4,845.8 | wafer-hybrid | 10.36x | 13,319.2 | pipeline | 3,872.8 | hybrid | 3.44x | 3.77x | 1.25x | 0.33x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.27x to 0.34x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x63 | 51,345 | 12,688.5 | 12,688.5 | link_latency | DSV4-Flash/b200_sxm-x32-nvl72-tensor | 51,200 | 1.00x | tensor | 208.67 | 3,539.8 | 3,539.8 | link_latency | 3.58x | 0.82x | 26.27x | 3.58x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x36 | 29,340 | 11,663.5 | 11,663.5 | link_latency | DSV4-Flash/b200_sxm-x18-nvl72-tensor | 28,800 | 1.02x | tensor | 208.62 | 3,028.3 | 3,028.3 | link_latency | 3.85x | 1.34x | 24.15x | 3.85x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,320.2 | 537,214.4 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 213.10 | 3,852.3 | 11,556.9 | link_latency | 1.64x | 6.43x | 13.08x | 1.64x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 6,300.3 | 441,019.9 | compute | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 210.91 | 3,984.2 | 7,968.5 | link_latency | 1.58x | 6.43x | 13.04x | 1.58x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,320.2 | 537,214.4 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 213.98 | 3,775.7 | 15,102.8 | link_latency | 1.67x | 6.43x | 13.08x | 1.67x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 6,300.3 | 441,019.9 | compute | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 213.39 | 3,786.5 | 15,146.0 | link_latency | 1.66x | 6.43x | 13.04x | 1.66x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,320.2 | 537,214.4 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 217.51 | 3,500.4 | 28,003.4 | link_latency | 1.81x | 6.43x | 13.08x | 1.81x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 6,300.3 | 441,019.9 | compute | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 218.35 | 3,450.7 | 27,605.5 | link_latency | 1.83x | 6.43x | 13.04x | 1.83x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,320.2 | 537,214.4 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 224.56 | 3,065.2 | 49,043.9 | link_latency | 2.06x | 6.43x | 13.08x | 2.06x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 6,300.3 | 441,019.9 | compute | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 228.27 | 2,947.5 | 47,160.4 | link_latency | 2.14x | 6.43x | 13.04x | 2.14x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,320.2 | 537,214.4 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 238.66 | 2,479.7 | 79,350.3 | link_latency | 2.55x | 6.43x | 13.08x | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 6,300.3 | 441,019.9 | compute | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 248.10 | 2,318.7 | 74,198.6 | link_latency | 2.72x | 5.94x | 13.04x | 2.72x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,320.2 | 537,214.4 | compute | DSV4-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 266.85 | 1,840.8 | 117,813.2 | link_latency | 3.43x | 4.56x | 13.08x | 3.43x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 6,300.3 | 441,019.9 | compute | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 287.78 | 1,686.5 | 107,935.6 | link_latency | 3.74x | 4.09x | 13.04x | 3.74x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x349-romfill | 284,435 | 2,332.0 | 597,000.9 | compute | DSV4-Flash/b200_sxm-x178-nvl72-hybrid | 284,800 | 1.00x | hybrid | 436.03 | 878.5 | 224,889.7 | link_latency | 2.65x | 2.65x | 5.65x | 2.65x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 1,880.4 | 481,372.3 | compute | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 525.82 | 779.6 | 199,581.0 | link_latency | 2.41x | 2.41x | 5.10x | 2.41x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33 | 1,525,425 | 650.5 | 666,098.5 | kv_read | DSV4-Flash/b200_sxm-x953-nvl72-hybrid | 1,524,800 | 1.00x | hybrid | 557.96 | 896.9 | 918,474.3 | link_latency | 0.73x | 0.73x | 1.39x | 0.73x |
| DeepSeek-V4-Flash-0731 | 1024 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-romfill | 227,385 | 485.5 | 497,201.5 | compute | DSV4-Flash/b200_sxm-x142-expert | 227,200 | 1.00x | expert | 1,114.40 | 285.1 | 291,909.6 | kv_read | 1.70x | 1.70x | 3.32x | 1.70x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 183.9 | 753,373.2 | kv_read | DSV4-Flash/b200_sxm-x953-expert | 1,524,800 | 1.00x | expert | 815.07 | 442.7 | 1,813,316.5 | kv_read | 0.42x | 0.42x | 0.86x | 0.42x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-romfill | 227,385 | 122.0 | 499,696.8 | compute | DSV4-Flash/b200_sxm-x142-pipeline | 227,200 | 1.00x | pipeline | 87.89 | infeasible | — | capacity_or_format | — | — | — | — |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 9 | 14,400 | 208.49 | 208.49 | 2,276.3 | 2,276.3 |
| DeepSeek-V4-Flash-0731 | 11 | 17,600 | 208.53 | 208.53 | 2,502.3 | 2,502.3 |
| DeepSeek-V4-Flash-0731 | 12 | 19,200 | 208.55 | 208.55 | 2,599.0 | 2,599.0 |
| DeepSeek-V4-Flash-0731 | 17 | 27,200 | 208.61 | 208.61 | 2,970.6 | 2,970.6 |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 208.62 | 208.62 | 3,028.3 | 3,028.3 |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 208.62 | 208.62 | 3,081.9 | 3,081.9 |
| DeepSeek-V4-Flash-0731 | 20 | 32,000 | 208.63 | 208.63 | 3,131.7 | 3,131.7 |
| DeepSeek-V4-Flash-0731 | 23 | 36,800 | 208.65 | 208.65 | 3,262.6 | 3,262.6 |
| DeepSeek-V4-Flash-0731 | 24 | 38,400 | 208.65 | 208.65 | 3,300.9 | 3,300.9 |
| DeepSeek-V4-Flash-0731 | 25 | 40,000 | 208.65 | 208.65 | 3,336.9 | 3,336.9 |
| DeepSeek-V4-Flash-0731 | 26 | 41,600 | 208.66 | 208.66 | 3,370.9 | 3,370.9 |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 208.67 | 208.67 | 3,462.1 | 3,462.1 |
| DeepSeek-V4-Flash-0731 | 31 | 49,600 | 208.67 | 208.67 | 3,515.2 | 3,515.2 |
| DeepSeek-V4-Flash-0731 | 32 | 51,200 | 208.67 | 208.67 | 3,539.8 | 3,539.8 |
| DeepSeek-V4-Flash-0731 | 33 | 52,800 | 208.68 | 208.68 | 3,563.3 | 3,563.3 |
| DeepSeek-V4-Flash-0731 | 46 | 73,600 | 208.70 | 208.70 | 3,790.4 | 3,790.4 |
| DeepSeek-V4-Flash-0731 | 54 | 86,400 | 208.70 | 208.70 | 3,883.5 | 3,883.5 |
| DeepSeek-V4-Flash-0731 | 55 | 88,000 | 208.71 | 208.71 | 3,893.5 | 3,893.5 |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 208.71 | 208.71 | 3,921.7 | 3,921.7 |
| DeepSeek-V4-Flash-0731 | 61 | 97,600 | 208.71 | 208.71 | 3,947.4 | 3,947.4 |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 210.91 | 210.91 | 3,724.5 | 3,724.5 |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 210.91 | 210.91 | 3,888.1 | 3,888.1 |
| DeepSeek-V4-Flash-0731 | 142 | 227,200 | 210.91 | 210.91 | 3,984.2 | 3,984.2 |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 213.10 | 213.10 | 3,852.3 | 3,852.3 |
| DeepSeek-V4-Flash-0731 | 176 | 281,600 | 213.10 | 213.10 | 3,860.9 | 3,860.9 |
| DeepSeek-V4-Flash-0731 | 178 | 284,800 | 213.10 | 213.10 | 3,866.6 | 3,866.6 |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 215.30 | 215.30 | 3,820.7 | 3,820.7 |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 217.49 | 217.49 | 3,872.8 | 3,872.8 |
| DeepSeek-V4-Flash-0731 | 953 | 1,524,800 | 237.24 | 237.24 | 3,590.6 | 3,590.6 |

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
| DeepSeek-V4-Flash-0731 | 9 | 14,400 | 483.1 | 2,276.3 | 1,515.4 | tensor | 208.49 | 47.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 11 | 17,600 | 483.1 | 2,502.3 | 1,722.8 | tensor | 208.53 | 52.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 12 | 19,200 | 483.1 | 2,599.0 | 1,816.0 | tensor | 208.55 | 54.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 17 | 27,200 | 483.1 | 2,970.6 | 1,747.8 | tensor | 208.61 | 62.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 483.1 | 3,028.3 | 1,808.8 | tensor | 208.62 | 63.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 483.1 | 3,081.9 | 1,867.0 | tensor | 208.62 | 64.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 20 | 32,000 | 483.1 | 3,131.7 | 1,922.7 | tensor | 208.63 | 65.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 23 | 36,800 | 483.1 | 3,262.6 | 2,076.2 | tensor | 208.65 | 68.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 24 | 38,400 | 483.1 | 3,300.9 | 2,123.3 | tensor | 208.65 | 68.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 25 | 40,000 | 483.1 | 3,336.9 | 1,845.2 | tensor | 208.65 | 69.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 26 | 41,600 | 483.1 | 3,370.9 | 1,887.3 | tensor | 208.66 | 70.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 483.1 | 3,462.1 | 2,005.7 | tensor | 208.67 | 72.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 31 | 49,600 | 483.1 | 3,515.2 | 2,078.7 | tensor | 208.67 | 73.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | 51,200 | 483.1 | 3,539.8 | 2,113.5 | tensor | 208.67 | 73.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 33 | 52,800 | 483.1 | 3,563.3 | 1,895.8 | tensor | 208.68 | 74.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 46 | 73,600 | 483.1 | 3,790.4 | 2,048.2 | tensor | 208.70 | 79.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 54 | 86,400 | 483.1 | 3,883.5 | 2,045.7 | tensor | 208.70 | 81.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 55 | 88,000 | 483.1 | 3,893.5 | 2,065.3 | tensor | 208.71 | 81.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 483.1 | 3,921.7 | 1,971.0 | tensor | 208.71 | 81.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 61 | 97,600 | 483.1 | 3,947.4 | 2,024.2 | tensor | 208.71 | 82.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 483.1 | 1,628.7 | 3,724.5 | hybrid | 210.91 | 78.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 483.1 | 1,643.8 | 3,888.1 | hybrid | 210.91 | 82.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 142 | 227,200 | 483.1 | 1,652.2 | 3,984.2 | hybrid | 210.91 | 84.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 483.1 | 1,639.8 | 3,852.3 | hybrid | 213.10 | 82.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 176 | 281,600 | 483.1 | 1,640.4 | 3,860.9 | hybrid | 213.10 | 82.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 178 | 284,800 | 483.1 | 1,640.7 | 3,866.6 | hybrid | 213.10 | 82.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 483.1 | 1,638.1 | 3,820.7 | hybrid | 215.30 | 82.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 483.1 | 1,640.0 | 3,872.8 | hybrid | 217.49 | 84.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 953 | 1,524,800 | 483.1 | 1,635.1 | 3,590.6 | hybrid | 237.24 | 85.2% | link_latency |

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
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x107 | DeepSeek-V4-Flash-0731 | 107 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x36 | DeepSeek-V4-Flash-0731 | 36 | tensor | rom_package_ucie | rom_board_serdes | 172 | 41.00 us | 2,439.0 tok/s | 24,390.2 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 9 on rom_board_serdes (traversals 4.4) = 38.88 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x108 | DeepSeek-V4-Flash-0731 | 108 | hybrid | rom_package_ucie | rom_board_serdes | 112 | 4.83 us | 20,684.2 tok/s | 206,841.6 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 26 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.72 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x106 | DeepSeek-V4-Flash-0731 | 106 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4-Flash-0731 | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x40 | DeepSeek-V4-Flash-0731 | 40 | tensor | nvlink5 | infiniband_ndr | 172 | 591.43 us | 169.1 tok/s | 1,690.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 382.98 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x63 | DeepSeek-V4-Flash-0731 | 63 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279 | DeepSeek-V4-Flash-0731 | 279 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x279 | DeepSeek-V4-Flash-0731 | 279 | tensor | rom_package_ucie | rom_board_serdes | 172 | 154.63 us | 646.7 tok/s | 6,466.9 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 70 on rom_board_serdes (traversals 17.6) = 152.52 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | DeepSeek-V4-Flash-0731 | 279 | hybrid | rom_package_ucie | rom_board_serdes | 128 | 6.51 us | 15,367.0 tok/s | 153,670.4 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 42 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.39 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x279 | DeepSeek-V4-Flash-0731 | 279 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | DeepSeek-V4-Flash-0731 | 33 | pipeline | on_wafer_n5 | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-tensor-x279 | DeepSeek-V4-Flash-0731 | 279 | tensor | nvlink5 | infiniband_ndr | 172 | 598.68 us | 167.0 tok/s | 1,670.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 35 on infiniband_ndr (traversals 2.0) = 390.22 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x33 | DeepSeek-V4-Flash-0731 | 33 | tensor | on_wafer_n5 | rom_wafer_serdes | 172 | 260.49 us | 383.9 tok/s | 3,838.9 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us; 86 x all_reduce span 33 on rom_wafer_serdes (traversals 11.0) = 94.94 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x279 | DeepSeek-V4-Flash-0731 | 279 | hybrid | nvlink5 | infiniband_ndr | 120 | 283.05 us | 353.3 tok/s | 3,533.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 34 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 74.59 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33 | DeepSeek-V4-Flash-0731 | 33 | hybrid | on_wafer_n5 | rom_wafer_serdes | 118 | 168.79 us | 592.4 tok/s | 5,924.4 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us; 32 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 3.24 us |
| DSV4-Flash/b200_sxm-x9-pipeline | DeepSeek-V4-Flash-0731 | 9 | pipeline | nvlink5 | infiniband_ndr | 8 | 10.66 us | 9,383.0 tok/s | 93,830.1 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.46 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x9-tensor | DeepSeek-V4-Flash-0731 | 9 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x9-hybrid | DeepSeek-V4-Flash-0731 | 9 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x9-nvl72-tensor | DeepSeek-V4-Flash-0731 | 9 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.49 us | 479.6 tok/s | 4,796.5 tok/s | 86 x all_reduce span 9 on nvlink5_nvl72 (traversals 2.0) = 208.49 us |
| DSV4-Flash/b200_sxm-x9-expert | DeepSeek-V4-Flash-0731 | 9 | expert | nvlink5 | infiniband_ndr | 172 | 392.43 us | 254.8 tok/s | 2,548.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 183.97 us |
| DSV4-Flash/b200_sxm-x9-nvl72-expert | DeepSeek-V4-Flash-0731 | 9 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.21 us | 320.3 tok/s | 3,203.0 tok/s | 86 x all_reduce span 9 on nvlink5_nvl72 (traversals 2.0) = 208.49 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.72 us |
| DSV4-Flash/b200_sxm-x11-pipeline | DeepSeek-V4-Flash-0731 | 11 | pipeline | nvlink5 | infiniband_ndr | 10 | 13.08 us | 7,647.7 tok/s | 76,477.4 tok/s | 9 x point_to_point span 2 on nvlink5 (traversals 1.0) = 10.88 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x11-tensor | DeepSeek-V4-Flash-0731 | 11 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x11-hybrid | DeepSeek-V4-Flash-0731 | 11 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x11-nvl72-tensor | DeepSeek-V4-Flash-0731 | 11 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.53 us | 479.5 tok/s | 4,795.4 tok/s | 86 x all_reduce span 11 on nvlink5_nvl72 (traversals 2.0) = 208.53 us |
| DSV4-Flash/b200_sxm-x11-expert | DeepSeek-V4-Flash-0731 | 11 | expert | nvlink5 | infiniband_ndr | 172 | 390.72 us | 255.9 tok/s | 2,559.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 182.27 us |
| DSV4-Flash/b200_sxm-x11-nvl72-expert | DeepSeek-V4-Flash-0731 | 11 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.16 us | 320.3 tok/s | 3,203.5 tok/s | 86 x all_reduce span 11 on nvlink5_nvl72 (traversals 2.0) = 208.53 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.63 us |
| DSV4-Flash/b200_sxm-x12-pipeline | DeepSeek-V4-Flash-0731 | 12 | pipeline | nvlink5 | infiniband_ndr | 11 | 14.28 us | 7,000.4 tok/s | 70,004.2 tok/s | 10 x point_to_point span 2 on nvlink5 (traversals 1.0) = 12.09 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x12-tensor | DeepSeek-V4-Flash-0731 | 12 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x12-hybrid | DeepSeek-V4-Flash-0731 | 12 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x12-nvl72-tensor | DeepSeek-V4-Flash-0731 | 12 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.55 us | 479.5 tok/s | 4,795.0 tok/s | 86 x all_reduce span 12 on nvlink5_nvl72 (traversals 2.0) = 208.55 us |
| DSV4-Flash/b200_sxm-x12-expert | DeepSeek-V4-Flash-0731 | 12 | expert | nvlink5 | infiniband_ndr | 172 | 390.08 us | 256.4 tok/s | 2,563.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 181.63 us |
| DSV4-Flash/b200_sxm-x12-nvl72-expert | DeepSeek-V4-Flash-0731 | 12 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.14 us | 320.4 tok/s | 3,203.6 tok/s | 86 x all_reduce span 12 on nvlink5_nvl72 (traversals 2.0) = 208.55 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.59 us |
| DSV4-Flash/b200_sxm-x17-pipeline | DeepSeek-V4-Flash-0731 | 17 | pipeline | nvlink5 | infiniband_ndr | 16 | 21.32 us | 4,691.5 tok/s | 46,915.1 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x17-tensor | DeepSeek-V4-Flash-0731 | 17 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x17-hybrid | DeepSeek-V4-Flash-0731 | 17 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x17-nvl72-tensor | DeepSeek-V4-Flash-0731 | 17 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.61 us | 479.4 tok/s | 4,793.6 tok/s | 86 x all_reduce span 17 on nvlink5_nvl72 (traversals 2.0) = 208.61 us |
| DSV4-Flash/b200_sxm-x17-expert | DeepSeek-V4-Flash-0731 | 17 | expert | nvlink5 | infiniband_ndr | 172 | 386.98 us | 258.4 tok/s | 2,584.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 179.55 us |
| DSV4-Flash/b200_sxm-x17-nvl72-expert | DeepSeek-V4-Flash-0731 | 17 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.09 us | 320.4 tok/s | 3,204.2 tok/s | 86 x all_reduce span 17 on nvlink5_nvl72 (traversals 2.0) = 208.61 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.48 us |
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
| DSV4-Flash/b200_sxm-x20-pipeline | DeepSeek-V4-Flash-0731 | 20 | pipeline | nvlink5 | infiniband_ndr | 19 | 24.94 us | 4,009.2 tok/s | 40,092.3 tok/s | 17 x point_to_point span 2 on nvlink5 (traversals 1.0) = 20.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x20-tensor | DeepSeek-V4-Flash-0731 | 20 | tensor | nvlink5 | infiniband_ndr | 172 | 585.80 us | 170.7 tok/s | 1,707.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x20-hybrid | DeepSeek-V4-Flash-0731 | 20 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.84 us | 469.8 tok/s | 4,698.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x20-nvl72-tensor | DeepSeek-V4-Flash-0731 | 20 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.63 us | 479.3 tok/s | 4,793.2 tok/s | 86 x all_reduce span 20 on nvlink5_nvl72 (traversals 2.0) = 208.63 us |
| DSV4-Flash/b200_sxm-x20-expert | DeepSeek-V4-Flash-0731 | 20 | expert | nvlink5 | infiniband_ndr | 172 | 386.23 us | 258.9 tok/s | 2,589.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 178.81 us |
| DSV4-Flash/b200_sxm-x20-nvl72-expert | DeepSeek-V4-Flash-0731 | 20 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.07 us | 320.4 tok/s | 3,204.5 tok/s | 86 x all_reduce span 20 on nvlink5_nvl72 (traversals 2.0) = 208.63 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.43 us |
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
| DSV4-Flash/b200_sxm-x25-pipeline | DeepSeek-V4-Flash-0731 | 25 | pipeline | nvlink5 | infiniband_ndr | 24 | 31.97 us | 3,127.7 tok/s | 31,276.7 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x25-tensor | DeepSeek-V4-Flash-0731 | 25 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x25-hybrid | DeepSeek-V4-Flash-0731 | 25 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x25-nvl72-tensor | DeepSeek-V4-Flash-0731 | 25 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.65 us | 479.3 tok/s | 4,792.6 tok/s | 86 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 208.65 us |
| DSV4-Flash/b200_sxm-x25-expert | DeepSeek-V4-Flash-0731 | 25 | expert | nvlink5 | infiniband_ndr | 172 | 385.05 us | 259.7 tok/s | 2,597.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.96 us |
| DSV4-Flash/b200_sxm-x25-nvl72-expert | DeepSeek-V4-Flash-0731 | 25 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.04 us | 320.5 tok/s | 3,204.7 tok/s | 86 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 208.65 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.39 us |
| DSV4-Flash/b200_sxm-x26-pipeline | DeepSeek-V4-Flash-0731 | 26 | pipeline | nvlink5 | infiniband_ndr | 25 | 33.18 us | 3,013.7 tok/s | 30,137.0 tok/s | 22 x point_to_point span 2 on nvlink5 (traversals 1.0) = 26.60 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x26-tensor | DeepSeek-V4-Flash-0731 | 26 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x26-hybrid | DeepSeek-V4-Flash-0731 | 26 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x26-nvl72-tensor | DeepSeek-V4-Flash-0731 | 26 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.66 us | 479.3 tok/s | 4,792.5 tok/s | 86 x all_reduce span 26 on nvlink5_nvl72 (traversals 2.0) = 208.66 us |
| DSV4-Flash/b200_sxm-x26-expert | DeepSeek-V4-Flash-0731 | 26 | expert | nvlink5 | infiniband_ndr | 172 | 384.92 us | 259.8 tok/s | 2,598.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.83 us |
| DSV4-Flash/b200_sxm-x26-nvl72-expert | DeepSeek-V4-Flash-0731 | 26 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.04 us | 320.5 tok/s | 3,204.7 tok/s | 86 x all_reduce span 26 on nvlink5_nvl72 (traversals 2.0) = 208.66 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.38 us |
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
| DSV4-Flash/b200_sxm-x32-pipeline | DeepSeek-V4-Flash-0731 | 32 | pipeline | nvlink5 | infiniband_ndr | 31 | 40.44 us | 2,473.0 tok/s | 24,730.2 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.85 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x32-tensor | DeepSeek-V4-Flash-0731 | 32 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x32-hybrid | DeepSeek-V4-Flash-0731 | 32 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x32-nvl72-tensor | DeepSeek-V4-Flash-0731 | 32 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.67 us | 479.2 tok/s | 4,792.1 tok/s | 86 x all_reduce span 32 on nvlink5_nvl72 (traversals 2.0) = 208.67 us |
| DSV4-Flash/b200_sxm-x32-expert | DeepSeek-V4-Flash-0731 | 32 | expert | nvlink5 | infiniband_ndr | 172 | 384.14 us | 260.3 tok/s | 2,603.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.91 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.22 us |
| DSV4-Flash/b200_sxm-x32-nvl72-expert | DeepSeek-V4-Flash-0731 | 32 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.02 us | 320.5 tok/s | 3,204.9 tok/s | 86 x all_reduce span 32 on nvlink5_nvl72 (traversals 2.0) = 208.67 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.35 us |
| DSV4-Flash/b200_sxm-x33-pipeline | DeepSeek-V4-Flash-0731 | 33 | pipeline | nvlink5 | infiniband_ndr | 32 | 42.63 us | 2,345.8 tok/s | 23,457.5 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.85 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/b200_sxm-x33-tensor | DeepSeek-V4-Flash-0731 | 33 | tensor | nvlink5 | infiniband_ndr | 172 | 591.43 us | 169.1 tok/s | 1,690.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 382.98 us |
| DSV4-Flash/b200_sxm-x33-hybrid | DeepSeek-V4-Flash-0731 | 33 | hybrid | nvlink5 | infiniband_ndr | 90 | 217.23 us | 460.3 tok/s | 4,603.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| DSV4-Flash/b200_sxm-x33-nvl72-tensor | DeepSeek-V4-Flash-0731 | 33 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.68 us | 479.2 tok/s | 4,792.1 tok/s | 86 x all_reduce span 33 on nvlink5_nvl72 (traversals 2.0) = 208.68 us |
| DSV4-Flash/b200_sxm-x33-expert | DeepSeek-V4-Flash-0731 | 33 | expert | nvlink5 | infiniband_ndr | 172 | 384.06 us | 260.4 tok/s | 2,603.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.91 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.14 us |
| DSV4-Flash/b200_sxm-x33-nvl72-expert | DeepSeek-V4-Flash-0731 | 33 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.02 us | 320.5 tok/s | 3,204.9 tok/s | 86 x all_reduce span 33 on nvlink5_nvl72 (traversals 2.0) = 208.68 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.34 us |
| DSV4-Flash/b200_sxm-x46-pipeline | DeepSeek-V4-Flash-0731 | 46 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x46-tensor | DeepSeek-V4-Flash-0731 | 46 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x46-hybrid | DeepSeek-V4-Flash-0731 | 46 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x46-nvl72-tensor | DeepSeek-V4-Flash-0731 | 46 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.70 us | 479.2 tok/s | 4,791.6 tok/s | 86 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 208.70 us |
| DSV4-Flash/b200_sxm-x46-expert | DeepSeek-V4-Flash-0731 | 46 | expert | nvlink5 | infiniband_ndr | 172 | 383.23 us | 260.9 tok/s | 2,609.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.81 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.42 us |
| DSV4-Flash/b200_sxm-x46-nvl72-expert | DeepSeek-V4-Flash-0731 | 46 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.00 us | 320.5 tok/s | 3,205.1 tok/s | 86 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 208.70 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.30 us |
| DSV4-Flash/b200_sxm-x54-pipeline | DeepSeek-V4-Flash-0731 | 54 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x54-tensor | DeepSeek-V4-Flash-0731 | 54 | tensor | nvlink5 | infiniband_ndr | 172 | 593.85 us | 168.4 tok/s | 1,683.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 385.39 us |
| DSV4-Flash/b200_sxm-x54-hybrid | DeepSeek-V4-Flash-0731 | 54 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.62 us | 451.2 tok/s | 4,512.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| DSV4-Flash/b200_sxm-x54-nvl72-tensor | DeepSeek-V4-Flash-0731 | 54 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.70 us | 479.1 tok/s | 4,791.5 tok/s | 86 x all_reduce span 54 on nvlink5_nvl72 (traversals 2.0) = 208.70 us |
| DSV4-Flash/b200_sxm-x54-expert | DeepSeek-V4-Flash-0731 | 54 | expert | nvlink5 | infiniband_ndr | 172 | 382.89 us | 261.2 tok/s | 2,611.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.74 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.15 us |
| DSV4-Flash/b200_sxm-x54-nvl72-expert | DeepSeek-V4-Flash-0731 | 54 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.2 tok/s | 86 x all_reduce span 54 on nvlink5_nvl72 (traversals 2.0) = 208.70 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.29 us |
| DSV4-Flash/b200_sxm-x55-pipeline | DeepSeek-V4-Flash-0731 | 55 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x55-tensor | DeepSeek-V4-Flash-0731 | 55 | tensor | nvlink5 | infiniband_ndr | 172 | 593.85 us | 168.4 tok/s | 1,683.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 385.39 us |
| DSV4-Flash/b200_sxm-x55-hybrid | DeepSeek-V4-Flash-0731 | 55 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.62 us | 451.2 tok/s | 4,512.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| DSV4-Flash/b200_sxm-x55-nvl72-tensor | DeepSeek-V4-Flash-0731 | 55 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.71 us | 479.1 tok/s | 4,791.4 tok/s | 86 x all_reduce span 55 on nvlink5_nvl72 (traversals 2.0) = 208.71 us |
| DSV4-Flash/b200_sxm-x55-expert | DeepSeek-V4-Flash-0731 | 55 | expert | nvlink5 | infiniband_ndr | 172 | 382.86 us | 261.2 tok/s | 2,611.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.74 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.12 us |
| DSV4-Flash/b200_sxm-x55-nvl72-expert | DeepSeek-V4-Flash-0731 | 55 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.2 tok/s | 86 x all_reduce span 55 on nvlink5_nvl72 (traversals 2.0) = 208.71 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.29 us |
| DSV4-Flash/b200_sxm-x58-pipeline | DeepSeek-V4-Flash-0731 | 58 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x58-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x58-hybrid | DeepSeek-V4-Flash-0731 | 58 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x58-nvl72-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.71 us | 479.1 tok/s | 4,791.4 tok/s | 86 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 208.71 us |
| DSV4-Flash/b200_sxm-x58-expert | DeepSeek-V4-Flash-0731 | 58 | expert | nvlink5 | infiniband_ndr | 172 | 382.73 us | 261.3 tok/s | 2,612.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.69 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.04 us |
| DSV4-Flash/b200_sxm-x58-nvl72-expert | DeepSeek-V4-Flash-0731 | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.2 tok/s | 86 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 208.71 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.28 us |
| DSV4-Flash/b200_sxm-x61-pipeline | DeepSeek-V4-Flash-0731 | 61 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x61-tensor | DeepSeek-V4-Flash-0731 | 61 | tensor | nvlink5 | infiniband_ndr | 172 | 594.60 us | 168.2 tok/s | 1,681.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 386.15 us |
| DSV4-Flash/b200_sxm-x61-hybrid | DeepSeek-V4-Flash-0731 | 61 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.81 us | 446.8 tok/s | 4,468.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| DSV4-Flash/b200_sxm-x61-nvl72-tensor | DeepSeek-V4-Flash-0731 | 61 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.71 us | 479.1 tok/s | 4,791.3 tok/s | 86 x all_reduce span 61 on nvlink5_nvl72 (traversals 2.0) = 208.71 us |
| DSV4-Flash/b200_sxm-x61-expert | DeepSeek-V4-Flash-0731 | 61 | expert | nvlink5 | infiniband_ndr | 172 | 382.66 us | 261.3 tok/s | 2,613.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.69 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.97 us |
| DSV4-Flash/b200_sxm-x61-nvl72-expert | DeepSeek-V4-Flash-0731 | 61 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.3 tok/s | 86 x all_reduce span 61 on nvlink5_nvl72 (traversals 2.0) = 208.71 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.28 us |
| DSV4-Flash/b200_sxm-x87-pipeline | DeepSeek-V4-Flash-0731 | 87 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x87-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink5 | infiniband_ndr | 172 | 596.04 us | 167.8 tok/s | 1,677.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 387.59 us |
| DSV4-Flash/b200_sxm-x87-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink5 | infiniband_ndr | 96 | 230.39 us | 434.0 tok/s | 4,340.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| DSV4-Flash/b200_sxm-x87-nvl72-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x87-expert | DeepSeek-V4-Flash-0731 | 87 | expert | nvlink5 | infiniband_ndr | 172 | 382.16 us | 261.7 tok/s | 2,616.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.61 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.55 us |
| DSV4-Flash/b200_sxm-x87-nvl72-expert | DeepSeek-V4-Flash-0731 | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 384.27 us | 260.2 tok/s | 2,602.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.55 us |
| DSV4-Flash/b200_sxm-x116-pipeline | DeepSeek-V4-Flash-0731 | 116 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x116-tensor | DeepSeek-V4-Flash-0731 | 116 | tensor | nvlink5 | infiniband_ndr | 172 | 597.07 us | 167.5 tok/s | 1,674.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 388.61 us |
| DSV4-Flash/b200_sxm-x116-hybrid | DeepSeek-V4-Flash-0731 | 116 | hybrid | nvlink5 | infiniband_ndr | 100 | 239.17 us | 418.1 tok/s | 4,181.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| DSV4-Flash/b200_sxm-x116-nvl72-tensor | DeepSeek-V4-Flash-0731 | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x116-expert | DeepSeek-V4-Flash-0731 | 116 | expert | nvlink5 | infiniband_ndr | 172 | 381.86 us | 261.9 tok/s | 2,618.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.55 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.31 us |
| DSV4-Flash/b200_sxm-x116-nvl72-expert | DeepSeek-V4-Flash-0731 | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 384.02 us | 260.4 tok/s | 2,604.0 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.31 us |
| DSV4-Flash/b200_sxm-x142-pipeline | DeepSeek-V4-Flash-0731 | 142 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x142-tensor | DeepSeek-V4-Flash-0731 | 142 | tensor | nvlink5 | infiniband_ndr | 172 | 597.54 us | 167.4 tok/s | 1,673.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 18 on infiniband_ndr (traversals 2.0) = 389.08 us |
| DSV4-Flash/b200_sxm-x142-hybrid | DeepSeek-V4-Flash-0731 | 142 | hybrid | nvlink5 | infiniband_ndr | 103 | 245.75 us | 406.9 tok/s | 4,069.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 37.30 us |
| DSV4-Flash/b200_sxm-x142-nvl72-tensor | DeepSeek-V4-Flash-0731 | 142 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 579.01 us | 172.7 tok/s | 1,727.1 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x142-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 142 | hybrid | nvlink5_nvl72 | infiniband_ndr | 87 | 210.91 us | 474.1 tok/s | 4,741.4 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x142-expert | DeepSeek-V4-Flash-0731 | 142 | expert | nvlink5 | infiniband_ndr | 172 | 381.70 us | 262.0 tok/s | 2,619.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.52 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.18 us |
| DSV4-Flash/b200_sxm-x142-nvl72-expert | DeepSeek-V4-Flash-0731 | 142 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 383.89 us | 260.5 tok/s | 2,604.9 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.18 us |
| DSV4-Flash/b200_sxm-x173-pipeline | DeepSeek-V4-Flash-0731 | 173 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x173-tensor | DeepSeek-V4-Flash-0731 | 173 | tensor | nvlink5 | infiniband_ndr | 172 | 597.96 us | 167.2 tok/s | 1,672.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 389.51 us |
| DSV4-Flash/b200_sxm-x173-hybrid | DeepSeek-V4-Flash-0731 | 173 | hybrid | nvlink5 | infiniband_ndr | 107 | 254.53 us | 392.9 tok/s | 3,928.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| DSV4-Flash/b200_sxm-x173-nvl72-tensor | DeepSeek-V4-Flash-0731 | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 586.06 us | 170.6 tok/s | 1,706.3 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 88 | 213.10 us | 469.3 tok/s | 4,692.6 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x173-expert | DeepSeek-V4-Flash-0731 | 173 | expert | nvlink5 | infiniband_ndr | 172 | 381.57 us | 262.1 tok/s | 2,620.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.50 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.07 us |
| DSV4-Flash/b200_sxm-x173-nvl72-expert | DeepSeek-V4-Flash-0731 | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 382.63 us | 261.4 tok/s | 2,613.5 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 207.56 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.07 us |
| DSV4-Flash/b200_sxm-x176-pipeline | DeepSeek-V4-Flash-0731 | 176 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x176-tensor | DeepSeek-V4-Flash-0731 | 176 | tensor | nvlink5 | infiniband_ndr | 172 | 597.96 us | 167.2 tok/s | 1,672.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 389.51 us |
| DSV4-Flash/b200_sxm-x176-hybrid | DeepSeek-V4-Flash-0731 | 176 | hybrid | nvlink5 | infiniband_ndr | 107 | 254.53 us | 392.9 tok/s | 3,928.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| DSV4-Flash/b200_sxm-x176-nvl72-tensor | DeepSeek-V4-Flash-0731 | 176 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 586.06 us | 170.6 tok/s | 1,706.3 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x176-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 176 | hybrid | nvlink5_nvl72 | infiniband_ndr | 88 | 213.10 us | 469.3 tok/s | 4,692.6 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x176-expert | DeepSeek-V4-Flash-0731 | 176 | expert | nvlink5 | infiniband_ndr | 172 | 381.55 us | 262.1 tok/s | 2,620.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.49 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.06 us |
| DSV4-Flash/b200_sxm-x176-nvl72-expert | DeepSeek-V4-Flash-0731 | 176 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 382.62 us | 261.4 tok/s | 2,613.6 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 207.56 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.06 us |
| DSV4-Flash/b200_sxm-x178-pipeline | DeepSeek-V4-Flash-0731 | 178 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x178-tensor | DeepSeek-V4-Flash-0731 | 178 | tensor | nvlink5 | infiniband_ndr | 172 | 598.05 us | 167.2 tok/s | 1,672.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 23 on infiniband_ndr (traversals 2.0) = 389.59 us |
| DSV4-Flash/b200_sxm-x178-hybrid | DeepSeek-V4-Flash-0731 | 178 | hybrid | nvlink5 | infiniband_ndr | 108 | 256.72 us | 389.5 tok/s | 3,895.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 22 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.26 us |
| DSV4-Flash/b200_sxm-x178-nvl72-tensor | DeepSeek-V4-Flash-0731 | 178 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 586.06 us | 170.6 tok/s | 1,706.3 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 377.34 us |
| DSV4-Flash/b200_sxm-x178-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 178 | hybrid | nvlink5_nvl72 | infiniband_ndr | 88 | 213.10 us | 469.3 tok/s | 4,692.6 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| DSV4-Flash/b200_sxm-x178-expert | DeepSeek-V4-Flash-0731 | 178 | expert | nvlink5 | infiniband_ndr | 172 | 381.55 us | 262.1 tok/s | 2,620.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.49 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.05 us |
| DSV4-Flash/b200_sxm-x178-nvl72-expert | DeepSeek-V4-Flash-0731 | 178 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 382.61 us | 261.4 tok/s | 2,613.6 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 207.56 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 175.05 us |
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
| DSV4-Flash/b200_sxm-x953-pipeline | DeepSeek-V4-Flash-0731 | 953 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x953-tensor | DeepSeek-V4-Flash-0731 | 953 | tensor | nvlink5 | infiniband_ndr | 172 | 948.69 us | 105.4 tok/s | 1,054.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 120 on infiniband_ndr (traversals 4.0) = 740.24 us |
| DSV4-Flash/b200_sxm-x953-hybrid | DeepSeek-V4-Flash-0731 | 953 | hybrid | nvlink5 | infiniband_ndr | 128 | 300.60 us | 332.7 tok/s | 3,326.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 42 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 92.14 us |
| DSV4-Flash/b200_sxm-x953-nvl72-tensor | DeepSeek-V4-Flash-0731 | 953 | tensor | nvlink5_nvl72 | infiniband_ndr | 172 | 597.13 us | 167.5 tok/s | 1,674.7 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 86 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 388.41 us |
| DSV4-Flash/b200_sxm-x953-nvl72-hybrid | DeepSeek-V4-Flash-0731 | 953 | hybrid | nvlink5_nvl72 | infiniband_ndr | 99 | 237.24 us | 421.5 tok/s | 4,215.2 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 208.72 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 28.52 us |
| DSV4-Flash/b200_sxm-x953-expert | DeepSeek-V4-Flash-0731 | 953 | expert | nvlink5 | infiniband_ndr | 172 | 381.09 us | 262.4 tok/s | 2,624.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.42 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.67 us |
| DSV4-Flash/b200_sxm-x953-nvl72-expert | DeepSeek-V4-Flash-0731 | 953 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 381.25 us | 262.3 tok/s | 2,623.0 tok/s | 86 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 206.58 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 174.67 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 1 | array | array | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x52-romfill | 42,380 | 12,076.8 | 0.285 | 12,076.8 (42,380) | 5,403.4 (46,225) | 0.45x | link_latency |
| DeepSeek-V4-Flash-0731 | 2 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 6,300.3 | 0.028 | 6,300.3 (227,385) | 4,447.5 (1,525,425) | 0.71x | compute |
| DeepSeek-V4-Flash-0731 | 4 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 6,300.3 | 0.028 | 6,300.3 (227,385) | 4,447.5 (1,525,425) | 0.71x | compute |
| DeepSeek-V4-Flash-0731 | 8 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 6,300.3 | 0.028 | 6,300.3 (227,385) | 4,447.5 (1,525,425) | 0.71x | compute |
| DeepSeek-V4-Flash-0731 | 16 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 6,300.3 | 0.028 | 6,300.3 (227,385) | 4,447.5 (1,525,425) | 0.71x | compute |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 6,300.3 | 0.028 | 6,300.3 (227,385) | 4,447.5 (1,525,425) | 0.71x | compute |
| DeepSeek-V4-Flash-0731 | 64 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-romfill | 227,385 | 6,300.3 | 0.028 | 6,300.3 (227,385) | 3,760.8 (1,525,425) | 0.60x | compute |
| DeepSeek-V4-Flash-0731 | 256 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 2,274.3 | 0.008 | 2,274.3 (277,100) | 1,922.4 (1,525,425) | 0.85x | compute |
| DeepSeek-V4-Flash-0731 | 1024 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33 | 1,525,425 | 650.5 | 0.000 | 590.8 (277,100) | 650.5 (1,525,425) | 1.10x | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 183.9 | 0.000 | 148.6 (277,100) | 183.9 (1,525,425) | 1.24x | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | sram | 387,056.0 | 26,106.7 | 26,106.7 | 14.83x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 387,056.0 | 26,106.7 | 26,106.7 | 14.83x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 387,056.0 | 26,106.7 | 26,106.7 | 14.83x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 387,056.0 | 26,106.7 | 31,812.2 | 14.83x | 1.22x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | sram | 387,056.0 | 26,106.7 | 53,200.4 | 14.83x | 2.04x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | sram | 387,056.0 | 26,106.7 | 86,634.3 | 14.83x | 3.32x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | sram | 387,056.0 | 26,106.7 | 131,091.1 | 14.83x | 5.02x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | sram | 588,553.3 | 26,106.7 | 287,586.5 | 22.54x | 11.02x | thermal | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 666,098.5 | 26,106.7 | 486,190.6 | 25.51x | 18.62x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 730,670.2 | 26,110.6 | 577,616.0 | 27.98x | 22.12x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 750,480.0 | 750,480.0 | 750,480.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 750,480.0 | 750,480.0 | 750,480.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 750,480.0 | 750,480.0 | 750,480.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 750,480.0 | 750,480.0 | 750,480.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 750,480.0 | 750,480.0 | 750,480.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 750,480.0 | 750,480.0 | 750,480.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 750,480.0 | 750,480.0 | 750,480.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 750,480.0 | 750,480.0 | 750,480.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 750,480.0 | 750,480.0 | 750,480.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 753,373.2 | 753,373.2 | 753,373.2 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 387,056.0 | 0.254 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream | 1,525,425 | 1.00 | 1.00 | 26,106.7 | 0.017 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion | 1,525,425 | 1.00 | 1.00 | 26,106.7 | 0.017 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 387,056.0 | 0.254 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream | 1,525,425 | 1.00 | 1.00 | 26,106.7 | 0.017 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion | 1,525,425 | 1.00 | 1.00 | 26,106.7 | 0.017 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 387,056.0 | 0.254 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream | 1,525,425 | 1.00 | 1.00 | 26,106.7 | 0.017 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion | 1,525,425 | 1.00 | 1.00 | 26,106.7 | 0.017 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 387,056.0 | 0.254 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream | 1,525,425 | 1.00 | 1.00 | 26,106.7 | 0.017 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.13 | 31,812.2 | 0.688 | link_latency | 0.08x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 387,056.0 | 0.254 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream | 1,525,425 | 1.00 | 1.00 | 26,106.7 | 0.017 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x279-perregion | 227,385 | 1.00 | 2.88 | 53,200.4 | 0.234 | link_latency | 0.14x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 387,056.0 | 0.254 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream | 1,525,425 | 1.00 | 1.00 | 26,106.7 | 0.017 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x279-perregion | 227,385 | 1.00 | 4.03 | 86,634.3 | 0.381 | link_latency | 0.22x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 387,056.0 | 0.254 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream | 1,525,425 | 1.00 | 1.00 | 26,106.7 | 0.017 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x279-perregion | 227,385 | 1.00 | 5.83 | 131,091.1 | 0.577 | link_latency | 0.34x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.94x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x349 | 284,435 | 1.00 | 1.00 | 588,553.3 | 2.069 | thermal | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.28x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream | 1,525,425 | 1.00 | 1.00 | 26,106.7 | 0.017 | weight_read | 0.04x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.28x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x33-perregion | 1,525,425 | 1.00 | 13.84 | 287,586.5 | 0.189 | weight_read | 0.49x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.28x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33 | 1,525,425 | 1.00 | 1.00 | 666,098.5 | 0.437 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.13x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream | 1,525,425 | 1.00 | 1.00 | 26,106.7 | 0.017 | weight_read | 0.04x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.13x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x33-perregion | 1,525,425 | 1.00 | 38.75 | 486,190.6 | 0.319 | weight_read | 0.73x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 750,480.0 | 0.492 | kv_read | 1.13x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33 | 1,525,425 | 1.00 | 1.00 | 730,670.2 | 0.479 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 753,373.2 | 0.494 | kv_read | 1.03x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perstream | 227,385 | 1.00 | 14.68 | 26,110.6 | 0.115 | weight_read | 0.04x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 2.19 | 753,373.2 | 0.494 | kv_read | 1.03x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x33-perregion | 1,525,425 | 1.00 | 124.47 | 577,616.0 | 0.379 | kv_read | 0.79x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.17 | 753,373.2 | 0.494 | kv_read | 1.03x |

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
| DeepSeek-V4-Flash-0731 | 1 | 18 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 279 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 279 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 279 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | 279 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 279 | 3.67 | 1.032 | 1.497 | 1.45x |
| DeepSeek-V4-Flash-0731 | 4096 | 279 | 14.68 | 1.170 | 2.760 | 2.36x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 9 | 4.56 | 3.12 | 1.46x |
| DeepSeek-V4-Flash-0731 | 2 | 9 | 6.77 | 3.88 | 1.75x |
| DeepSeek-V4-Flash-0731 | 4 | 9 | 8.41 | 4.66 | 1.81x |
| DeepSeek-V4-Flash-0731 | 8 | 9 | 8.95 | 5.41 | 1.66x |
| DeepSeek-V4-Flash-0731 | 16 | 9 | 9.00 | 6.06 | 1.49x |
| DeepSeek-V4-Flash-0731 | 32 | 9 | 9.00 | 6.56 | 1.37x |
| DeepSeek-V4-Flash-0731 | 64 | 9 | 9.00 | 6.89 | 1.31x |
| DeepSeek-V4-Flash-0731 | 1 | 11 | 4.79 | 3.32 | 1.44x |
| DeepSeek-V4-Flash-0731 | 2 | 11 | 7.45 | 4.21 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 11 | 9.79 | 5.16 | 1.90x |
| DeepSeek-V4-Flash-0731 | 8 | 11 | 10.84 | 6.09 | 1.78x |
| DeepSeek-V4-Flash-0731 | 16 | 11 | 11.00 | 6.93 | 1.59x |
| DeepSeek-V4-Flash-0731 | 32 | 11 | 11.00 | 7.60 | 1.45x |
| DeepSeek-V4-Flash-0731 | 64 | 11 | 11.00 | 8.04 | 1.37x |
| DeepSeek-V4-Flash-0731 | 1 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 2 | 12 | 7.72 | 4.35 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 12 | 10.40 | 5.38 | 1.93x |
| DeepSeek-V4-Flash-0731 | 8 | 12 | 11.74 | 6.41 | 1.83x |
| DeepSeek-V4-Flash-0731 | 16 | 12 | 11.99 | 7.34 | 1.63x |
| DeepSeek-V4-Flash-0731 | 32 | 12 | 12.00 | 8.08 | 1.48x |
| DeepSeek-V4-Flash-0731 | 64 | 12 | 12.00 | 8.59 | 1.40x |
| DeepSeek-V4-Flash-0731 | 256 | 12 | 12.00 | 8.89 | 1.35x |
| DeepSeek-V4-Flash-0731 | 1 | 17 | 5.18 | 3.76 | 1.38x |
| DeepSeek-V4-Flash-0731 | 2 | 17 | 8.72 | 4.94 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 17 | 12.83 | 6.31 | 2.03x |
| DeepSeek-V4-Flash-0731 | 8 | 17 | 15.84 | 7.75 | 2.04x |
| DeepSeek-V4-Flash-0731 | 16 | 17 | 16.87 | 9.12 | 1.85x |
| DeepSeek-V4-Flash-0731 | 32 | 17 | 17.00 | 10.27 | 1.65x |
| DeepSeek-V4-Flash-0731 | 64 | 17 | 17.00 | 11.07 | 1.54x |
| DeepSeek-V4-Flash-0731 | 256 | 17 | 17.00 | 11.55 | 1.47x |
| DeepSeek-V4-Flash-0731 | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 8.86 | 5.03 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 13.21 | 6.47 | 2.04x |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 16.56 | 7.99 | 2.07x |
| DeepSeek-V4-Flash-0731 | 16 | 18 | 17.82 | 9.44 | 1.89x |
| DeepSeek-V4-Flash-0731 | 32 | 18 | 17.99 | 10.67 | 1.69x |
| DeepSeek-V4-Flash-0731 | 64 | 18 | 18.00 | 11.53 | 1.56x |
| DeepSeek-V4-Flash-0731 | 256 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 2 | 19 | 8.99 | 5.12 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 19 | 13.57 | 6.62 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 19 | 17.26 | 8.21 | 2.10x |
| DeepSeek-V4-Flash-0731 | 16 | 19 | 18.76 | 9.75 | 1.92x |
| DeepSeek-V4-Flash-0731 | 32 | 19 | 18.99 | 11.05 | 1.72x |
| DeepSeek-V4-Flash-0731 | 64 | 19 | 19.00 | 11.97 | 1.59x |
| DeepSeek-V4-Flash-0731 | 256 | 19 | 19.00 | 12.53 | 1.52x |
| DeepSeek-V4-Flash-0731 | 1 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 2 | 20 | 9.11 | 5.21 | 1.75x |
| DeepSeek-V4-Flash-0731 | 4 | 20 | 13.91 | 6.76 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 20 | 17.93 | 8.43 | 2.13x |
| DeepSeek-V4-Flash-0731 | 16 | 20 | 19.68 | 10.04 | 1.96x |
| DeepSeek-V4-Flash-0731 | 32 | 20 | 19.98 | 11.42 | 1.75x |
| DeepSeek-V4-Flash-0731 | 64 | 20 | 20.00 | 12.40 | 1.61x |
| DeepSeek-V4-Flash-0731 | 256 | 20 | 20.00 | 13.00 | 1.54x |
| DeepSeek-V4-Flash-0731 | 1 | 23 | 5.38 | 4.06 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 23 | 9.42 | 5.44 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 23 | 14.79 | 7.16 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 23 | 19.78 | 9.03 | 2.19x |
| DeepSeek-V4-Flash-0731 | 16 | 23 | 22.37 | 10.88 | 2.06x |
| DeepSeek-V4-Flash-0731 | 32 | 23 | 22.95 | 12.49 | 1.84x |
| DeepSeek-V4-Flash-0731 | 64 | 23 | 23.00 | 13.64 | 1.69x |
| DeepSeek-V4-Flash-0731 | 256 | 23 | 23.00 | 14.35 | 1.60x |
| DeepSeek-V4-Flash-0731 | 1 | 24 | 5.41 | 4.10 | 1.32x |
| DeepSeek-V4-Flash-0731 | 2 | 24 | 9.51 | 5.51 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 24 | 15.05 | 7.28 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 24 | 20.35 | 9.21 | 2.21x |
| DeepSeek-V4-Flash-0731 | 16 | 24 | 23.23 | 11.14 | 2.09x |
| DeepSeek-V4-Flash-0731 | 32 | 24 | 23.93 | 12.82 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 24 | 24.00 | 14.03 | 1.71x |
| DeepSeek-V4-Flash-0731 | 256 | 24 | 24.00 | 14.78 | 1.62x |
| DeepSeek-V4-Flash-0731 | 1 | 25 | 5.43 | 4.15 | 1.31x |
| DeepSeek-V4-Flash-0731 | 2 | 25 | 9.59 | 5.58 | 1.72x |
| DeepSeek-V4-Flash-0731 | 4 | 25 | 15.29 | 7.40 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 25 | 20.89 | 9.39 | 2.22x |
| DeepSeek-V4-Flash-0731 | 16 | 25 | 24.08 | 11.39 | 2.11x |
| DeepSeek-V4-Flash-0731 | 32 | 25 | 24.90 | 13.15 | 1.89x |
| DeepSeek-V4-Flash-0731 | 64 | 25 | 24.99 | 14.42 | 1.73x |
| DeepSeek-V4-Flash-0731 | 256 | 25 | 25.00 | 15.20 | 1.64x |
| DeepSeek-V4-Flash-0731 | 1 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 2 | 26 | 9.67 | 5.64 | 1.71x |
| DeepSeek-V4-Flash-0731 | 4 | 26 | 15.52 | 7.51 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 26 | 21.41 | 9.57 | 2.24x |
| DeepSeek-V4-Flash-0731 | 16 | 26 | 24.91 | 11.64 | 2.14x |
| DeepSeek-V4-Flash-0731 | 32 | 26 | 25.88 | 13.47 | 1.92x |
| DeepSeek-V4-Flash-0731 | 64 | 26 | 25.99 | 14.79 | 1.76x |
| DeepSeek-V4-Flash-0731 | 256 | 26 | 26.00 | 15.62 | 1.66x |
| DeepSeek-V4-Flash-0731 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 29 | 9.87 | 5.82 | 1.70x |
| DeepSeek-V4-Flash-0731 | 4 | 29 | 16.14 | 7.83 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 29 | 22.86 | 10.06 | 2.27x |
| DeepSeek-V4-Flash-0731 | 16 | 29 | 27.30 | 12.35 | 2.21x |
| DeepSeek-V4-Flash-0731 | 32 | 29 | 28.76 | 14.39 | 2.00x |
| DeepSeek-V4-Flash-0731 | 64 | 29 | 28.97 | 15.88 | 1.82x |
| DeepSeek-V4-Flash-0731 | 256 | 29 | 29.00 | 16.82 | 1.72x |
| DeepSeek-V4-Flash-0731 | 1 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 2 | 31 | 9.99 | 5.93 | 1.68x |
| DeepSeek-V4-Flash-0731 | 4 | 31 | 16.50 | 8.03 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 31 | 23.73 | 10.37 | 2.29x |
| DeepSeek-V4-Flash-0731 | 16 | 31 | 28.81 | 12.79 | 2.25x |
| DeepSeek-V4-Flash-0731 | 32 | 31 | 30.64 | 14.97 | 2.05x |
| DeepSeek-V4-Flash-0731 | 64 | 31 | 30.96 | 16.57 | 1.87x |
| DeepSeek-V4-Flash-0731 | 256 | 31 | 30.99 | 17.58 | 1.76x |
| DeepSeek-V4-Flash-0731 | 1 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4-Flash-0731 | 2 | 32 | 10.04 | 5.99 | 1.68x |
| DeepSeek-V4-Flash-0731 | 4 | 32 | 16.66 | 8.12 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 32 | 24.15 | 10.52 | 2.30x |
| DeepSeek-V4-Flash-0731 | 16 | 32 | 29.54 | 13.00 | 2.27x |
| DeepSeek-V4-Flash-0731 | 32 | 32 | 31.58 | 15.25 | 2.07x |
| DeepSeek-V4-Flash-0731 | 64 | 32 | 31.94 | 16.91 | 1.89x |
| DeepSeek-V4-Flash-0731 | 256 | 32 | 31.99 | 17.95 | 1.78x |
| DeepSeek-V4-Flash-0731 | 1 | 33 | 5.56 | 4.41 | 1.26x |
| DeepSeek-V4-Flash-0731 | 2 | 33 | 10.09 | 6.04 | 1.67x |
| DeepSeek-V4-Flash-0731 | 4 | 33 | 16.82 | 8.21 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 33 | 24.54 | 10.66 | 2.30x |
| DeepSeek-V4-Flash-0731 | 16 | 33 | 30.26 | 13.21 | 2.29x |
| DeepSeek-V4-Flash-0731 | 32 | 33 | 32.50 | 15.52 | 2.09x |
| DeepSeek-V4-Flash-0731 | 64 | 33 | 32.93 | 17.24 | 1.91x |
| DeepSeek-V4-Flash-0731 | 256 | 33 | 32.99 | 18.32 | 1.80x |
| DeepSeek-V4-Flash-0731 | 1 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 46 | 10.55 | 6.61 | 1.60x |
| DeepSeek-V4-Flash-0731 | 4 | 46 | 18.36 | 9.19 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 46 | 28.60 | 12.24 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 46 | 38.22 | 15.56 | 2.46x |
| DeepSeek-V4-Flash-0731 | 32 | 46 | 43.69 | 18.69 | 2.34x |
| DeepSeek-V4-Flash-0731 | 64 | 46 | 45.43 | 21.07 | 2.16x |
| DeepSeek-V4-Flash-0731 | 256 | 46 | 45.83 | 22.61 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1024 | 46 | 45.83 | 22.63 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1 | 54 | 5.73 | 4.85 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 54 | 10.74 | 6.89 | 1.56x |
| DeepSeek-V4-Flash-0731 | 4 | 54 | 18.98 | 9.65 | 1.97x |
| DeepSeek-V4-Flash-0731 | 8 | 54 | 30.38 | 13.02 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 54 | 42.08 | 16.75 | 2.51x |
| DeepSeek-V4-Flash-0731 | 32 | 54 | 49.76 | 20.33 | 2.45x |
| DeepSeek-V4-Flash-0731 | 64 | 54 | 52.71 | 23.10 | 2.28x |
| DeepSeek-V4-Flash-0731 | 256 | 54 | 53.54 | 24.90 | 2.15x |
| DeepSeek-V4-Flash-0731 | 1024 | 54 | 53.55 | 24.92 | 2.15x |
| DeepSeek-V4-Flash-0731 | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 55 | 10.76 | 6.93 | 1.55x |
| DeepSeek-V4-Flash-0731 | 4 | 55 | 19.05 | 9.71 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 55 | 30.58 | 13.11 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 55 | 42.52 | 16.89 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 55 | 50.48 | 20.52 | 2.46x |
| DeepSeek-V4-Flash-0731 | 64 | 55 | 53.60 | 23.34 | 2.30x |
| DeepSeek-V4-Flash-0731 | 256 | 55 | 54.49 | 25.18 | 2.16x |
| DeepSeek-V4-Flash-0731 | 1024 | 55 | 54.50 | 25.19 | 2.16x |
| DeepSeek-V4-Flash-0731 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 58 | 10.81 | 7.02 | 1.54x |
| DeepSeek-V4-Flash-0731 | 4 | 58 | 19.24 | 9.86 | 1.95x |
| DeepSeek-V4-Flash-0731 | 8 | 58 | 31.13 | 13.37 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 58 | 43.78 | 17.30 | 2.53x |
| DeepSeek-V4-Flash-0731 | 32 | 58 | 52.57 | 21.09 | 2.49x |
| DeepSeek-V4-Flash-0731 | 64 | 58 | 56.21 | 24.04 | 2.34x |
| DeepSeek-V4-Flash-0731 | 256 | 58 | 57.32 | 25.97 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1024 | 58 | 57.32 | 25.99 | 2.21x |
| DeepSeek-V4-Flash-0731 | 1 | 61 | 5.76 | 4.95 | 1.16x |
| DeepSeek-V4-Flash-0731 | 2 | 61 | 10.86 | 7.12 | 1.53x |
| DeepSeek-V4-Flash-0731 | 4 | 61 | 19.41 | 10.00 | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | 61 | 31.64 | 13.62 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 61 | 44.97 | 17.68 | 2.54x |
| DeepSeek-V4-Flash-0731 | 32 | 61 | 54.57 | 21.63 | 2.52x |
| DeepSeek-V4-Flash-0731 | 64 | 61 | 58.76 | 24.72 | 2.38x |
| DeepSeek-V4-Flash-0731 | 256 | 61 | 60.10 | 26.74 | 2.25x |
| DeepSeek-V4-Flash-0731 | 1024 | 61 | 60.11 | 26.76 | 2.25x |
| DeepSeek-V4-Flash-0731 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 87 | 11.15 | 7.78 | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | 87 | 20.44 | 10.95 | 1.87x |
| DeepSeek-V4-Flash-0731 | 8 | 87 | 34.83 | 15.44 | 2.26x |
| DeepSeek-V4-Flash-0731 | 16 | 87 | 52.83 | 20.51 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 87 | 68.97 | 25.63 | 2.69x |
| DeepSeek-V4-Flash-0731 | 64 | 87 | 78.37 | 29.78 | 2.63x |
| DeepSeek-V4-Flash-0731 | 256 | 87 | 82.46 | 32.55 | 2.53x |
| DeepSeek-V4-Flash-0731 | 1024 | 87 | 82.49 | 32.58 | 2.53x |
| DeepSeek-V4-Flash-0731 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 2 | 116 | 11.32 | 8.33 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 116 | 21.08 | 11.71 | 1.80x |
| DeepSeek-V4-Flash-0731 | 8 | 116 | 36.91 | 16.98 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 116 | 58.39 | 22.88 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 116 | 80.31 | 29.09 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 116 | 95.45 | 34.23 | 2.79x |
| DeepSeek-V4-Flash-0731 | 256 | 116 | 103.29 | 37.73 | 2.74x |
| DeepSeek-V4-Flash-0731 | 1024 | 116 | 103.36 | 37.77 | 2.74x |
| DeepSeek-V4-Flash-0731 | 1 | 142 | 5.90 | 5.47 | 1.08x |
| DeepSeek-V4-Flash-0731 | 2 | 142 | 11.42 | 8.71 | 1.31x |
| DeepSeek-V4-Flash-0731 | 4 | 142 | 21.45 | 12.27 | 1.75x |
| DeepSeek-V4-Flash-0731 | 8 | 142 | 38.13 | 18.03 | 2.11x |
| DeepSeek-V4-Flash-0731 | 16 | 142 | 61.80 | 24.52 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 142 | 87.75 | 31.58 | 2.78x |
| DeepSeek-V4-Flash-0731 | 64 | 142 | 107.42 | 37.52 | 2.86x |
| DeepSeek-V4-Flash-0731 | 256 | 142 | 118.65 | 41.61 | 2.85x |
| DeepSeek-V4-Flash-0731 | 1024 | 142 | 118.74 | 41.65 | 2.85x |
| DeepSeek-V4-Flash-0731 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 2 | 173 | 11.49 | 9.06 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 173 | 21.74 | 12.85 | 1.69x |
| DeepSeek-V4-Flash-0731 | 8 | 173 | 39.14 | 19.00 | 2.06x |
| DeepSeek-V4-Flash-0731 | 16 | 173 | 64.73 | 26.15 | 2.48x |
| DeepSeek-V4-Flash-0731 | 32 | 173 | 94.43 | 34.13 | 2.77x |
| DeepSeek-V4-Flash-0731 | 64 | 173 | 118.70 | 40.88 | 2.90x |
| DeepSeek-V4-Flash-0731 | 256 | 173 | 133.64 | 45.54 | 2.93x |
| DeepSeek-V4-Flash-0731 | 1024 | 173 | 133.78 | 45.59 | 2.93x |
| DeepSeek-V4-Flash-0731 | 1 | 176 | 5.92 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 2 | 176 | 11.50 | 9.09 | 1.26x |
| DeepSeek-V4-Flash-0731 | 4 | 176 | 21.77 | 12.91 | 1.69x |
| DeepSeek-V4-Flash-0731 | 8 | 176 | 39.22 | 19.08 | 2.06x |
| DeepSeek-V4-Flash-0731 | 16 | 176 | 64.96 | 26.29 | 2.47x |
| DeepSeek-V4-Flash-0731 | 32 | 176 | 94.98 | 34.36 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 176 | 119.65 | 41.17 | 2.91x |
| DeepSeek-V4-Flash-0731 | 256 | 176 | 134.93 | 45.89 | 2.94x |
| DeepSeek-V4-Flash-0731 | 1024 | 176 | 135.07 | 45.94 | 2.94x |
| DeepSeek-V4-Flash-0731 | 4096 | 176 | 135.07 | 45.94 | 2.94x |
| DeepSeek-V4-Flash-0731 | 1 | 178 | 5.92 | 5.57 | 1.06x |
| DeepSeek-V4-Flash-0731 | 2 | 178 | 11.50 | 9.11 | 1.26x |
| DeepSeek-V4-Flash-0731 | 4 | 178 | 21.78 | 12.94 | 1.68x |
| DeepSeek-V4-Flash-0731 | 8 | 178 | 39.27 | 19.13 | 2.05x |
| DeepSeek-V4-Flash-0731 | 16 | 178 | 65.12 | 26.39 | 2.47x |
| DeepSeek-V4-Flash-0731 | 32 | 178 | 95.34 | 34.51 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 178 | 120.28 | 41.37 | 2.91x |
| DeepSeek-V4-Flash-0731 | 256 | 178 | 135.78 | 46.12 | 2.94x |
| DeepSeek-V4-Flash-0731 | 1024 | 178 | 135.92 | 46.17 | 2.94x |
| DeepSeek-V4-Flash-0731 | 4096 | 178 | 135.92 | 46.17 | 2.94x |
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
| DeepSeek-V4-Flash-0731 | 1 | 953 | 5.98 | 5.92 | 1.01x |
| DeepSeek-V4-Flash-0731 | 2 | 953 | 11.79 | 11.13 | 1.06x |
| DeepSeek-V4-Flash-0731 | 4 | 953 | 22.90 | 18.76 | 1.22x |
| DeepSeek-V4-Flash-0731 | 8 | 953 | 43.25 | 27.02 | 1.60x |
| DeepSeek-V4-Flash-0731 | 16 | 953 | 77.54 | 39.52 | 1.96x |
| DeepSeek-V4-Flash-0731 | 32 | 953 | 126.93 | 57.95 | 2.19x |
| DeepSeek-V4-Flash-0731 | 64 | 953 | 180.40 | 72.06 | 2.50x |
| DeepSeek-V4-Flash-0731 | 256 | 953 | 224.15 | 83.06 | 2.70x |
| DeepSeek-V4-Flash-0731 | 1024 | 953 | 224.60 | 83.18 | 2.70x |
| DeepSeek-V4-Flash-0731 | 4096 | 953 | 224.60 | 83.18 | 2.70x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 4.9% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 17.6% |

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
| DeepSeek-V4-Flash-0731 | 1 | 18 | 78.33% | 28.88 | 2.05 |
| DeepSeek-V4-Flash-0731 | 2 | 1 | 7.92% | 9.25 | 2.05 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 7.92% | 9.25 | 2.05 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 7.92% | 9.25 | 2.05 |

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
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,366.1 | 381,137.0 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,366.1 | 381,137.0 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,366.1 | 381,137.0 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,366.1 | 381,137.0 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,366.1 | 381,137.0 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,366.1 | 381,137.0 |
| DeepSeek-V4-Flash-0731 | 64 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,366.1 | 381,137.0 |
| DeepSeek-V4-Flash-0731 | 256 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,366.1 | 381,137.0 |
| DeepSeek-V4-Flash-0731 | 1024 | 8.34% | 20.0 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 462.6 | 473,700.3 |
| DeepSeek-V4-Flash-0731 | 4096 | 29.40% | 51.0 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 116.1 | 475,451.5 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 251 |
| gpu | kv_read | 100 |
| gpu | link_latency | 833 |
| gpu | thermal | 253 |
| gpu | weight_read | 393 |
| rom | compute | 188 |
| rom | infeasible | 2904 |
| rom | kv_read | 58 |
| rom | link_latency | 492 |
| rom | thermal | 35 |
| rom | weight_read | 343 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 251 |
| rom | CAPACITY | 2904 |

## Mechanical consistency audit

**FAIL** over 90,273 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x36', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x40', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x60', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x63', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x90', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x106', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x107', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x108', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x120', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x36', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x40', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x60', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x63', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x90', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x106', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x107', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x108', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x120', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x36', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x40', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x60', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x63', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x90', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x106', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x107', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x108', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x120', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x36', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x38', 'DeepSeek-V4-Flash-0731', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 71 |
| derived | 47 |
| assumed | 67 |

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

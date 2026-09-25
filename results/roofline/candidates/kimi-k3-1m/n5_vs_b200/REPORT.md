# Area-constrained roofline: n5_vs_b200-kimi-k3-1m

> CANDIDATE MODEL under n5_vs_b200: Kimi-K3 at 1,000,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 247x (ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream, 3,857 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 3 devices. On the GPU side the correction reaches 11x (b200_sxm-x1965-pipeline, 1,965 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 58 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Kimi-K3 takes 6 x 46,225 mm2 (277,350 mm2, wafer, KV in SRAM) at 1,635 tok/s per user and 6 tok/s per 1,000 mm2, holding 1 session, against 173 copies of one unified HBM die at the same silicon: 5.8x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Kimi-K3 on 832,050 mm2 of ROM silicon at 1,897 tok/s per user against 832,000 mm2 of b200_sxm-x520-nvl72-hybrid at 283 tok/s: **6.7x**, ROM binding on `layer_fixed_latency` and the GPU on `layer_fixed_latency`. It holds 1 resident session against the GPU cluster's 5,792. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 7.77x to it.** At 554,700 mm2 on Kimi-K3 the pipeline-only GPU delivers 36.82 tok/s and the same silicon running hybrid delivers 286 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.08x (Kimi-K3, ROM binding on `layer_fixed_latency`) to 0.80x (Kimi-K3, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** Kimi-K3 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 42 to 160,869 tok/s, and its rate with every slot occupied from 160,869 to 160,869. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 3,857 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 2,124 us over NVLink, capping per-user decode at 471 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 686.7 us and cap it at 1,456 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 10 of 10 operating points and an array 0; on tokens per second per square millimetre the same points go 0 to the array and 10 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 58 of 1538 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 6.2x of aggregate throughput (Kimi-K3). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 5.99x, on Kimi-K3 at batch 4096, where the busiest region carries 3.42x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 10 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 215 of 1,538 feasible points (14.0%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `Kimi-K3/b200_sxm-x371-nvl72-hybrid` at batch 4096 on 593,600 mm2, throttled 1.42x from 18 to 12 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 36% arithmetic against 31.8% weight read. The ROM sweep is not what melts it.


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

### Kimi-K3 at 1,000,000 tokens

**Recommended: `ROM-N5-native-SRAMKV-wafer-tensor-x6`** -- 6 x 46,225 mm2 wafers, 277,350 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **1,635.1 tok/s per user** (0.61 ms/token), binding on `layer_fixed_latency`
- **5.9 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 1,635 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 19,325 W at 0.070 W/mm2, 11,819.3 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 173 copies of one unified HBM die -- `b200_sxm-x173-nvl72-hybrid`, 276,800 mm2, area ratio 1.0020 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 277,350 | 276,800 | 1.0020 |
| user tok/s | 1,635.1 | 281.8 | 5.80x |
| aggregate tok/s | 1,635 | 845 | 0.26x |
| resident sessions | 1 | 1,854 | -- |
| J/token | 11.8193 | 232.7742 | 19.7x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 1,854 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x144-nvl72-hybrid` at 230,400 mm2 and 288.6 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-hybrid-x12` | 554,700 | 1,868.6 | 3.4 | 1 | 6.53x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 832,050 | 1,896.9 | 2.3 | 1 | 6.70x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x284` | 231,460 | 672.9 | 2.9 | 1 | 2.44x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-wafer-tensor-x6` | 277,350 | 1,635.1 | 5.9 | 1 | 5.80x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-wafer-tensor-x6` | 277,350 | 1,635.1 | 5.9 | -- | 5.9 | ACCEPT |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x8` | 369,800 | 1,796.7 | 4.9 | 1.7 | 5.9 | stop |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x12` | 554,700 | 1,868.6 | 3.4 | 0.8 | 5.9 | stop |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 832,050 | 1,896.9 | 2.3 | 0.5 | 5.9 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-wafer-tensor-x6` **<-- recommended** | 277,350 | 6 | 1,635.1 | 1,635 | 5.9 | 1 | `layer_fixed_latency` | 19,325 | 11,819.3 | `b200_sxm-x173-nvl72-hybrid` | 5.80x |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x8` | 369,800 | 8 | 1,796.7 | 1,797 | 4.9 | 1 | `layer_fixed_latency` | 32,777 | 18,242.5 | `b200_sxm-x231-nvl72-hybrid` | 6.39x |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x12` | 554,700 | 12 | 1,868.6 | 1,869 | 3.4 | 1 | `layer_fixed_latency` | 59,608 | 31,899.7 | `b200_sxm-x347-nvl72-hybrid` | 6.53x |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 832,050 | 18 | 1,896.9 | 1,897 | 2.3 | 1 | `layer_fixed_latency` | 99,832 | 52,628.2 | `b200_sxm-x520-nvl72-hybrid` | 6.70x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 96 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x312` | 254,280 | 785.2 | 3.1 | 1 |
| array | 96 | fastest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | 312,145 | 946.4 | 3.0 | 1 |
| array | 96 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x284` | 231,460 | 672.9 | 2.9 | 1 |
| wafer | 27 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x6` | 277,350 | 1,635.1 | 5.9 | 1 |
| wafer | 27 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 832,050 | 1,896.9 | 2.3 | 1 |
| wafer | 27 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x6` | 277,350 | 1,635.1 | 5.9 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-hybrid-x383` | 312,145 | 946.4 | 946 | 1 | 24,172 | 25,539.7 | `layer_fixed_latency` | `b200_sxm-x195-nvl72-hybrid` | 285.4 | 2,103 | 257,115.7 | 1.000 | 3.32x | 10.1x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x18` | 832,050 | 1,896.9 | 1,897 | 1 | 99,832 | 52,628.2 | `layer_fixed_latency` | `b200_sxm-x520-nvl72-hybrid` | 283.0 | 5,792 | 661,484.4 | 1.000 | 6.70x | 12.6x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 1,743.9 | 29,646 | 4,148 | 496,271 | 128,831.0 | `layer_fixed_latency` | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | 22,193 | 1,264,954.5 | 1.000 | 6.32x | 9.8x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 1,743.9 | 29,646 | 4,148 | 496,271 | 65,312.7 | `layer_fixed_latency` | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | 22,193 | 641,298.3 | 1.000 | 6.32x | 9.8x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 1,743.9 | 29,646 | 4,148 | 496,271 | 33,553.6 | `layer_fixed_latency` | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | 22,193 | 329,470.1 | 1.000 | 6.32x | 9.8x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 1,743.9 | 29,646 | 4,148 | 496,271 | 17,674.0 | `layer_fixed_latency` | `b200_sxm-x1965-nvl72-hybrid` | 276.0 | 22,193 | 173,556.0 | 1.000 | 6.32x | 9.8x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 1,591.6 | 54,116 | 4,148 | 540,182 | 10,493.7 | `layer_fixed_latency` | `b200_sxm-x1965-nvl72-hybrid` | 273.9 | 22,193 | 94,757.3 | 1.000 | 5.81x | 9.0x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 1,322.5 | 89,931 | 4,148 | 604,451 | 7,029.2 | `kv_read` | `b200_sxm-x1965-nvl72-hybrid` | 257.6 | 22,193 | 52,809.6 | 1.000 | 5.13x | 7.5x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 531.0 | 135,941 | 4,148 | 686,757 | 5,051.9 | `kv_read` | `b200_sxm-x1965-nvl72-hybrid` | 196.9 | 22,193 | 22,376.8 | 1.000 | 2.70x | 4.4x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 152.1 | 155,769 | 4,148 | 722,285 | 4,636.9 | `kv_read` | `b200_sxm-x1965-nvl72-hybrid` | 120.5 | 22,193 | 12,771.0 | 1.000 | 1.26x | 2.8x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x68` | 3,143,300 | 39.3 | 160,869 | 4,148 | 731,423 | 4,546.7 | `kv_read` | `b200_sxm-x1965-nvl72-hybrid` | 49.4 | 22,193 | 9,716.4 | 1.000 | 0.80x | 2.1x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-wafer-tensor-x6` | 277,350 | wafer | SRAM | 1 |
| 2-1024 | `ROM-N5-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | wafer | HBM | 4,148 |
| 4096 | `ROM-N5-native-HBMKV-wafer-pipeline-x68` | 3,143,300 | wafer | HBM | 4,148 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Kimi-K3 | SRAM | rom | 284, 312, 318, 319, 340, 378, 383, 395 |
| Kimi-K3 | SRAM | sram | 284, 312, 318, 319, 340, 378, 383, 395 |

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
| Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-tensor-x6` | 1 | 341 on `rom_wafer_express` | 5.24 | hierarchical | 301.90 | 225.55 | 96.33 | 135.95 | 1,635.1 |
| Kimi-K3 | `b200_sxm-x173-nvl72-hybrid` | 1 | 64 | 5.24 | measured_floor | 2,180.10 | 976.93 | 406.00 | 487.52 | 281.8 |
| Kimi-K3 | `b200_sxm-x173-nvl72-hybrid` | 64 | 64 | 5.24 | measured_floor | 2,180.10 | 1,441.30 | 2,373.33 | 677.09 | 168.5 |

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

- **215 of 1,538 feasible points (14.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 215.
- By area class: wafer (>=40,000 mm2) 215.
- By KV store: hbm 215.
- By batch: B=1 19, B=2 19, B=4 19, B=8 19, B=16 19, B=32 20, B=64 22, B=256 31, B=1024 38, B=4096 9.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 47% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 1,151 | 215 | 43.9% | 100.0% | 0.625 | 80% |
| rom | wafer (>=40,000 mm2) | 387 | 0 | 15.3% | 46.6% | 0.233 | 97% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `Kimi-K3/b200_sxm-x371-nvl72-hybrid` | Kimi-K3 | 4096 | 593,600 | hbm | 1.416x | 371,000.0 / 371,000.0 W | 35% | 12.4 | 17.5 |
| `Kimi-K3/b200_sxm-x371-pipeline` | Kimi-K3 | 4096 | 593,600 | hbm | 1.387x | 371,000.0 / 371,000.0 W | 35% | 8.7 | 12.0 |
| `Kimi-K3/b200_sxm-x520-nvl72-hybrid` | Kimi-K3 | 4096 | 832,000 | hbm | 1.377x | 520,000.0 / 520,000.0 W | 35% | 16.3 | 22.4 |
| `Kimi-K3/b200_sxm-x116-hybrid` | Kimi-K3 | 1024 | 185,600 | hbm | 1.371x | 116,000.0 / 116,000.0 W | 35% | 14.7 | 20.2 |
| `Kimi-K3/b200_sxm-x116-pipeline` | Kimi-K3 | 1024 | 185,600 | hbm | 1.361x | 116,000.0 / 116,000.0 W | 35% | 10.4 | 14.1 |
| `Kimi-K3/b200_sxm-x520-pipeline` | Kimi-K3 | 4096 | 832,000 | hbm | 1.348x | 520,000.0 / 520,000.0 W | 35% | 11.3 | 15.3 |
| `Kimi-K3/b200_sxm-x193-nvl72-hybrid` | Kimi-K3 | 1024 | 308,800 | hbm | 1.344x | 193,000.0 / 193,000.0 W | 35% | 25.2 | 33.9 |
| `Kimi-K3/b200_sxm-x195-nvl72-hybrid` | Kimi-K3 | 1024 | 312,000 | hbm | 1.341x | 195,000.0 / 195,000.0 W | 35% | 25.5 | 34.2 |
| `Kimi-K3/b200_sxm-x162-nvl72-hybrid` | Kimi-K3 | 1024 | 259,200 | hbm | 1.336x | 162,000.0 / 162,000.0 W | 35% | 21.9 | 29.2 |
| `Kimi-K3/b200_sxm-x144-pipeline` | Kimi-K3 | 1024 | 230,400 | hbm | 1.336x | 144,000.0 / 144,000.0 W | 35% | 12.2 | 16.4 |
| `Kimi-K3/b200_sxm-x145-pipeline` | Kimi-K3 | 1024 | 232,000 | hbm | 1.335x | 145,000.0 / 145,000.0 W | 35% | 12.3 | 16.4 |
| `Kimi-K3/b200_sxm-x201-nvl72-hybrid` | Kimi-K3 | 1024 | 321,600 | hbm | 1.334x | 201,000.0 / 201,000.0 W | 35% | 26.3 | 35.0 |

The worst point's dynamic energy is arithmetic 35.6%, kv read 32.4%, weight read 31.8%, operand delivery 0.1%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| Kimi-K3 | 1 | 554,700 | `Kimi-K3/ROM-N5-native-SRAMKV-wafer-hybrid-x12` | 31.899654 | 59,608.4 | layer_fixed_latency | `Kimi-K3/b200_sxm-x347-nvl72-hybrid` | 442.504959 | 146,849.8 | layer_fixed_latency | 13.87x |
| Kimi-K3 | 2 | 3,143,300 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68` | 128.831026 | 496,271.3 | layer_fixed_latency | `Kimi-K3/b200_sxm-x1965-nvl72-hybrid` | 1,264.954540 | 824,971.2 | layer_fixed_latency | 9.82x |
| Kimi-K3 | 4 | 3,143,300 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68` | 65.312745 | 496,271.3 | layer_fixed_latency | `Kimi-K3/b200_sxm-x1965-nvl72-hybrid` | 641.298259 | 824,971.2 | layer_fixed_latency | 9.82x |
| Kimi-K3 | 8 | 3,143,300 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68` | 33.553605 | 496,271.3 | layer_fixed_latency | `Kimi-K3/b200_sxm-x1965-nvl72-hybrid` | 329.470118 | 824,971.2 | layer_fixed_latency | 9.82x |
| Kimi-K3 | 16 | 3,143,300 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68` | 17.674035 | 496,271.3 | layer_fixed_latency | `Kimi-K3/b200_sxm-x1965-nvl72-hybrid` | 173.556048 | 824,971.2 | layer_fixed_latency | 9.82x |
| Kimi-K3 | 32 | 3,143,300 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68` | 10.493673 | 540,181.7 | layer_fixed_latency | `Kimi-K3/b200_sxm-x1965-nvl72-hybrid` | 94.757274 | 830,387.3 | layer_fixed_latency | 9.03x |
| Kimi-K3 | 64 | 3,143,300 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68` | 7.029200 | 604,450.7 | kv_read | `Kimi-K3/b200_sxm-x1965-nvl72-hybrid` | 52.809587 | 870,590.3 | layer_fixed_latency | 7.51x |
| Kimi-K3 | 256 | 3,143,300 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68` | 5.051886 | 686,756.7 | kv_read | `Kimi-K3/b200_sxm-x1965-nvl72-hybrid` | 22.376771 | 1,127,701.9 | layer_fixed_latency | 4.43x |
| Kimi-K3 | 1024 | 3,143,300 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68` | 4.636897 | 722,284.7 | kv_read | `Kimi-K3/b200_sxm-x1965-nvl72-hybrid` | 12.771022 | 1,575,836.8 | weight_read | 2.75x |
| Kimi-K3 | 4096 | 3,143,300 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68` | 4.546690 | 731,422.9 | kv_read | `Kimi-K3/b200_sxm-x1965-nvl72-hybrid` | 9.716400 | 1,965,000.0 | thermal | 2.14x |

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
| Kimi-K3 | 1,000,000 | 2,800 B | 1,560.9 GB | 4.46 | 14.273 GB | 14.273 GB | 9.6 |

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
| Kimi-K3 | 6 | 277,350 | 1,757.9 | wafer-hybrid | 1,635.1 | wafer-tensor | 1.08x | 368.7 | pipeline | 281.8 | hybrid | 1.31x | 4.77x | 5.80x | 1.22x |
| Kimi-K3 | 8 | 369,800 | 2,215.0 | wafer-pipeline | 1,796.7 | wafer-hybrid | 1.23x | 373.6 | pipeline | 281.4 | hybrid | 1.33x | 5.93x | 6.39x | 1.08x |
| Kimi-K3 | 12 | 554,700 | 2,221.4 | wafer-pipeline | 1,868.6 | wafer-hybrid | 1.19x | 378.7 | pipeline | 286.2 | hybrid | 1.32x | 5.87x | 6.53x | 1.11x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.08x to 1.22x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Kimi-K3 | 1 | fastest | Kimi-K3/ROM-N5-native-SRAMKV-wafer-hybrid-x18 | 832,050 | 1,896.9 | 1,896.9 | layer_fixed_latency | Kimi-K3/b200_sxm-x520-nvl72-hybrid | 832,000 | 1.00x | hybrid | 1,005.74 | 283.0 | 2,264.3 | layer_fixed_latency | 6.70x | 0.10x | 51.52x | 6.70x |
| Kimi-K3 | 1 | smallest silicon | Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x284 | 231,460 | 672.9 | 672.9 | link_latency | Kimi-K3/b200_sxm-x145-nvl72-hybrid | 232,000 | 1.00x | hybrid | 976.93 | 275.9 | 827.8 | layer_fixed_latency | 2.44x | 0.13x | 18.27x | 2.44x |
| Kimi-K3 | 2 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,743.9 | 29,645.9 | layer_fixed_latency | Kimi-K3/b200_sxm-x1965-nvl72-hybrid | 3,144,000 | 1.00x | hybrid | 1,120.89 | 276.0 | 7,729.1 | layer_fixed_latency | 6.32x | 0.41x | 47.36x | 6.32x |
| Kimi-K3 | 4 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,743.9 | 29,645.9 | layer_fixed_latency | Kimi-K3/b200_sxm-x1965-nvl72-hybrid | 3,144,000 | 1.00x | hybrid | 1,120.89 | 276.0 | 7,729.1 | layer_fixed_latency | 6.32x | 0.41x | 47.36x | 6.32x |
| Kimi-K3 | 8 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,743.9 | 29,645.9 | layer_fixed_latency | Kimi-K3/b200_sxm-x1965-nvl72-hybrid | 3,144,000 | 1.00x | hybrid | 1,120.89 | 276.0 | 7,729.1 | layer_fixed_latency | 6.32x | 0.41x | 47.36x | 6.32x |
| Kimi-K3 | 16 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,743.9 | 29,645.9 | layer_fixed_latency | Kimi-K3/b200_sxm-x1965-nvl72-hybrid | 3,144,000 | 1.00x | hybrid | 1,120.89 | 276.0 | 7,729.1 | layer_fixed_latency | 6.32x | 0.41x | 47.36x | 6.32x |
| Kimi-K3 | 32 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,591.6 | 54,115.8 | layer_fixed_latency | Kimi-K3/b200_sxm-x1965-nvl72-hybrid | 3,144,000 | 1.00x | hybrid | 1,137.47 | 273.9 | 8,763.3 | layer_fixed_latency | 5.81x | 0.75x | 43.23x | 5.81x |
| Kimi-K3 | 64 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,322.5 | 89,931.0 | kv_read | Kimi-K3/b200_sxm-x1965-nvl72-hybrid | 3,144,000 | 1.00x | hybrid | 1,270.10 | 257.6 | 16,485.5 | layer_fixed_latency | 5.13x | 1.24x | 35.92x | 5.13x |
| Kimi-K3 | 256 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 531.0 | 135,940.6 | kv_read | Kimi-K3/b200_sxm-x1965-nvl72-hybrid | 3,144,000 | 1.00x | hybrid | 1,598.86 | 196.9 | 50,396.1 | layer_fixed_latency | 2.70x | 1.88x | 14.42x | 2.70x |
| Kimi-K3 | 1024 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 152.1 | 155,769.0 | kv_read | Kimi-K3/b200_sxm-x1965-nvl72-hybrid | 3,144,000 | 1.00x | hybrid | 2,034.16 | 120.5 | 123,391.6 | weight_read | 1.26x | 1.26x | 4.13x | 1.27x |
| Kimi-K3 | 4096 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 39.3 | 160,869.3 | kv_read | Kimi-K3/b200_sxm-x1965-nvl72-hybrid | 3,144,000 | 1.00x | hybrid | 2,199.76 | 49.4 | 202,235.4 | thermal | 0.80x | 0.80x | 1.45x | 0.81x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| Kimi-K3 | 29 | 46,400 | 963.09 | 454.98 | 255.0 | 293.0 |
| Kimi-K3 | 58 | 92,800 | 963.36 | 455.14 | 283.1 | 330.6 |
| Kimi-K3 | 69 | 110,400 | 963.40 | 455.16 | 288.1 | 337.6 |
| Kimi-K3 | 74 | 118,400 | 971.17 | 457.48 | 265.9 | 307.9 |
| Kimi-K3 | 87 | 139,200 | 971.17 | 457.48 | 272.5 | 316.8 |
| Kimi-K3 | 116 | 185,600 | 971.17 | 457.48 | 282.4 | 330.4 |
| Kimi-K3 | 144 | 230,400 | 971.20 | 457.48 | 288.6 | 338.9 |
| Kimi-K3 | 145 | 232,000 | 976.93 | 459.80 | 275.9 | 321.9 |
| Kimi-K3 | 159 | 254,400 | 976.93 | 459.80 | 279.1 | 326.2 |
| Kimi-K3 | 162 | 259,200 | 976.93 | 459.80 | 279.7 | 327.0 |
| Kimi-K3 | 173 | 276,800 | 976.93 | 459.80 | 281.8 | 329.9 |
| Kimi-K3 | 193 | 308,800 | 976.96 | 459.80 | 285.1 | 334.4 |
| Kimi-K3 | 195 | 312,000 | 976.96 | 459.80 | 285.4 | 334.8 |
| Kimi-K3 | 201 | 321,600 | 976.96 | 459.80 | 286.2 | 335.9 |
| Kimi-K3 | 231 | 369,600 | 982.69 | 462.12 | 281.4 | 329.7 |
| Kimi-K3 | 347 | 555,200 | 988.47 | 464.43 | 286.2 | 336.7 |
| Kimi-K3 | 371 | 593,600 | 994.20 | 466.75 | 282.5 | 332.0 |
| Kimi-K3 | 520 | 832,000 | 1,005.74 | 471.38 | 283.0 | 333.5 |
| Kimi-K3 | 1,965 | 3,144,000 | 1,120.89 | 517.72 | 276.0 | 331.2 |

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
| Kimi-K3 | 29 | 46,400 | 36.8 | 255.0 | 159.4 | tensor | 963.09 | 24.6% | layer_fixed_latency |
| Kimi-K3 | 58 | 92,800 | 36.8 | 283.1 | 158.8 | tensor | 963.36 | 27.3% | layer_fixed_latency |
| Kimi-K3 | 69 | 110,400 | 36.8 | 288.1 | 163.0 | tensor | 963.40 | 27.8% | layer_fixed_latency |
| Kimi-K3 | 74 | 118,400 | 36.8 | 170.2 | 265.9 | hybrid | 971.17 | 25.8% | layer_fixed_latency |
| Kimi-K3 | 87 | 139,200 | 36.8 | 171.6 | 272.5 | hybrid | 971.17 | 26.5% | layer_fixed_latency |
| Kimi-K3 | 116 | 185,600 | 36.8 | 173.5 | 282.4 | hybrid | 971.17 | 27.4% | layer_fixed_latency |
| Kimi-K3 | 144 | 230,400 | 36.8 | 174.6 | 288.6 | hybrid | 971.20 | 28.0% | layer_fixed_latency |
| Kimi-K3 | 145 | 232,000 | 36.8 | 173.2 | 275.9 | hybrid | 976.93 | 27.0% | layer_fixed_latency |
| Kimi-K3 | 159 | 254,400 | 36.8 | 173.7 | 279.1 | hybrid | 976.93 | 27.3% | layer_fixed_latency |
| Kimi-K3 | 162 | 259,200 | 36.8 | 173.7 | 279.7 | hybrid | 976.93 | 27.3% | layer_fixed_latency |
| Kimi-K3 | 173 | 276,800 | 36.8 | 174.0 | 281.8 | hybrid | 976.93 | 27.5% | layer_fixed_latency |
| Kimi-K3 | 193 | 308,800 | 36.8 | 174.4 | 285.1 | hybrid | 976.96 | 27.8% | layer_fixed_latency |
| Kimi-K3 | 195 | 312,000 | 36.8 | 174.5 | 285.4 | hybrid | 976.96 | 27.9% | layer_fixed_latency |
| Kimi-K3 | 201 | 321,600 | 36.8 | 174.6 | 286.2 | hybrid | 976.96 | 28.0% | layer_fixed_latency |
| Kimi-K3 | 231 | 369,600 | 36.8 | 174.3 | 281.4 | hybrid | 982.69 | 27.7% | layer_fixed_latency |
| Kimi-K3 | 347 | 555,200 | 36.8 | 174.9 | 286.2 | hybrid | 988.47 | 28.3% | layer_fixed_latency |
| Kimi-K3 | 371 | 593,600 | 36.8 | 174.7 | 282.5 | hybrid | 994.20 | 28.1% | layer_fixed_latency |
| Kimi-K3 | 520 | 832,000 | 36.8 | 174.9 | 283.0 | hybrid | 1,005.74 | 28.5% | layer_fixed_latency |
| Kimi-K3 | 1965 | 3,144,000 | 36.8 | 175.1 | 276.0 | hybrid | 1,120.89 | 30.9% | layer_fixed_latency |

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
| Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x395 | Kimi-K3 | 395 | pipeline | rom_package_ucie | rom_board_serdes | 92 | 3.42 us | 29,235.7 tok/s | 292,356.8 tok/s | 69 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.94 us; 23 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.48 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x284 | Kimi-K3 | 284 | tensor | rom_package_ucie | rom_board_serdes | 372 | 336.96 us | 296.8 tok/s | 2,967.7 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 186 x all_reduce span 71 on rom_board_serdes (traversals 17.6) = 331.74 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x318 | Kimi-K3 | 318 | hybrid | rom_package_ucie | rom_board_serdes | 265 | 13.75 us | 7,273.2 tok/s | 72,732.1 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 79 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 8.53 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x395 | Kimi-K3 | 395 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x18 | Kimi-K3 | 18 | pipeline | on_wafer_n5 | rom_wafer_serdes | 92 | 11.48 us | 8,712.7 tok/s | 87,127.5 tok/s | 91 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 11.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x378 | Kimi-K3 | 378 | tensor | nvlink5 | infiniband_ndr | 372 | 1,365.99 us | 73.2 tok/s | 732.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 48 on infiniband_ndr (traversals 2.0) = 911.82 us |
| Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x8 | Kimi-K3 | 8 | tensor | on_wafer_n5 | rom_wafer_serdes | 372 | 441.06 us | 226.7 tok/s | 2,267.3 tok/s | 186 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 358.05 us; 186 x all_reduce span 8 on rom_wafer_serdes (traversals 4.4) = 83.01 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x312 | Kimi-K3 | 312 | hybrid | nvlink5 | infiniband_ndr | 224 | 542.21 us | 184.4 tok/s | 1,844.3 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 38 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 88.04 us |
| Kimi-K3/ROM-N5-native-SRAMKV-wafer-hybrid-x12 | Kimi-K3 | 12 | hybrid | on_wafer_n5 | rom_wafer_serdes | 197 | 359.18 us | 278.4 tok/s | 2,784.1 tok/s | 186 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 358.05 us; 11 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 1.13 us |
| Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | Kimi-K3 | 68 | pipeline | on_wafer_n5 | rom_wafer_serdes | 92 | 11.48 us | 8,712.7 tok/s | 87,127.5 tok/s | 91 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 11.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| Kimi-K3/ROM-N5-native-HBMKV-wafer-tensor-x68 | Kimi-K3 | 68 | tensor | on_wafer_n5 | rom_wafer_serdes | 372 | 686.72 us | 145.6 tok/s | 1,456.2 tok/s | 186 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 358.05 us; 186 x all_reduce span 68 on rom_wafer_serdes (traversals 17.6) = 328.67 us |
| Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | Kimi-K3 | 68 | hybrid | on_wafer_n5 | rom_wafer_serdes | 253 | 364.91 us | 274.0 tok/s | 2,740.4 tok/s | 186 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 358.05 us; 67 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 6.86 us |
| Kimi-K3/b200_sxm-x29-pipeline | Kimi-K3 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 37.35 us | 2,677.5 tok/s | 26,774.9 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.40 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| Kimi-K3/b200_sxm-x29-tensor | Kimi-K3 | 29 | tensor | nvlink5 | infiniband_ndr | 372 | 1,329.33 us | 75.2 tok/s | 752.3 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 875.15 us |
| Kimi-K3/b200_sxm-x29-hybrid | Kimi-K3 | 29 | hybrid | nvlink5 | infiniband_ndr | 189 | 461.13 us | 216.9 tok/s | 2,168.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| Kimi-K3/b200_sxm-x29-nvl72-tensor | Kimi-K3 | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 186 | 454.98 us | 219.8 tok/s | 2,197.9 tok/s | 186 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 454.98 us |
| Kimi-K3/b200_sxm-x29-expert | Kimi-K3 | 29 | expert | nvlink5 | infiniband_ndr | 372 | 856.00 us | 116.8 tok/s | 1,168.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 448.99 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 407.00 us |
| Kimi-K3/b200_sxm-x29-nvl72-expert | Kimi-K3 | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 679.82 us | 147.1 tok/s | 1,471.0 tok/s | 186 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 454.98 us; 186 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 224.83 us |
| Kimi-K3/b200_sxm-x58-pipeline | Kimi-K3 | 58 | pipeline | nvlink5 | infiniband_ndr | 57 | 77.01 us | 1,298.5 tok/s | 12,984.7 tok/s | 50 x point_to_point span 2 on nvlink5 (traversals 1.0) = 60.80 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| Kimi-K3/b200_sxm-x58-tensor | Kimi-K3 | 58 | tensor | nvlink5 | infiniband_ndr | 372 | 1,349.33 us | 74.1 tok/s | 741.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 895.15 us |
| Kimi-K3/b200_sxm-x58-hybrid | Kimi-K3 | 58 | hybrid | nvlink5 | infiniband_ndr | 193 | 470.39 us | 212.6 tok/s | 2,125.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| Kimi-K3/b200_sxm-x58-nvl72-tensor | Kimi-K3 | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 186 | 455.14 us | 219.7 tok/s | 2,197.1 tok/s | 186 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 455.14 us |
| Kimi-K3/b200_sxm-x58-expert | Kimi-K3 | 58 | expert | nvlink5 | infiniband_ndr | 372 | 839.80 us | 119.1 tok/s | 1,190.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 447.51 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 392.29 us |
| Kimi-K3/b200_sxm-x58-nvl72-expert | Kimi-K3 | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 679.15 us | 147.2 tok/s | 1,472.4 tok/s | 186 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 455.14 us; 186 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 224.02 us |
| Kimi-K3/b200_sxm-x69-pipeline | Kimi-K3 | 69 | pipeline | nvlink5 | infiniband_ndr | 68 | 91.49 us | 1,093.0 tok/s | 10,930.2 tok/s | 60 x point_to_point span 2 on nvlink5 (traversals 1.0) = 72.96 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.53 us |
| Kimi-K3/b200_sxm-x69-tensor | Kimi-K3 | 69 | tensor | nvlink5 | infiniband_ndr | 372 | 1,351.55 us | 74.0 tok/s | 739.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 897.37 us |
| Kimi-K3/b200_sxm-x69-hybrid | Kimi-K3 | 69 | hybrid | nvlink5 | infiniband_ndr | 194 | 472.71 us | 211.5 tok/s | 2,115.5 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.53 us |
| Kimi-K3/b200_sxm-x69-nvl72-tensor | Kimi-K3 | 69 | tensor | nvlink5_nvl72 | infiniband_ndr | 186 | 455.16 us | 219.7 tok/s | 2,197.0 tok/s | 186 x all_reduce span 69 on nvlink5_nvl72 (traversals 2.0) = 455.16 us |
| Kimi-K3/b200_sxm-x69-expert | Kimi-K3 | 69 | expert | nvlink5 | infiniband_ndr | 372 | 837.32 us | 119.4 tok/s | 1,194.3 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 447.37 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 389.95 us |
| Kimi-K3/b200_sxm-x69-nvl72-expert | Kimi-K3 | 69 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 679.05 us | 147.3 tok/s | 1,472.7 tok/s | 186 x all_reduce span 69 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 223.89 us |
| Kimi-K3/b200_sxm-x74-pipeline | Kimi-K3 | 74 | pipeline | nvlink5 | infiniband_ndr | 73 | 98.67 us | 1,013.5 tok/s | 10,134.8 tok/s | 64 x point_to_point span 2 on nvlink5 (traversals 1.0) = 77.82 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| Kimi-K3/b200_sxm-x74-tensor | Kimi-K3 | 74 | tensor | nvlink5 | infiniband_ndr | 372 | 1,353.33 us | 73.9 tok/s | 738.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 899.15 us |
| Kimi-K3/b200_sxm-x74-hybrid | Kimi-K3 | 74 | hybrid | nvlink5 | infiniband_ndr | 195 | 475.03 us | 210.5 tok/s | 2,105.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| Kimi-K3/b200_sxm-x74-nvl72-tensor | Kimi-K3 | 74 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,290.32 us | 77.5 tok/s | 775.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 835.15 us |
| Kimi-K3/b200_sxm-x74-nvl72-hybrid | Kimi-K3 | 74 | hybrid | nvlink5_nvl72 | infiniband_ndr | 187 | 457.48 us | 218.6 tok/s | 2,185.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| Kimi-K3/b200_sxm-x74-expert | Kimi-K3 | 74 | expert | nvlink5 | infiniband_ndr | 372 | 836.37 us | 119.6 tok/s | 1,195.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 447.26 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 389.11 us |
| Kimi-K3/b200_sxm-x74-nvl72-expert | Kimi-K3 | 74 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 844.28 us | 118.4 tok/s | 1,184.4 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 389.11 us |
| Kimi-K3/b200_sxm-x87-pipeline | Kimi-K3 | 87 | pipeline | nvlink5 | infiniband_ndr | 86 | 115.58 us | 865.2 tok/s | 8,652.2 tok/s | 76 x point_to_point span 2 on nvlink5 (traversals 1.0) = 92.41 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| Kimi-K3/b200_sxm-x87-tensor | Kimi-K3 | 87 | tensor | nvlink5 | infiniband_ndr | 372 | 1,354.78 us | 73.8 tok/s | 738.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 900.61 us |
| Kimi-K3/b200_sxm-x87-hybrid | Kimi-K3 | 87 | hybrid | nvlink5 | infiniband_ndr | 196 | 477.34 us | 209.5 tok/s | 2,094.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| Kimi-K3/b200_sxm-x87-nvl72-tensor | Kimi-K3 | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,290.32 us | 77.5 tok/s | 775.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 835.15 us |
| Kimi-K3/b200_sxm-x87-nvl72-hybrid | Kimi-K3 | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 187 | 457.48 us | 218.6 tok/s | 2,185.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| Kimi-K3/b200_sxm-x87-expert | Kimi-K3 | 87 | expert | nvlink5 | infiniband_ndr | 372 | 834.57 us | 119.8 tok/s | 1,198.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 447.18 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 387.39 us |
| Kimi-K3/b200_sxm-x87-nvl72-expert | Kimi-K3 | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 842.55 us | 118.7 tok/s | 1,186.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 387.39 us |
| Kimi-K3/b200_sxm-x116-pipeline | Kimi-K3 | 116 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x116-tensor | Kimi-K3 | 116 | tensor | nvlink5 | infiniband_ndr | 372 | 1,358.66 us | 73.6 tok/s | 736.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 904.48 us |
| Kimi-K3/b200_sxm-x116-hybrid | Kimi-K3 | 116 | hybrid | nvlink5 | infiniband_ndr | 200 | 486.61 us | 205.5 tok/s | 2,055.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| Kimi-K3/b200_sxm-x116-nvl72-tensor | Kimi-K3 | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,290.32 us | 77.5 tok/s | 775.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 835.15 us |
| Kimi-K3/b200_sxm-x116-nvl72-hybrid | Kimi-K3 | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 187 | 457.48 us | 218.6 tok/s | 2,185.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| Kimi-K3/b200_sxm-x116-expert | Kimi-K3 | 116 | expert | nvlink5 | infiniband_ndr | 372 | 831.89 us | 120.2 tok/s | 1,202.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.96 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 384.94 us |
| Kimi-K3/b200_sxm-x116-nvl72-expert | Kimi-K3 | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 840.10 us | 119.0 tok/s | 1,190.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 384.94 us |
| Kimi-K3/b200_sxm-x144-pipeline | Kimi-K3 | 144 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x144-tensor | Kimi-K3 | 144 | tensor | nvlink5 | infiniband_ndr | 372 | 1,360.44 us | 73.5 tok/s | 735.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 18 on infiniband_ndr (traversals 2.0) = 906.26 us |
| Kimi-K3/b200_sxm-x144-hybrid | Kimi-K3 | 144 | hybrid | nvlink5 | infiniband_ndr | 203 | 493.56 us | 202.6 tok/s | 2,026.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 39.38 us |
| Kimi-K3/b200_sxm-x144-nvl72-tensor | Kimi-K3 | 144 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,290.32 us | 77.5 tok/s | 775.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 835.15 us |
| Kimi-K3/b200_sxm-x144-nvl72-hybrid | Kimi-K3 | 144 | hybrid | nvlink5_nvl72 | infiniband_ndr | 187 | 457.48 us | 218.6 tok/s | 2,185.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| Kimi-K3/b200_sxm-x144-expert | Kimi-K3 | 144 | expert | nvlink5 | infiniband_ndr | 372 | 830.34 us | 120.4 tok/s | 1,204.3 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.83 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 383.51 us |
| Kimi-K3/b200_sxm-x144-nvl72-expert | Kimi-K3 | 144 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 834.29 us | 119.9 tok/s | 1,198.6 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 383.51 us |
| Kimi-K3/b200_sxm-x145-pipeline | Kimi-K3 | 145 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x145-tensor | Kimi-K3 | 145 | tensor | nvlink5 | infiniband_ndr | 372 | 1,360.91 us | 73.5 tok/s | 734.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 906.73 us |
| Kimi-K3/b200_sxm-x145-hybrid | Kimi-K3 | 145 | hybrid | nvlink5 | infiniband_ndr | 204 | 495.88 us | 201.7 tok/s | 2,016.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| Kimi-K3/b200_sxm-x145-nvl72-tensor | Kimi-K3 | 145 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x145-nvl72-hybrid | Kimi-K3 | 145 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x145-expert | Kimi-K3 | 145 | expert | nvlink5 | infiniband_ndr | 372 | 830.30 us | 120.4 tok/s | 1,204.4 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.83 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 383.46 us |
| Kimi-K3/b200_sxm-x145-nvl72-expert | Kimi-K3 | 145 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 834.25 us | 119.9 tok/s | 1,198.7 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 383.46 us |
| Kimi-K3/b200_sxm-x159-pipeline | Kimi-K3 | 159 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x159-tensor | Kimi-K3 | 159 | tensor | nvlink5 | infiniband_ndr | 372 | 1,361.33 us | 73.5 tok/s | 734.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 907.15 us |
| Kimi-K3/b200_sxm-x159-hybrid | Kimi-K3 | 159 | hybrid | nvlink5 | infiniband_ndr | 205 | 498.19 us | 200.7 tok/s | 2,007.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 19 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 44.02 us |
| Kimi-K3/b200_sxm-x159-nvl72-tensor | Kimi-K3 | 159 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x159-nvl72-hybrid | Kimi-K3 | 159 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x159-expert | Kimi-K3 | 159 | expert | nvlink5 | infiniband_ndr | 372 | 829.76 us | 120.5 tok/s | 1,205.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.81 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.95 us |
| Kimi-K3/b200_sxm-x159-nvl72-expert | Kimi-K3 | 159 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 833.73 us | 119.9 tok/s | 1,199.4 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.95 us |
| Kimi-K3/b200_sxm-x162-pipeline | Kimi-K3 | 162 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x162-tensor | Kimi-K3 | 162 | tensor | nvlink5 | infiniband_ndr | 372 | 1,361.71 us | 73.4 tok/s | 734.4 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 21 on infiniband_ndr (traversals 2.0) = 907.53 us |
| Kimi-K3/b200_sxm-x162-hybrid | Kimi-K3 | 162 | hybrid | nvlink5 | infiniband_ndr | 206 | 500.51 us | 199.8 tok/s | 1,998.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 20 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.33 us |
| Kimi-K3/b200_sxm-x162-nvl72-tensor | Kimi-K3 | 162 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x162-nvl72-hybrid | Kimi-K3 | 162 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x162-expert | Kimi-K3 | 162 | expert | nvlink5 | infiniband_ndr | 372 | 829.64 us | 120.5 tok/s | 1,205.3 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.79 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.85 us |
| Kimi-K3/b200_sxm-x162-nvl72-expert | Kimi-K3 | 162 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 833.63 us | 120.0 tok/s | 1,199.6 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.85 us |
| Kimi-K3/b200_sxm-x173-pipeline | Kimi-K3 | 173 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x173-tensor | Kimi-K3 | 173 | tensor | nvlink5 | infiniband_ndr | 372 | 1,362.05 us | 73.4 tok/s | 734.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 907.88 us |
| Kimi-K3/b200_sxm-x173-hybrid | Kimi-K3 | 173 | hybrid | nvlink5 | infiniband_ndr | 207 | 502.83 us | 198.9 tok/s | 1,988.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| Kimi-K3/b200_sxm-x173-nvl72-tensor | Kimi-K3 | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x173-nvl72-hybrid | Kimi-K3 | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x173-expert | Kimi-K3 | 173 | expert | nvlink5 | infiniband_ndr | 372 | 829.28 us | 120.6 tok/s | 1,205.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.77 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.51 us |
| Kimi-K3/b200_sxm-x173-nvl72-expert | Kimi-K3 | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 833.29 us | 120.0 tok/s | 1,200.1 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.51 us |
| Kimi-K3/b200_sxm-x193-pipeline | Kimi-K3 | 193 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x193-tensor | Kimi-K3 | 193 | tensor | nvlink5 | infiniband_ndr | 372 | 1,362.93 us | 73.4 tok/s | 733.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 908.75 us |
| Kimi-K3/b200_sxm-x193-hybrid | Kimi-K3 | 193 | hybrid | nvlink5 | infiniband_ndr | 210 | 509.78 us | 196.2 tok/s | 1,961.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 55.60 us |
| Kimi-K3/b200_sxm-x193-nvl72-tensor | Kimi-K3 | 193 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x193-nvl72-hybrid | Kimi-K3 | 193 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x193-expert | Kimi-K3 | 193 | expert | nvlink5 | infiniband_ndr | 372 | 828.73 us | 120.7 tok/s | 1,206.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.72 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.00 us |
| Kimi-K3/b200_sxm-x193-nvl72-expert | Kimi-K3 | 193 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 832.78 us | 120.1 tok/s | 1,200.8 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.00 us |
| Kimi-K3/b200_sxm-x195-pipeline | Kimi-K3 | 195 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x195-tensor | Kimi-K3 | 195 | tensor | nvlink5 | infiniband_ndr | 372 | 1,362.93 us | 73.4 tok/s | 733.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 908.75 us |
| Kimi-K3/b200_sxm-x195-hybrid | Kimi-K3 | 195 | hybrid | nvlink5 | infiniband_ndr | 210 | 509.78 us | 196.2 tok/s | 1,961.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 55.60 us |
| Kimi-K3/b200_sxm-x195-nvl72-tensor | Kimi-K3 | 195 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x195-nvl72-hybrid | Kimi-K3 | 195 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x195-expert | Kimi-K3 | 195 | expert | nvlink5 | infiniband_ndr | 372 | 828.68 us | 120.7 tok/s | 1,206.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.72 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.96 us |
| Kimi-K3/b200_sxm-x195-nvl72-expert | Kimi-K3 | 195 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 832.74 us | 120.1 tok/s | 1,200.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.96 us |
| Kimi-K3/b200_sxm-x201-pipeline | Kimi-K3 | 201 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x201-tensor | Kimi-K3 | 201 | tensor | nvlink5 | infiniband_ndr | 372 | 1,363.17 us | 73.4 tok/s | 733.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 26 on infiniband_ndr (traversals 2.0) = 909.00 us |
| Kimi-K3/b200_sxm-x201-hybrid | Kimi-K3 | 201 | hybrid | nvlink5 | infiniband_ndr | 211 | 512.10 us | 195.3 tok/s | 1,952.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 25 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 57.92 us |
| Kimi-K3/b200_sxm-x201-nvl72-tensor | Kimi-K3 | 201 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x201-nvl72-hybrid | Kimi-K3 | 201 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x201-expert | Kimi-K3 | 201 | expert | nvlink5 | infiniband_ndr | 372 | 828.54 us | 120.7 tok/s | 1,206.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.71 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.83 us |
| Kimi-K3/b200_sxm-x201-nvl72-expert | Kimi-K3 | 201 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 832.61 us | 120.1 tok/s | 1,201.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.83 us |
| Kimi-K3/b200_sxm-x231-pipeline | Kimi-K3 | 231 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x231-tensor | Kimi-K3 | 231 | tensor | nvlink5 | infiniband_ndr | 372 | 1,363.81 us | 73.3 tok/s | 733.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 909.63 us |
| Kimi-K3/b200_sxm-x231-hybrid | Kimi-K3 | 231 | hybrid | nvlink5 | infiniband_ndr | 214 | 519.05 us | 192.7 tok/s | 1,926.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 64.87 us |
| Kimi-K3/b200_sxm-x231-nvl72-tensor | Kimi-K3 | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,330.32 us | 75.2 tok/s | 751.7 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 875.15 us |
| Kimi-K3/b200_sxm-x231-nvl72-hybrid | Kimi-K3 | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 189 | 462.12 us | 216.4 tok/s | 2,164.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| Kimi-K3/b200_sxm-x231-expert | Kimi-K3 | 231 | expert | nvlink5 | infiniband_ndr | 372 | 827.95 us | 120.8 tok/s | 1,207.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.68 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.27 us |
| Kimi-K3/b200_sxm-x231-nvl72-expert | Kimi-K3 | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 830.60 us | 120.4 tok/s | 1,204.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 449.32 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.27 us |
| Kimi-K3/b200_sxm-x347-pipeline | Kimi-K3 | 347 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x347-tensor | Kimi-K3 | 347 | tensor | nvlink5 | infiniband_ndr | 372 | 1,365.69 us | 73.2 tok/s | 732.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 911.51 us |
| Kimi-K3/b200_sxm-x347-hybrid | Kimi-K3 | 347 | hybrid | nvlink5 | infiniband_ndr | 229 | 553.80 us | 180.6 tok/s | 1,805.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 99.62 us |
| Kimi-K3/b200_sxm-x347-nvl72-tensor | Kimi-K3 | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,338.32 us | 74.7 tok/s | 747.2 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 883.15 us |
| Kimi-K3/b200_sxm-x347-nvl72-hybrid | Kimi-K3 | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 190 | 464.43 us | 215.3 tok/s | 2,153.2 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| Kimi-K3/b200_sxm-x347-expert | Kimi-K3 | 347 | expert | nvlink5 | infiniband_ndr | 372 | 826.62 us | 121.0 tok/s | 1,209.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.58 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 380.04 us |
| Kimi-K3/b200_sxm-x347-nvl72-expert | Kimi-K3 | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 828.63 us | 120.7 tok/s | 1,206.8 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 448.59 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 380.04 us |
| Kimi-K3/b200_sxm-x371-pipeline | Kimi-K3 | 371 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x371-tensor | Kimi-K3 | 371 | tensor | nvlink5 | infiniband_ndr | 372 | 1,365.92 us | 73.2 tok/s | 732.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 47 on infiniband_ndr (traversals 2.0) = 911.75 us |
| Kimi-K3/b200_sxm-x371-hybrid | Kimi-K3 | 371 | hybrid | nvlink5 | infiniband_ndr | 232 | 560.75 us | 178.3 tok/s | 1,783.3 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 46 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 106.57 us |
| Kimi-K3/b200_sxm-x371-nvl72-tensor | Kimi-K3 | 371 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,343.65 us | 74.4 tok/s | 744.2 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 888.48 us |
| Kimi-K3/b200_sxm-x371-nvl72-hybrid | Kimi-K3 | 371 | hybrid | nvlink5_nvl72 | infiniband_ndr | 191 | 466.75 us | 214.2 tok/s | 2,142.5 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| Kimi-K3/b200_sxm-x371-expert | Kimi-K3 | 371 | expert | nvlink5 | infiniband_ndr | 372 | 826.45 us | 121.0 tok/s | 1,210.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.57 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 379.88 us |
| Kimi-K3/b200_sxm-x371-nvl72-expert | Kimi-K3 | 371 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 828.03 us | 120.8 tok/s | 1,207.7 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 448.15 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 379.88 us |
| Kimi-K3/b200_sxm-x520-pipeline | Kimi-K3 | 520 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x520-tensor | Kimi-K3 | 520 | tensor | nvlink5 | infiniband_ndr | 372 | 2,122.03 us | 47.1 tok/s | 471.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 65 on infiniband_ndr (traversals 4.0) = 1,667.85 us |
| Kimi-K3/b200_sxm-x520-hybrid | Kimi-K3 | 520 | hybrid | nvlink5 | infiniband_ndr | 250 | 602.45 us | 166.0 tok/s | 1,659.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 64 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 148.27 us |
| Kimi-K3/b200_sxm-x520-nvl72-tensor | Kimi-K3 | 520 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,350.32 us | 74.1 tok/s | 740.6 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 895.15 us |
| Kimi-K3/b200_sxm-x520-nvl72-hybrid | Kimi-K3 | 520 | hybrid | nvlink5_nvl72 | infiniband_ndr | 193 | 471.38 us | 212.1 tok/s | 2,121.4 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| Kimi-K3/b200_sxm-x520-expert | Kimi-K3 | 520 | expert | nvlink5 | infiniband_ndr | 372 | 825.74 us | 121.1 tok/s | 1,211.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.52 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 379.22 us |
| Kimi-K3/b200_sxm-x520-nvl72-expert | Kimi-K3 | 520 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 826.87 us | 120.9 tok/s | 1,209.4 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 447.65 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 379.22 us |
| Kimi-K3/b200_sxm-x1965-pipeline | Kimi-K3 | 1965 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x1965-tensor | Kimi-K3 | 1965 | tensor | nvlink5 | infiniband_ndr | 372 | 2,123.84 us | 47.1 tok/s | 470.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 246 on infiniband_ndr (traversals 4.0) = 1,669.66 us |
| Kimi-K3/b200_sxm-x1965-hybrid | Kimi-K3 | 1965 | hybrid | nvlink5 | infiniband_ndr | 278 | 667.32 us | 149.9 tok/s | 1,498.5 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 92 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 213.14 us |
| Kimi-K3/b200_sxm-x1965-nvl72-tensor | Kimi-K3 | 1965 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,364.60 us | 73.3 tok/s | 732.8 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 28 on infiniband_ndr (traversals 2.0) = 909.44 us |
| Kimi-K3/b200_sxm-x1965-nvl72-hybrid | Kimi-K3 | 1965 | hybrid | nvlink5_nvl72 | infiniband_ndr | 213 | 517.72 us | 193.2 tok/s | 1,931.6 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 27 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 62.55 us |
| Kimi-K3/b200_sxm-x1965-expert | Kimi-K3 | 1965 | expert | nvlink5 | infiniband_ndr | 372 | 824.45 us | 121.3 tok/s | 1,212.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.43 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 378.01 us |
| Kimi-K3/b200_sxm-x1965-nvl72-expert | Kimi-K3 | 1965 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 824.74 us | 121.3 tok/s | 1,212.5 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 446.72 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 378.01 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Kimi-K3 | 1 | wafer | wafer | Kimi-K3/ROM-N5-native-SRAMKV-wafer-hybrid-x12 | 554,700 | 1,868.6 | 0.003 | 933.2 (308,070) | 1,868.6 (554,700) | 2.00x | layer_fixed_latency |
| Kimi-K3 | 2 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,743.9 | 0.001 | — (—) | 1,743.9 (3,143,300) | — | layer_fixed_latency |
| Kimi-K3 | 4 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,743.9 | 0.001 | — (—) | 1,743.9 (3,143,300) | — | layer_fixed_latency |
| Kimi-K3 | 8 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,743.9 | 0.001 | — (—) | 1,743.9 (3,143,300) | — | layer_fixed_latency |
| Kimi-K3 | 16 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,743.9 | 0.001 | — (—) | 1,743.9 (3,143,300) | — | layer_fixed_latency |
| Kimi-K3 | 32 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,591.6 | 0.001 | — (—) | 1,591.6 (3,143,300) | — | layer_fixed_latency |
| Kimi-K3 | 64 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,322.5 | 0.000 | — (—) | 1,322.5 (3,143,300) | — | kv_read |
| Kimi-K3 | 256 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 531.0 | 0.000 | — (—) | 531.0 (3,143,300) | — | kv_read |
| Kimi-K3 | 1024 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 152.1 | 0.000 | — (—) | 152.1 (3,143,300) | — | kv_read |
| Kimi-K3 | 4096 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 39.3 | 0.000 | — (—) | 39.3 (3,143,300) | — | kv_read |

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
| Kimi-K3 | 896 | 1,614.3 MB | 275.4 mm2 | 49.57 mm2 (18.0%) | 246,743 mm2 | 44,414 mm2 | 266,259 mm2 = 326.7 reticles |

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
| Kimi-K3 | 1 | sram | 160,869.3 | 26,113.2 | 26,113.2 | 6.16x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 2 | sram | 160,869.3 | 26,113.2 | 26,113.2 | 6.16x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 4 | sram | 160,869.3 | 26,113.2 | 26,113.2 | 6.16x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 8 | sram | 160,869.3 | 26,113.2 | 26,113.2 | 6.16x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 16 | sram | 160,869.3 | 26,113.2 | 26,113.2 | 6.16x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 32 | sram | 160,869.3 | 26,113.2 | 26,113.2 | 6.16x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 64 | sram | 160,869.3 | 26,113.2 | 39,108.2 | 6.16x | 1.50x | kv_read | weight_read | weight_read |
| Kimi-K3 | 256 | sram | 160,869.3 | 26,113.2 | 89,681.5 | 6.16x | 3.43x | kv_read | weight_read | weight_read |
| Kimi-K3 | 1024 | sram | 160,869.3 | 26,113.2 | 135,145.4 | 6.16x | 5.18x | kv_read | weight_read | kv_read |
| Kimi-K3 | 4096 | sram | 160,869.3 | 26,113.2 | 156,545.0 | 6.16x | 5.99x | kv_read | weight_read | kv_read |
| Kimi-K3 | 1 | rom | 158,990.8 | 159,253.8 | 159,253.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 2 | rom | 158,990.8 | 159,253.8 | 159,253.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 4 | rom | 158,990.8 | 159,253.8 | 159,253.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 8 | rom | 158,990.8 | 159,253.8 | 159,253.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 16 | rom | 158,990.8 | 159,253.8 | 159,253.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 32 | rom | 158,990.8 | 159,253.8 | 159,253.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 64 | rom | 158,990.8 | 159,253.8 | 159,253.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 256 | rom | 158,990.8 | 159,253.8 | 159,253.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 1024 | rom | 158,990.8 | 159,253.8 | 159,253.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 4096 | rom | 159,074.2 | 159,353.0 | 159,313.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| Kimi-K3 | 1 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 160,869.3 | 0.051 | kv_read | 1.00x |
| Kimi-K3 | 1 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 8.86 | 1.00 | 158,990.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 1 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 1 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 1 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 1 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 2 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 160,869.3 | 0.051 | kv_read | 1.00x |
| Kimi-K3 | 2 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 8.86 | 1.00 | 158,990.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 2 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 2 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 2 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 2 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 4 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 160,869.3 | 0.051 | kv_read | 1.00x |
| Kimi-K3 | 4 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 8.86 | 1.00 | 158,990.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 4 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 4 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 4 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 4 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 8 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 160,869.3 | 0.051 | kv_read | 1.00x |
| Kimi-K3 | 8 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 8.86 | 1.00 | 158,990.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 8 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 8 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 8 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 8 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 16 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 160,869.3 | 0.051 | kv_read | 1.00x |
| Kimi-K3 | 16 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 8.86 | 1.00 | 158,990.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 16 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 16 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 16 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 16 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 32 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 160,869.3 | 0.051 | kv_read | 1.00x |
| Kimi-K3 | 32 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 8.86 | 1.00 | 158,990.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 32 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 32 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 32 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 32 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 64 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 160,869.3 | 0.051 | kv_read | 1.00x |
| Kimi-K3 | 64 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 8.86 | 1.00 | 158,990.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 64 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 64 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 64 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68-perregion | 3,143,300 | 1.00 | 1.77 | 39,108.2 | 0.012 | weight_read | 0.24x |
| Kimi-K3 | 64 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 256 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 160,869.3 | 0.051 | kv_read | 1.00x |
| Kimi-K3 | 256 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 8.86 | 1.00 | 158,990.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 256 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 256 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 256 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68-perregion | 3,143,300 | 1.00 | 2.97 | 89,681.5 | 0.029 | weight_read | 0.56x |
| Kimi-K3 | 256 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 1024 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 160,869.3 | 0.051 | kv_read | 1.00x |
| Kimi-K3 | 1024 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 8.86 | 1.00 | 158,990.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 1024 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 1024 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 1024 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68-perregion | 3,143,300 | 1.00 | 3.99 | 135,145.4 | 0.043 | kv_read | 0.84x |
| Kimi-K3 | 1024 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 29.78 | 1.00 | 159,253.8 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 4096 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 160,869.3 | 0.051 | kv_read | 1.00x |
| Kimi-K3 | 4096 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 8.86 | 1.00 | 159,074.2 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 4096 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.06 | 26,113.2 | 0.008 | weight_read | 0.16x |
| Kimi-K3 | 4096 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 29.78 | 1.06 | 159,353.0 | 0.051 | kv_read | 0.99x |
| Kimi-K3 | 4096 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x68-perregion | 3,143,300 | 1.00 | 4.21 | 156,545.0 | 0.050 | kv_read | 0.97x |
| Kimi-K3 | 4096 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 29.78 | 1.02 | 159,313.8 | 0.051 | kv_read | 0.99x |

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
| Kimi-K3 | 1 | 135 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 2 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 4 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 8 | 3,857 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 16 | 3,857 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 32 | 3,857 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 64 | 3,857 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 256 | 3,857 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 1024 | 3,857 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 4096 | 3,857 | 1.06 | 1.001 | 1.015 | 1.01x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| Kimi-K3 | 1 | 29 | 12.46 | 6.68 | 1.87x |
| Kimi-K3 | 2 | 29 | 19.47 | 8.87 | 2.19x |
| Kimi-K3 | 4 | 29 | 25.74 | 11.34 | 2.27x |
| Kimi-K3 | 8 | 29 | 28.57 | 13.90 | 2.06x |
| Kimi-K3 | 16 | 29 | 28.99 | 16.33 | 1.78x |
| Kimi-K3 | 32 | 29 | 29.00 | 18.39 | 1.58x |
| Kimi-K3 | 64 | 29 | 29.00 | 19.91 | 1.46x |
| Kimi-K3 | 1 | 58 | 14.09 | 8.11 | 1.74x |
| Kimi-K3 | 2 | 58 | 24.59 | 11.50 | 2.14x |
| Kimi-K3 | 4 | 58 | 38.37 | 15.54 | 2.47x |
| Kimi-K3 | 8 | 58 | 50.84 | 20.16 | 2.52x |
| Kimi-K3 | 16 | 58 | 56.83 | 24.95 | 2.28x |
| Kimi-K3 | 32 | 58 | 57.94 | 29.37 | 1.97x |
| Kimi-K3 | 64 | 58 | 58.00 | 32.85 | 1.77x |
| Kimi-K3 | 256 | 58 | 58.00 | 35.61 | 1.63x |
| Kimi-K3 | 1 | 69 | 14.37 | 8.48 | 1.70x |
| Kimi-K3 | 2 | 69 | 25.57 | 12.19 | 2.10x |
| Kimi-K3 | 4 | 69 | 41.21 | 16.67 | 2.47x |
| Kimi-K3 | 8 | 69 | 57.08 | 21.91 | 2.60x |
| Kimi-K3 | 16 | 69 | 66.39 | 27.48 | 2.42x |
| Kimi-K3 | 32 | 69 | 68.78 | 32.73 | 2.10x |
| Kimi-K3 | 64 | 69 | 68.99 | 36.91 | 1.87x |
| Kimi-K3 | 256 | 69 | 69.00 | 40.29 | 1.71x |
| Kimi-K3 | 1 | 74 | 14.48 | 8.63 | 1.68x |
| Kimi-K3 | 2 | 74 | 25.93 | 12.46 | 2.08x |
| Kimi-K3 | 4 | 74 | 42.30 | 17.13 | 2.47x |
| Kimi-K3 | 8 | 74 | 59.59 | 22.64 | 2.63x |
| Kimi-K3 | 16 | 74 | 70.51 | 28.54 | 2.47x |
| Kimi-K3 | 32 | 74 | 73.65 | 34.15 | 2.16x |
| Kimi-K3 | 64 | 74 | 73.98 | 38.65 | 1.91x |
| Kimi-K3 | 256 | 74 | 74.00 | 42.31 | 1.75x |
| Kimi-K3 | 1 | 87 | 14.69 | 8.99 | 1.63x |
| Kimi-K3 | 2 | 87 | 26.70 | 13.07 | 2.04x |
| Kimi-K3 | 4 | 87 | 44.67 | 18.18 | 2.46x |
| Kimi-K3 | 8 | 87 | 65.34 | 24.36 | 2.68x |
| Kimi-K3 | 16 | 87 | 80.50 | 31.08 | 2.59x |
| Kimi-K3 | 32 | 87 | 86.07 | 37.58 | 2.29x |
| Kimi-K3 | 64 | 87 | 86.93 | 42.89 | 2.03x |
| Kimi-K3 | 256 | 87 | 87.00 | 47.26 | 1.84x |
| Kimi-K3 | 1 | 116 | 15.01 | 9.67 | 1.55x |
| Kimi-K3 | 2 | 116 | 27.85 | 14.10 | 1.98x |
| Kimi-K3 | 4 | 116 | 48.36 | 20.08 | 2.41x |
| Kimi-K3 | 8 | 116 | 75.06 | 27.51 | 2.73x |
| Kimi-K3 | 16 | 116 | 99.38 | 35.87 | 2.77x |
| Kimi-K3 | 32 | 116 | 112.13 | 44.21 | 2.54x |
| Kimi-K3 | 64 | 116 | 115.43 | 51.21 | 2.25x |
| Kimi-K3 | 256 | 116 | 115.95 | 57.08 | 2.03x |
| Kimi-K3 | 1024 | 116 | 115.95 | 57.24 | 2.03x |
| Kimi-K3 | 1 | 144 | 15.19 | 10.20 | 1.49x |
| Kimi-K3 | 2 | 144 | 28.55 | 14.81 | 1.93x |
| Kimi-K3 | 4 | 144 | 50.72 | 21.59 | 2.35x |
| Kimi-K3 | 8 | 144 | 81.72 | 29.99 | 2.73x |
| Kimi-K3 | 16 | 144 | 113.86 | 39.67 | 2.87x |
| Kimi-K3 | 32 | 144 | 134.66 | 49.60 | 2.72x |
| Kimi-K3 | 64 | 144 | 141.99 | 58.10 | 2.44x |
| Kimi-K3 | 256 | 144 | 143.70 | 65.36 | 2.20x |
| Kimi-K3 | 1024 | 144 | 143.72 | 65.56 | 2.19x |
| Kimi-K3 | 1 | 145 | 15.20 | 10.22 | 1.49x |
| Kimi-K3 | 2 | 145 | 28.57 | 14.83 | 1.93x |
| Kimi-K3 | 4 | 145 | 50.79 | 21.64 | 2.35x |
| Kimi-K3 | 8 | 145 | 81.92 | 30.07 | 2.72x |
| Kimi-K3 | 16 | 145 | 114.32 | 39.80 | 2.87x |
| Kimi-K3 | 32 | 145 | 135.42 | 49.78 | 2.72x |
| Kimi-K3 | 64 | 145 | 142.92 | 58.33 | 2.45x |
| Kimi-K3 | 256 | 145 | 144.69 | 65.64 | 2.20x |
| Kimi-K3 | 1024 | 145 | 144.71 | 65.84 | 2.20x |
| Kimi-K3 | 1 | 159 | 15.27 | 10.45 | 1.46x |
| Kimi-K3 | 2 | 159 | 28.83 | 15.13 | 1.91x |
| Kimi-K3 | 4 | 159 | 51.68 | 22.31 | 2.32x |
| Kimi-K3 | 8 | 159 | 84.56 | 31.16 | 2.71x |
| Kimi-K3 | 16 | 159 | 120.41 | 41.47 | 2.90x |
| Kimi-K3 | 32 | 159 | 145.65 | 52.18 | 2.79x |
| Kimi-K3 | 64 | 159 | 155.68 | 61.44 | 2.53x |
| Kimi-K3 | 256 | 159 | 158.41 | 69.41 | 2.28x |
| Kimi-K3 | 1024 | 159 | 158.44 | 69.63 | 2.28x |
| Kimi-K3 | 1 | 162 | 15.28 | 10.50 | 1.46x |
| Kimi-K3 | 2 | 162 | 28.88 | 15.19 | 1.90x |
| Kimi-K3 | 4 | 162 | 51.85 | 22.44 | 2.31x |
| Kimi-K3 | 8 | 162 | 85.08 | 31.39 | 2.71x |
| Kimi-K3 | 16 | 162 | 121.63 | 41.81 | 2.91x |
| Kimi-K3 | 32 | 162 | 147.75 | 52.68 | 2.80x |
| Kimi-K3 | 64 | 162 | 158.36 | 62.08 | 2.55x |
| Kimi-K3 | 256 | 162 | 161.33 | 70.19 | 2.30x |
| Kimi-K3 | 1024 | 162 | 161.37 | 70.41 | 2.29x |
| Kimi-K3 | 1 | 173 | 15.32 | 10.66 | 1.44x |
| Kimi-K3 | 2 | 173 | 29.05 | 15.40 | 1.89x |
| Kimi-K3 | 4 | 173 | 52.45 | 22.93 | 2.29x |
| Kimi-K3 | 8 | 173 | 86.86 | 32.17 | 2.70x |
| Kimi-K3 | 16 | 173 | 125.90 | 43.04 | 2.93x |
| Kimi-K3 | 32 | 173 | 155.23 | 54.44 | 2.85x |
| Kimi-K3 | 64 | 173 | 168.05 | 64.38 | 2.61x |
| Kimi-K3 | 256 | 173 | 171.99 | 72.99 | 2.36x |
| Kimi-K3 | 1024 | 173 | 172.04 | 73.22 | 2.35x |
| Kimi-K3 | 1 | 193 | 15.39 | 10.94 | 1.41x |
| Kimi-K3 | 2 | 193 | 29.32 | 15.76 | 1.86x |
| Kimi-K3 | 4 | 193 | 53.37 | 23.74 | 2.25x |
| Kimi-K3 | 8 | 193 | 89.68 | 33.46 | 2.68x |
| Kimi-K3 | 16 | 193 | 132.85 | 45.11 | 2.94x |
| Kimi-K3 | 32 | 193 | 167.89 | 57.43 | 2.92x |
| Kimi-K3 | 64 | 193 | 185.02 | 68.30 | 2.71x |
| Kimi-K3 | 256 | 193 | 191.08 | 77.80 | 2.46x |
| Kimi-K3 | 1024 | 193 | 191.16 | 78.06 | 2.45x |
| Kimi-K3 | 1 | 195 | 15.40 | 10.97 | 1.40x |
| Kimi-K3 | 2 | 195 | 29.34 | 15.79 | 1.86x |
| Kimi-K3 | 4 | 195 | 53.45 | 23.82 | 2.24x |
| Kimi-K3 | 8 | 195 | 89.93 | 33.58 | 2.68x |
| Kimi-K3 | 16 | 195 | 133.49 | 45.31 | 2.95x |
| Kimi-K3 | 32 | 195 | 169.10 | 57.72 | 2.93x |
| Kimi-K3 | 64 | 195 | 186.67 | 68.68 | 2.72x |
| Kimi-K3 | 256 | 195 | 192.96 | 78.26 | 2.47x |
| Kimi-K3 | 1024 | 195 | 193.05 | 78.52 | 2.46x |
| Kimi-K3 | 1 | 201 | 15.42 | 11.05 | 1.40x |
| Kimi-K3 | 2 | 201 | 29.41 | 15.89 | 1.85x |
| Kimi-K3 | 4 | 201 | 53.69 | 24.04 | 2.23x |
| Kimi-K3 | 8 | 201 | 90.68 | 33.94 | 2.67x |
| Kimi-K3 | 16 | 201 | 135.37 | 45.89 | 2.95x |
| Kimi-K3 | 32 | 201 | 172.64 | 58.56 | 2.95x |
| Kimi-K3 | 64 | 201 | 191.56 | 69.79 | 2.74x |
| Kimi-K3 | 256 | 201 | 198.59 | 79.63 | 2.49x |
| Kimi-K3 | 1024 | 201 | 198.70 | 79.90 | 2.49x |
| Kimi-K3 | 1 | 231 | 15.49 | 11.40 | 1.36x |
| Kimi-K3 | 2 | 231 | 29.69 | 16.36 | 1.81x |
| Kimi-K3 | 4 | 231 | 54.71 | 25.06 | 2.18x |
| Kimi-K3 | 8 | 231 | 93.92 | 35.53 | 2.64x |
| Kimi-K3 | 16 | 231 | 143.75 | 48.55 | 2.96x |
| Kimi-K3 | 32 | 231 | 188.94 | 62.52 | 3.02x |
| Kimi-K3 | 64 | 231 | 214.85 | 75.04 | 2.86x |
| Kimi-K3 | 256 | 231 | 226.08 | 86.12 | 2.63x |
| Kimi-K3 | 1024 | 231 | 226.26 | 86.42 | 2.62x |
| Kimi-K3 | 1 | 347 | 15.66 | 12.40 | 1.26x |
| Kimi-K3 | 2 | 347 | 30.35 | 17.89 | 1.70x |
| Kimi-K3 | 4 | 347 | 57.11 | 27.69 | 2.06x |
| Kimi-K3 | 8 | 347 | 101.77 | 40.21 | 2.53x |
| Kimi-K3 | 16 | 347 | 165.42 | 56.60 | 2.92x |
| Kimi-K3 | 32 | 347 | 235.25 | 74.67 | 3.15x |
| Kimi-K3 | 64 | 347 | 287.88 | 91.49 | 3.15x |
| Kimi-K3 | 256 | 347 | 320.18 | 106.82 | 3.00x |
| Kimi-K3 | 1024 | 347 | 320.86 | 107.24 | 2.99x |
| Kimi-K3 | 1 | 371 | 15.68 | 12.55 | 1.25x |
| Kimi-K3 | 2 | 371 | 30.44 | 18.17 | 1.68x |
| Kimi-K3 | 4 | 371 | 57.43 | 28.07 | 2.05x |
| Kimi-K3 | 8 | 371 | 102.85 | 41.04 | 2.51x |
| Kimi-K3 | 16 | 371 | 168.55 | 58.02 | 2.91x |
| Kimi-K3 | 32 | 371 | 242.43 | 76.78 | 3.16x |
| Kimi-K3 | 64 | 371 | 300.11 | 94.33 | 3.18x |
| Kimi-K3 | 256 | 371 | 337.15 | 110.45 | 3.05x |
| Kimi-K3 | 1024 | 371 | 337.96 | 110.91 | 3.05x |
| Kimi-K3 | 1 | 520 | 15.77 | 13.28 | 1.19x |
| Kimi-K3 | 2 | 520 | 30.80 | 19.68 | 1.56x |
| Kimi-K3 | 4 | 520 | 58.77 | 29.77 | 1.97x |
| Kimi-K3 | 8 | 520 | 107.47 | 45.60 | 2.36x |
| Kimi-K3 | 16 | 520 | 182.40 | 65.11 | 2.80x |
| Kimi-K3 | 32 | 520 | 275.78 | 87.61 | 3.15x |
| Kimi-K3 | 64 | 520 | 360.27 | 109.33 | 3.30x |
| Kimi-K3 | 256 | 520 | 425.73 | 129.74 | 3.28x |
| Kimi-K3 | 1024 | 520 | 427.33 | 130.32 | 3.28x |
| Kimi-K3 | 4096 | 520 | 427.33 | 130.32 | 3.28x |
| Kimi-K3 | 1 | 1965 | 15.94 | 15.11 | 1.06x |
| Kimi-K3 | 2 | 1965 | 31.47 | 26.02 | 1.21x |
| Kimi-K3 | 4 | 1965 | 61.34 | 38.37 | 1.60x |
| Kimi-K3 | 8 | 1965 | 116.70 | 58.99 | 1.98x |
| Kimi-K3 | 16 | 1965 | 212.12 | 94.68 | 2.24x |
| Kimi-K3 | 32 | 1965 | 355.96 | 130.80 | 2.72x |
| Kimi-K3 | 64 | 1965 | 526.86 | 175.73 | 3.00x |
| Kimi-K3 | 256 | 1965 | 714.03 | 215.77 | 3.31x |
| Kimi-K3 | 1024 | 1965 | 719.67 | 217.04 | 3.32x |
| Kimi-K3 | 4096 | 1965 | 719.68 | 217.04 | 3.32x |

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
| gpu | Kimi-K3 | 1 | 2,180.10 | 62.9% |
| rom | Kimi-K3 | 1 | 286.19 | 67.7% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| Kimi-K3 | sram | interleaved | 128 B | 1.00x |
| Kimi-K3 | hbm | interleaved | 32 B | 1.00x |

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
| Kimi-K3 | 1 | 135 | 95.79% | 1,236.96 | 9.57 |
| Kimi-K3 | 2 | 3 | 16.63% | 271.97 | 9.57 |
| Kimi-K3 | 4 | 3 | 16.63% | 271.97 | 9.57 |

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
| Kimi-K3 | 1 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 41.7 | 160,869.3 |
| Kimi-K3 | 2 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 41.7 | 160,869.3 |
| Kimi-K3 | 4 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 41.7 | 160,869.3 |
| Kimi-K3 | 8 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 41.7 | 160,869.3 |
| Kimi-K3 | 16 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 41.7 | 160,869.3 |
| Kimi-K3 | 32 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 41.7 | 160,869.3 |
| Kimi-K3 | 64 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 41.7 | 160,869.3 |
| Kimi-K3 | 256 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 41.7 | 160,869.3 |
| Kimi-K3 | 1024 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 41.7 | 160,869.3 |
| Kimi-K3 | 4096 | 1.90% | 138.6 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 39.3 | 160,869.3 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 25 |
| gpu | infeasible | 149 |
| gpu | layer_fixed_latency | 139 |
| gpu | link_latency | 587 |
| gpu | thermal | 215 |
| gpu | weight_read | 185 |
| rom | compute | 49 |
| rom | infeasible | 1743 |
| rom | kv_read | 58 |
| rom | layer_fixed_latency | 135 |
| rom | link_latency | 97 |
| rom | weight_read | 48 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 149 |
| rom | CAPACITY | 1743 |

## Mechanical consistency audit

**FAIL** over 50,640 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x284', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x312', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x318', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x319', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x378', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x383', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x395', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x284', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x312', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x318', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x319', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x378', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x383', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x395', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x284', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x312', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x318', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x319', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x378', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x383', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x395', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x284', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x312', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x318', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x319', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x378', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x383', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x395', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x6', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x8', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x12', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x18', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x284', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x312', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x318', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x319', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x378', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x383', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x395', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x6', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x8', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x12', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x18', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x284', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x312', 'Kimi-K3', 1)

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

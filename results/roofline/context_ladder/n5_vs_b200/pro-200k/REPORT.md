# Area-constrained roofline: n5_vs_b200-pro-200k

> CONTEXT-LADDER RUNG of n5_vs_b200: DeepSeek-V4-Pro-0813 at 200,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 55x (ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream, 568 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 4 devices. On the GPU side the correction reaches 5x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 29 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Pro-0813 takes 3 x 46,225 mm2 (138,675 mm2, wafer, KV in SRAM) at 1,943 tok/s per user and 14 tok/s per 1,000 mm2, holding 1 session, against 87 copies of one unified HBM die at the same silicon: 4.8x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Pro-0813 on 184,900 mm2 of ROM silicon at 2,133 tok/s per user against 185,600 mm2 of b200_sxm-x116-nvl72-hybrid at 412 tok/s: **5.2x**, ROM binding on `layer_fixed_latency` and the GPU on `layer_fixed_latency`. It holds 1 resident session against the GPU cluster's 9,050. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 3.01x to it.** At 214,345 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 137.42 tok/s and the same silicon running hybrid delivers 413 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.00x (DeepSeek-V4-Pro-0813, ROM binding on `link_latency`) to 5.18x (DeepSeek-V4-Pro-0813, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Pro-0813 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 92 to 14,865 tok/s, and its rate with every slot occupied from 14,589 to 14,865. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 158 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 896 us over NVLink, capping per-user decode at 1,116 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 316.2 us and cap it at 3,163 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 9 of 10 operating points and an array 1; on tokens per second per square millimetre the same points go 9 to the array and 1 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 48 of 4423 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 31.2x of aggregate throughput (DeepSeek-V4-Pro-0813). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 15.35x, on DeepSeek-V4-Pro-0813 at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 60 of 4,423 feasible points (1.4%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DSV4-Pro/b200_sxm-x56-pipeline` at batch 4096 on 89,600 mm2, throttled 1.06x from 10 to 10 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 93% weight read against 93.4% weight read. The ROM sweep is not what melts it.


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

### DeepSeek-V4-Pro-0813 at 200,000 tokens

**Recommended: `ROM-N5-native-SRAMKV-wafer-hybrid-x3`** -- 3 x 46,225 mm2 wafers, 138,675 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **1,942.9 tok/s per user** (0.51 ms/token), binding on `layer_fixed_latency`
- **14.0 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 1,943 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 8,131 W at 0.059 W/mm2, 4,184.9 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 87 copies of one unified HBM die -- `b200_sxm-x87-nvl72-hybrid`, 139,200 mm2, area ratio 0.9962 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 138,675 | 139,200 | 0.9962 |
| user tok/s | 1,942.9 | 406.7 | 4.78x |
| aggregate tok/s | 1,943 | 813 | 0.16x |
| resident sessions | 1 | 6,675 | -- |
| J/token | 4.1849 | 79.1946 | 18.9x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 6,675 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x134-nvl72-hybrid` at 214,400 mm2 and 413.2 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,132.7 | 11.5 | 1 | 5.18x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,132.7 | 11.5 | 1 | 5.18x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-hybrid-x147` | 119,805 | 1,048.6 | 8.8 | 1 | 2.60x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 1,942.9 | 14.0 | 1 | 4.78x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 1,942.9 | 14.0 | -- | 14.0 | ACCEPT |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,132.7 | 11.5 | 4.1 | 14.0 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x3` **<-- recommended** | 138,675 | 3 | 1,942.9 | 1,943 | 14.0 | 1 | `layer_fixed_latency` | 8,131 | 4,184.9 | `b200_sxm-x87-nvl72-hybrid` | 4.78x |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 4 | 2,132.7 | 2,133 | 11.5 | 1 | `layer_fixed_latency` | 14,837 | 6,957.0 | `b200_sxm-x116-nvl72-hybrid` | 5.18x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 276 | densest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x180` | 146,700 | 1,742.6 | 11.9 | 1 |
| array | 276 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 1,967.0 | 7.8 | 15,769 |
| array | 276 | smallest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x147` | 119,805 | 1,048.6 | 8.8 | 1 |
| wafer | 42 | densest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 1,942.9 | 14.0 | 1 |
| wafer | 42 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,132.7 | 11.5 | 1 |
| wafer | 42 | smallest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 1,942.9 | 14.0 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 1,967.0 | 76,711 | 15,769 | 33,966 | 14,689.6 | `layer_fixed_latency` | `b200_sxm-x157-nvl72-hybrid` | 409.5 | 12,409 | 138,591.4 | 0.999 | 4.80x | 9.4x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,132.7 | 2,133 | 1 | 14,837 | 6,957.0 | `layer_fixed_latency` | `b200_sxm-x116-nvl72-hybrid` | 411.6 | 9,050 | 102,983.8 | 0.996 | 5.18x | 14.8x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-hybrid-x235` | 191,525 | 1,920.3 | 1,920 | 1 | 15,794 | 8,224.8 | `layer_fixed_latency` | `b200_sxm-x120-nvl72-hybrid` | 412.1 | 9,378 | 106,265.0 | 0.998 | 4.66x | 12.9x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,132.7 | -- | 1 | -- | 6,957.0 | -- | -- | -- | -- | -- | 1.036 | 1.11x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 1,967.0 | 76,711 | 15,769 | 33,966 | 7,378.7 | `layer_fixed_latency` | `b200_sxm-x157-nvl72-hybrid` | 409.5 | 12,409 | 71,409.4 | 0.999 | 4.80x | 9.7x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 462,250 | 2,080.6 | 74,903 | 4,403 | 46,082 | 9,920.3 | `layer_fixed_latency` | `b200_sxm-x289-nvl72-hybrid` | 410.0 | 23,222 | 127,745.3 | 1.000 | 5.08x | 12.9x |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 1,967.0 | 76,711 | 15,769 | 33,966 | 3,723.3 | `layer_fixed_latency` | `b200_sxm-x157-nvl72-hybrid` | 400.8 | 12,409 | 37,833.6 | 0.999 | 4.91x | 10.2x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 462,250 | 2,080.6 | 74,903 | 4,403 | 46,082 | 4,994.1 | `layer_fixed_latency` | `b200_sxm-x289-nvl72-hybrid` | 410.0 | 23,222 | 65,986.4 | 1.000 | 5.08x | 13.2x |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 1,967.0 | 76,711 | 15,769 | 33,966 | 1,895.6 | `layer_fixed_latency` | `b200_sxm-x157-nvl72-hybrid` | 397.3 | 12,409 | 21,538.2 | 0.999 | 4.95x | 11.4x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 462,250 | 2,080.6 | 74,903 | 4,403 | 46,082 | 2,531.0 | `layer_fixed_latency` | `b200_sxm-x289-nvl72-hybrid` | 396.2 | 23,222 | 36,178.2 | 1.000 | 5.25x | 14.3x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 1,967.0 | 76,711 | 15,769 | 33,966 | 981.7 | `layer_fixed_latency` | `b200_sxm-x157-nvl72-hybrid` | 377.8 | 12,409 | 12,266.5 | 0.999 | 5.21x | 12.5x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 462,250 | 2,080.6 | 74,903 | 4,403 | 46,082 | 1,299.4 | `layer_fixed_latency` | `b200_sxm-x289-nvl72-hybrid` | 393.2 | 23,222 | 20,323.9 | 1.000 | 5.29x | 15.6x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 1,967.0 | 76,711 | 15,769 | 33,966 | 524.8 | `layer_fixed_latency` | `b200_sxm-x157-nvl72-hybrid` | 334.3 | 12,409 | 7,408.8 | 0.999 | 5.88x | 14.1x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 462,250 | 2,080.6 | 74,903 | 4,403 | 46,082 | 683.6 | `layer_fixed_latency` | `b200_sxm-x289-nvl72-hybrid` | 371.0 | 23,222 | 11,606.0 | 1.000 | 5.61x | 17.0x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x308` | 251,020 | 1,953.8 | 150,442 | 15,769 | 38,970 | 297.9 | `layer_fixed_latency` | `b200_sxm-x157-nvl72-hybrid` | 281.9 | 12,409 | 5,315.5 | 0.999 | 6.93x | 17.8x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 462,250 | 1,998.4 | 141,890 | 4,403 | 50,628 | 388.4 | `layer_fixed_latency` | `b200_sxm-x289-nvl72-hybrid` | 326.0 | 23,222 | 7,074.8 | 1.000 | 6.13x | 18.2x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 1,320.2 | 337,984 | 17,407 | 54,977 | 162.7 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 165.2 | 13,720 | 3,276.2 | 1.001 | 7.99x | 20.1x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,479.2 | 378,676 | 5,283 | 73,845 | 195.0 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 227.4 | 27,973 | 3,931.5 | 0.999 | 6.50x | 20.2x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 277,100 | 529.2 | 541,885 | 17,407 | 66,720 | 123.1 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 71.3 | 13,720 | 2,148.8 | 1.001 | 7.42x | 17.5x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 671.5 | 687,650 | 5,283 | 93,939 | 136.6 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 113.2 | 27,973 | 2,588.4 | 0.999 | 5.93x | 18.9x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 277,100 | 149.7 | 613,050 | 17,407 | 69,719 | 113.7 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 28.9 | 13,720 | 1,314.7 | 1.001 | 5.18x | 11.6x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 554,700 | 198.8 | 814,286 | 5,283 | 119,417 | 146.7 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 44.2 | 27,973 | 1,750.7 | 0.999 | 4.50x | 11.9x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | wafer | SRAM | 1 |
| 2-16 | `ROM-N5-native-HBMKV-array-hw-hybrid-x193` | 157,295 | array | HBM | 9,881 |
| 32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x208` | 169,520 | array | HBM | 10,649 |
| 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x244-romfill` | 198,860 | array | HBM | 12,492 |
| 256 | `ROM-N5-native-HBMKV-array-hw-pipeline-x260-romfill` | 211,900 | array | HBM | 13,311 |
| 1024-4096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x340` | 277,100 | array | HBM | 17,407 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Pro-0813 | HBM | rom | 158, 162, 170, 193, 208, 227, 231, 244, 260, 261, 308, 340 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 158, 162, 170, 193, 208, 227, 231, 263, 295, 296, 308, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 147, 156, 170, 180, 197, 216, 221, 227, 235, 288, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 147, 156, 170, 180, 197, 216, 221, 227, 235, 288, 340 |

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
| DeepSeek-V4-Pro-0813 | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 1 | 16 on `rom_wafer_express` | 5.51 | one_shot | 358.97 | 67.02 | 97.78 | 42.68 | 1,942.9 |
| DeepSeek-V4-Pro-0813 | `b200_sxm-x87-nvl72-hybrid` | 1 | 64 | 6.51 | measured_floor | 1,259.70 | 1,081.12 | 142.40 | 318.46 | 406.7 |
| DeepSeek-V4-Pro-0813 | `b200_sxm-x87-nvl72-hybrid` | 64 | 8 | 5.51 | measured_floor | 1,263.60 | 1,380.72 | 1,981.41 | 355.42 | 231.5 |

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

- **60 of 4,423 feasible points (1.4%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 60.
- By area class: wafer (>=40,000 mm2) 60.
- By KV store: hbm 60.
- By batch: B=256 4, B=1024 28, B=4096 28.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 43% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 256 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 2,155 | 60 | 38.1% | 100.0% | 0.625 | 92% |
| rom | wafer (>=40,000 mm2) | 2,268 | 0 | 21.0% | 55.8% | 0.279 | 92% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DSV4-Pro/b200_sxm-x56-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 89,600 | hbm | 1.058x | 56,000.0 / 56,000.0 W | 35% | 9.8 | 10.4 |
| `DSV4-Pro/b200_sxm-x58-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 92,800 | hbm | 1.058x | 58,000.0 / 58,000.0 W | 35% | 10.0 | 10.6 |
| `DSV4-Pro/b200_sxm-x75-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 120,000 | hbm | 1.057x | 75,000.0 / 75,000.0 W | 35% | 11.6 | 12.3 |
| `DSV4-Pro/b200_sxm-x79-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 126,400 | hbm | 1.057x | 79,000.0 / 79,000.0 W | 35% | 12.0 | 12.7 |
| `DSV4-Pro/b200_sxm-x80-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 128,000 | hbm | 1.057x | 80,000.0 / 80,000.0 W | 35% | 12.1 | 12.8 |
| `DSV4-Pro/b200_sxm-x83-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 132,800 | hbm | 1.057x | 83,000.0 / 83,000.0 W | 35% | 12.4 | 13.1 |
| `DSV4-Pro/b200_sxm-x87-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 139,200 | hbm | 1.057x | 87,000.0 / 87,000.0 W | 35% | 12.8 | 13.5 |
| `DSV4-Pro/b200_sxm-x92-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 147,200 | hbm | 1.057x | 92,000.0 / 92,000.0 W | 35% | 13.3 | 14.0 |
| `DSV4-Pro/b200_sxm-x98-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 156,800 | hbm | 1.056x | 98,000.0 / 98,000.0 W | 35% | 13.8 | 14.6 |
| `DSV4-Pro/b200_sxm-x100-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 160,000 | hbm | 1.056x | 100,000.0 / 100,000.0 W | 35% | 14.0 | 14.8 |
| `DSV4-Pro/b200_sxm-x29-pipeline` | DeepSeek-V4-Pro-0813 | 1024 | 46,400 | hbm | 1.056x | 29,000.0 / 29,000.0 W | 35% | 15.6 | 16.4 |
| `DSV4-Pro/b200_sxm-x106-pipeline` | DeepSeek-V4-Pro-0813 | 4096 | 169,600 | hbm | 1.056x | 106,000.0 / 106,000.0 W | 35% | 14.6 | 15.4 |

The worst point's dynamic energy is weight read 93.4%, kv read 5.5%, arithmetic 0.9%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4-Pro-0813 | 1 | 184,900 | `DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x4` | 6.956966 | 14,837.3 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x116-nvl72-hybrid` | 102.983758 | 44,131.3 | layer_fixed_latency | 14.80x |
| DeepSeek-V4-Pro-0813 | 2 | 462,250 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 9.920344 | 46,082.0 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x289-nvl72-hybrid` | 127.745347 | 109,942.8 | layer_fixed_latency | 12.88x |
| DeepSeek-V4-Pro-0813 | 4 | 462,250 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 4.994104 | 46,082.0 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x289-nvl72-hybrid` | 65.986392 | 109,942.8 | layer_fixed_latency | 13.21x |
| DeepSeek-V4-Pro-0813 | 8 | 462,250 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 2.530983 | 46,082.0 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x289-nvl72-hybrid` | 36.178248 | 118,027.2 | layer_fixed_latency | 14.29x |
| DeepSeek-V4-Pro-0813 | 16 | 462,250 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 1.299423 | 46,082.0 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x289-nvl72-hybrid` | 20.323933 | 132,862.9 | layer_fixed_latency | 15.64x |
| DeepSeek-V4-Pro-0813 | 32 | 462,250 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill` | 0.683643 | 46,082.0 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x289-nvl72-hybrid` | 11.605952 | 137,780.8 | layer_fixed_latency | 16.98x |
| DeepSeek-V4-Pro-0813 | 64 | 240,425 | `DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x295` | 0.286075 | 36,765.9 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x150-nvl72-hybrid` | 5.170225 | 92,131.8 | layer_fixed_latency | 18.07x |
| DeepSeek-V4-Pro-0813 | 256 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.195010 | 73,845.3 | layer_fixed_latency | `DSV4-Pro/b200_sxm-x347-nvl72-hybrid` | 3.931492 | 228,902.3 | weight_read | 20.16x |
| DeepSeek-V4-Pro-0813 | 1024 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.136608 | 93,938.5 | kv_read | `DSV4-Pro/b200_sxm-x347-nvl72-hybrid` | 2.588412 | 300,135.0 | weight_read | 18.95x |
| DeepSeek-V4-Pro-0813 | 4096 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12` | 0.146652 | 119,417.0 | kv_read | `DSV4-Pro/b200_sxm-x347-nvl72-hybrid` | 1.750699 | 316,879.4 | weight_read | 11.94x |

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
| DeepSeek-V4-Pro-0813 | 200,000 | 1,600 B | 892.7 GB | 4.46 | 0.473 GB | 1.978 GB | 83.8 |

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
| DeepSeek-V4-Pro-0813 | 3 | 138,675 | 2,627.5 | wafer-pipeline | 1,942.9 | wafer-hybrid | 1.35x | 683.9 | pipeline | 406.7 | hybrid | 1.68x | 3.84x | 4.78x | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 2,644.8 | wafer-pipeline | 2,132.7 | wafer-hybrid | 1.24x | 691.7 | pipeline | 411.6 | hybrid | 1.68x | 3.82x | 5.18x | 1.35x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 2,645.1 | wafer-pipeline | 2,091.7 | wafer-hybrid | 1.26x | 699.5 | pipeline | 411.0 | hybrid | 1.70x | 3.78x | 5.09x | 1.35x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 2,645.1 | wafer-pipeline | 2,026.8 | wafer-hybrid | 1.31x | 703.6 | pipeline | 410.5 | hybrid | 1.71x | 3.76x | 4.94x | 1.31x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 2,646.6 | wafer-pipeline | 2,077.4 | wafer-hybrid | 1.27x | 707.7 | pipeline | 412.1 | hybrid | 1.72x | 3.74x | 5.04x | 1.35x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.24x to 1.35x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x4 | 184,900 | 2,132.7 | 2,132.7 | layer_fixed_latency | DSV4-Pro/b200_sxm-x116-nvl72-hybrid | 185,600 | 1.00x | hybrid | 1,081.12 | 411.6 | 823.3 | layer_fixed_latency | 5.18x | 0.13x | 15.52x | 5.18x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x147 | 119,805 | 1,048.6 | 1,048.6 | layer_fixed_latency | DSV4-Pro/b200_sxm-x75-nvl72-hybrid | 120,000 | 1.00x | hybrid | 1,081.12 | 403.6 | 807.2 | layer_fixed_latency | 2.60x | 0.10x | 7.63x | 2.60x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill | 462,250 | 2,080.6 | 74,902.9 | layer_fixed_latency | DSV4-Pro/b200_sxm-x289-nvl72-hybrid | 462,400 | 1.00x | hybrid | 1,090.65 | 410.0 | 2,049.8 | layer_fixed_latency | 5.08x | 1.89x | 15.14x | 5.08x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 1,055.2 | 3,165.5 | layer_fixed_latency | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 1,081.12 | 405.0 | 810.0 | layer_fixed_latency | 2.61x | 0.29x | 7.68x | 2.61x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill | 462,250 | 2,080.6 | 74,902.9 | layer_fixed_latency | DSV4-Pro/b200_sxm-x289-nvl72-hybrid | 462,400 | 1.00x | hybrid | 1,090.65 | 410.0 | 2,049.8 | layer_fixed_latency | 5.08x | 1.89x | 15.14x | 5.08x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 1,009.6 | 5,048.2 | layer_fixed_latency | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 912.75 | 399.6 | 1,997.9 | layer_fixed_latency | 2.53x | 0.46x | 7.35x | 2.53x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill | 462,250 | 2,080.6 | 74,902.9 | layer_fixed_latency | DSV4-Pro/b200_sxm-x289-nvl72-hybrid | 462,400 | 1.00x | hybrid | 1,086.41 | 396.2 | 3,962.2 | layer_fixed_latency | 5.25x | 1.89x | 15.14x | 5.25x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 829.4 | 8,294.1 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 976.29 | 380.1 | 3,041.1 | layer_fixed_latency | 2.18x | 0.75x | 6.04x | 2.18x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill | 462,250 | 2,080.6 | 74,902.9 | layer_fixed_latency | DSV4-Pro/b200_sxm-x289-nvl72-hybrid | 462,400 | 1.00x | hybrid | 936.19 | 393.2 | 7,471.6 | layer_fixed_latency | 5.29x | 1.89x | 15.14x | 5.29x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 590.9 | 9,454.4 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 1,145.72 | 336.8 | 5,388.9 | layer_fixed_latency | 1.75x | 0.86x | 4.30x | 1.75x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill | 462,250 | 2,080.6 | 74,902.9 | layer_fixed_latency | DSV4-Pro/b200_sxm-x289-nvl72-hybrid | 462,400 | 1.00x | hybrid | 1,011.48 | 371.0 | 11,871.6 | layer_fixed_latency | 5.61x | 1.89x | 15.14x | 5.61x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 369.2 | 11,814.0 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 1,124.32 | 285.1 | 9,123.5 | layer_fixed_latency | 1.29x | 1.07x | 2.69x | 1.29x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill | 462,250 | 1,998.4 | 141,889.5 | layer_fixed_latency | DSV4-Pro/b200_sxm-x289-nvl72-hybrid | 462,400 | 1.00x | hybrid | 1,196.80 | 326.0 | 20,862.7 | layer_fixed_latency | 6.13x | 3.57x | 14.54x | 6.13x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x158 | 128,770 | 209.2 | 13,388.9 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 1,435.78 | 223.7 | 14,314.0 | weight_read | 0.94x | 0.94x | 1.52x | 0.94x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,479.2 | 378,675.5 | layer_fixed_latency | DSV4-Pro/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 1,453.96 | 227.4 | 58,222.8 | weight_read | 6.50x | 6.50x | 10.76x | 6.50x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x158 | 128,770 | 57.5 | 14,715.6 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 1,753.28 | 108.9 | 27,880.3 | weight_read | 0.53x | 0.53x | 0.67x | 0.53x |
| DeepSeek-V4-Pro-0813 | 1024 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 671.5 | 687,650.0 | kv_read | DSV4-Pro/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 1,173.90 | 113.2 | 115,953.3 | weight_read | 5.93x | 5.93x | 7.47x | 5.96x |
| DeepSeek-V4-Pro-0813 | 1024 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x158 | 128,770 | 14.5 | 14,849.4 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 4,956.14 | 42.4 | 43,443.9 | weight_read | 0.34x | 0.34x | 0.43x | 0.34x |
| DeepSeek-V4-Pro-0813 | 4096 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 198.8 | 814,285.6 | kv_read | DSV4-Pro/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 4,888.44 | 44.2 | 181,001.6 | weight_read | 4.50x | 4.50x | 5.56x | 4.51x |
| DeepSeek-V4-Pro-0813 | 4096 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x158 | 128,770 | 3.6 | 14,864.7 | compute | DSV4-Pro/b200_sxm-x80-nvl72-hybrid | 128,000 | 1.01x | hybrid | 17,767.59 | 19.7 | 80,816.1 | weight_read | 0.18x | 0.18x | 0.30x | 0.18x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 1,064.19 | 298.43 | 399.8 | 576.3 |
| DeepSeek-V4-Pro-0813 | 38 | 60,800 | 1,067.62 | 298.48 | 406.1 | 590.6 |
| DeepSeek-V4-Pro-0813 | 41 | 65,600 | 1,068.64 | 298.49 | 407.6 | 594.0 |
| DeepSeek-V4-Pro-0813 | 43 | 68,800 | 1,069.31 | 298.49 | 408.4 | 596.1 |
| DeepSeek-V4-Pro-0813 | 56 | 89,600 | 1,073.48 | 298.53 | 412.4 | 606.1 |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 1,074.10 | 298.53 | 412.8 | 607.2 |
| DeepSeek-V4-Pro-0813 | 75 | 120,000 | 1,081.12 | 300.87 | 403.6 | 589.1 |
| DeepSeek-V4-Pro-0813 | 79 | 126,400 | 1,081.12 | 300.87 | 404.7 | 591.5 |
| DeepSeek-V4-Pro-0813 | 80 | 128,000 | 1,081.12 | 300.87 | 405.0 | 592.1 |
| DeepSeek-V4-Pro-0813 | 83 | 132,800 | 1,081.12 | 300.87 | 405.7 | 593.7 |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 1,081.12 | 300.87 | 406.7 | 595.7 |
| DeepSeek-V4-Pro-0813 | 92 | 147,200 | 1,081.12 | 300.87 | 407.8 | 598.0 |
| DeepSeek-V4-Pro-0813 | 98 | 156,800 | 1,081.12 | 300.87 | 408.9 | 600.5 |
| DeepSeek-V4-Pro-0813 | 100 | 160,000 | 1,081.12 | 300.87 | 409.2 | 601.2 |
| DeepSeek-V4-Pro-0813 | 106 | 169,600 | 1,081.12 | 300.87 | 410.2 | 603.3 |
| DeepSeek-V4-Pro-0813 | 110 | 176,000 | 1,081.12 | 300.87 | 410.8 | 604.6 |
| DeepSeek-V4-Pro-0813 | 113 | 180,800 | 1,081.12 | 300.87 | 411.2 | 605.5 |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 1,081.12 | 300.87 | 411.6 | 606.4 |
| DeepSeek-V4-Pro-0813 | 118 | 188,800 | 1,081.12 | 300.87 | 411.9 | 606.9 |
| DeepSeek-V4-Pro-0813 | 120 | 192,000 | 1,081.12 | 300.87 | 412.1 | 607.5 |
| DeepSeek-V4-Pro-0813 | 124 | 198,400 | 1,081.12 | 300.87 | 412.6 | 608.5 |
| DeepSeek-V4-Pro-0813 | 132 | 211,200 | 1,083.51 | 300.87 | 413.0 | 610.4 |
| DeepSeek-V4-Pro-0813 | 133 | 212,800 | 1,083.51 | 300.87 | 413.1 | 610.6 |
| DeepSeek-V4-Pro-0813 | 134 | 214,400 | 1,083.51 | 300.87 | 413.2 | 610.8 |
| DeepSeek-V4-Pro-0813 | 147 | 235,200 | 1,084.29 | 303.18 | 408.4 | 599.6 |
| DeepSeek-V4-Pro-0813 | 150 | 240,000 | 1,084.29 | 303.18 | 408.7 | 600.4 |
| DeepSeek-V4-Pro-0813 | 151 | 241,600 | 1,084.29 | 303.18 | 408.8 | 600.6 |
| DeepSeek-V4-Pro-0813 | 157 | 251,200 | 1,084.29 | 303.18 | 409.5 | 602.0 |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 1,084.29 | 303.18 | 411.0 | 605.3 |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 1,087.47 | 305.50 | 410.5 | 604.5 |
| DeepSeek-V4-Pro-0813 | 289 | 462,400 | 1,090.65 | 307.82 | 410.0 | 603.7 |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 1,093.05 | 307.82 | 412.1 | 609.2 |

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
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 138.3 | 399.8 | 343.2 | tensor | 1,064.19 | 42.6% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 38 | 60,800 | 138.1 | 406.1 | 347.2 | tensor | 1,067.62 | 43.4% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 41 | 65,600 | 138.0 | 407.6 | 336.9 | tensor | 1,068.64 | 43.6% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 43 | 68,800 | 137.9 | 408.4 | 341.4 | tensor | 1,069.31 | 43.7% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 56 | 89,600 | 137.6 | 412.4 | 351.0 | tensor | 1,073.48 | 44.3% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 137.5 | 412.8 | 341.7 | tensor | 1,074.10 | 44.3% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 75 | 120,000 | 137.4 | 191.5 | 403.6 | hybrid | 1,081.12 | 43.6% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 79 | 126,400 | 137.4 | 191.3 | 404.7 | hybrid | 1,081.12 | 43.8% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 80 | 128,000 | 137.4 | 191.2 | 405.0 | hybrid | 1,081.12 | 43.8% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 83 | 132,800 | 137.4 | 191.0 | 405.7 | hybrid | 1,081.12 | 43.9% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 137.4 | 190.7 | 406.7 | hybrid | 1,081.12 | 44.0% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 92 | 147,200 | 137.4 | 190.3 | 407.8 | hybrid | 1,081.12 | 44.1% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 98 | 156,800 | 137.4 | 189.8 | 408.9 | hybrid | 1,081.12 | 44.2% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 100 | 160,000 | 137.4 | 189.7 | 409.2 | hybrid | 1,081.12 | 44.2% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 106 | 169,600 | 137.4 | 189.2 | 410.2 | hybrid | 1,081.12 | 44.3% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 110 | 176,000 | 137.4 | 188.9 | 410.8 | hybrid | 1,081.12 | 44.4% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 113 | 180,800 | 137.4 | 188.6 | 411.2 | hybrid | 1,081.12 | 44.5% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 137.4 | 188.4 | 411.6 | hybrid | 1,081.12 | 44.5% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 118 | 188,800 | 137.4 | 188.2 | 411.9 | hybrid | 1,081.12 | 44.5% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 120 | 192,000 | 137.4 | 188.0 | 412.1 | hybrid | 1,081.12 | 44.6% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 124 | 198,400 | 137.4 | 187.7 | 412.6 | hybrid | 1,081.12 | 44.6% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 132 | 211,200 | 137.4 | 187.0 | 413.0 | hybrid | 1,083.51 | 44.8% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 133 | 212,800 | 137.4 | 186.9 | 413.1 | hybrid | 1,083.51 | 44.8% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 134 | 214,400 | 137.4 | 186.9 | 413.2 | hybrid | 1,083.51 | 44.8% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 147 | 235,200 | 137.4 | 171.7 | 408.4 | hybrid | 1,084.29 | 44.3% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 150 | 240,000 | 137.4 | 171.4 | 408.7 | hybrid | 1,084.29 | 44.3% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 151 | 241,600 | 137.4 | 171.3 | 408.8 | hybrid | 1,084.29 | 44.3% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 157 | 251,200 | 137.4 | 170.7 | 409.5 | hybrid | 1,084.29 | 44.4% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 137.4 | 169.1 | 411.0 | hybrid | 1,084.29 | 44.6% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 137.4 | 157.1 | 410.5 | hybrid | 1,087.47 | 44.6% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 289 | 462,400 | 137.4 | 148.0 | 410.0 | hybrid | 1,090.65 | 44.7% | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 137.4 | 142.9 | 412.1 | hybrid | 1,093.05 | 45.0% | layer_fixed_latency |

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
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x235 | DeepSeek-V4-Pro-0813 | 235 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x156 | DeepSeek-V4-Pro-0813 | 156 | tensor | rom_package_ucie | rom_board_serdes | 244 | 167.30 us | 597.7 tok/s | 5,977.1 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 39 on rom_board_serdes (traversals 13.2) = 163.88 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x221 | DeepSeek-V4-Pro-0813 | 221 | hybrid | rom_package_ucie | rom_board_serdes | 177 | 9.36 us | 10,681.6 tok/s | 106,816.5 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 55 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 5.94 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x235 | DeepSeek-V4-Pro-0813 | 235 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x4 | DeepSeek-V4-Pro-0813 | 4 | pipeline | on_wafer_n5 | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x147 | DeepSeek-V4-Pro-0813 | 147 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x3 | DeepSeek-V4-Pro-0813 | 3 | tensor | on_wafer_n5 | rom_wafer_serdes | 244 | 262.27 us | 381.3 tok/s | 3,812.8 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 27.42 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hybrid-x197 | DeepSeek-V4-Pro-0813 | 197 | hybrid | nvlink5 | infiniband_ndr | 146 | 353.50 us | 282.9 tok/s | 2,828.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 55.60 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x4 | DeepSeek-V4-Pro-0813 | 4 | hybrid | on_wafer_n5 | rom_wafer_serdes | 125 | 235.16 us | 425.2 tok/s | 4,252.5 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 3 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.31 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x296 | DeepSeek-V4-Pro-0813 | 296 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-tensor-x162 | DeepSeek-V4-Pro-0813 | 162 | tensor | rom_package_ucie | rom_board_serdes | 244 | 167.31 us | 597.7 tok/s | 5,977.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 41 on rom_board_serdes (traversals 13.2) = 163.88 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x263 | DeepSeek-V4-Pro-0813 | 263 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 9.90 us | 10,099.3 tok/s | 100,993.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.48 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x295 | DeepSeek-V4-Pro-0813 | 295 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10 | DeepSeek-V4-Pro-0813 | 10 | pipeline | on_wafer_n5 | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x158 | DeepSeek-V4-Pro-0813 | 158 | tensor | nvlink5 | infiniband_ndr | 244 | 892.91 us | 112.0 tok/s | 1,119.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 595.01 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x10 | DeepSeek-V4-Pro-0813 | 10 | tensor | on_wafer_n5 | rom_wafer_serdes | 244 | 316.16 us | 316.3 tok/s | 3,163.0 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 10 on rom_wafer_serdes (traversals 6.6) = 81.31 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x208 | DeepSeek-V4-Pro-0813 | 208 | hybrid | nvlink5 | infiniband_ndr | 147 | 355.82 us | 281.0 tok/s | 2,810.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 25 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 57.92 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10 | DeepSeek-V4-Pro-0813 | 10 | hybrid | on_wafer_n5 | rom_wafer_serdes | 131 | 235.77 us | 424.1 tok/s | 4,241.4 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 9 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.92 us |
| DSV4-Pro/b200_sxm-x29-pipeline | DeepSeek-V4-Pro-0813 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 37.35 us | 2,677.5 tok/s | 26,774.9 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.40 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x29-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5 | infiniband_ndr | 244 | 871.93 us | 114.7 tok/s | 1,146.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x29-hybrid | DeepSeek-V4-Pro-0813 | 29 | hybrid | nvlink5 | infiniband_ndr | 125 | 304.85 us | 328.0 tok/s | 3,280.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x29-nvl72-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.43 us | 335.1 tok/s | 3,350.9 tok/s | 122 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 298.43 us |
| DSV4-Pro/b200_sxm-x29-expert | DeepSeek-V4-Pro-0813 | 29 | expert | nvlink5 | infiniband_ndr | 244 | 549.40 us | 182.0 tok/s | 1,820.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 294.50 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 254.90 us |
| DSV4-Pro/b200_sxm-x29-nvl72-expert | DeepSeek-V4-Pro-0813 | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.23 us | 224.6 tok/s | 2,246.0 tok/s | 122 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 298.43 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.80 us |
| DSV4-Pro/b200_sxm-x38-pipeline | DeepSeek-V4-Pro-0813 | 38 | pipeline | nvlink5 | infiniband_ndr | 37 | 49.39 us | 2,024.6 tok/s | 20,246.0 tok/s | 33 x point_to_point span 2 on nvlink5 (traversals 1.0) = 40.13 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x38-tensor | DeepSeek-V4-Pro-0813 | 38 | tensor | nvlink5 | infiniband_ndr | 244 | 877.17 us | 114.0 tok/s | 1,140.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x38-hybrid | DeepSeek-V4-Pro-0813 | 38 | hybrid | nvlink5 | infiniband_ndr | 126 | 307.17 us | 325.6 tok/s | 3,255.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x38-nvl72-tensor | DeepSeek-V4-Pro-0813 | 38 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.48 us | 335.0 tok/s | 3,350.3 tok/s | 122 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 298.48 us |
| DSV4-Pro/b200_sxm-x38-expert | DeepSeek-V4-Pro-0813 | 38 | expert | nvlink5 | infiniband_ndr | 244 | 547.26 us | 182.7 tok/s | 1,827.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 294.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 253.18 us |
| DSV4-Pro/b200_sxm-x38-nvl72-expert | DeepSeek-V4-Pro-0813 | 38 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.18 us | 224.6 tok/s | 2,246.3 tok/s | 122 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 298.48 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.71 us |
| DSV4-Pro/b200_sxm-x41-pipeline | DeepSeek-V4-Pro-0813 | 41 | pipeline | nvlink5 | infiniband_ndr | 40 | 54.14 us | 1,847.0 tok/s | 18,470.3 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.56 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x41-tensor | DeepSeek-V4-Pro-0813 | 41 | tensor | nvlink5 | infiniband_ndr | 244 | 880.67 us | 113.5 tok/s | 1,135.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 582.77 us |
| DSV4-Pro/b200_sxm-x41-hybrid | DeepSeek-V4-Pro-0813 | 41 | hybrid | nvlink5 | infiniband_ndr | 127 | 309.48 us | 323.1 tok/s | 3,231.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x41-nvl72-tensor | DeepSeek-V4-Pro-0813 | 41 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.49 us | 335.0 tok/s | 3,350.2 tok/s | 122 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 298.49 us |
| DSV4-Pro/b200_sxm-x41-expert | DeepSeek-V4-Pro-0813 | 41 | expert | nvlink5 | infiniband_ndr | 244 | 546.60 us | 182.9 tok/s | 1,829.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.78 us |
| DSV4-Pro/b200_sxm-x41-nvl72-expert | DeepSeek-V4-Pro-0813 | 41 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.17 us | 224.6 tok/s | 2,246.3 tok/s | 122 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 298.49 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.68 us |
| DSV4-Pro/b200_sxm-x43-pipeline | DeepSeek-V4-Pro-0813 | 43 | pipeline | nvlink5 | infiniband_ndr | 42 | 56.57 us | 1,767.6 tok/s | 17,676.3 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.99 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x43-tensor | DeepSeek-V4-Pro-0813 | 43 | tensor | nvlink5 | infiniband_ndr | 244 | 880.67 us | 113.5 tok/s | 1,135.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 582.77 us |
| DSV4-Pro/b200_sxm-x43-hybrid | DeepSeek-V4-Pro-0813 | 43 | hybrid | nvlink5 | infiniband_ndr | 127 | 309.48 us | 323.1 tok/s | 3,231.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.58 us |
| DSV4-Pro/b200_sxm-x43-nvl72-tensor | DeepSeek-V4-Pro-0813 | 43 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.49 us | 335.0 tok/s | 3,350.1 tok/s | 122 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 298.49 us |
| DSV4-Pro/b200_sxm-x43-expert | DeepSeek-V4-Pro-0813 | 43 | expert | nvlink5 | infiniband_ndr | 244 | 546.36 us | 183.0 tok/s | 1,830.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.82 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 252.54 us |
| DSV4-Pro/b200_sxm-x43-nvl72-expert | DeepSeek-V4-Pro-0813 | 43 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.17 us | 224.6 tok/s | 2,246.4 tok/s | 122 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 298.49 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.67 us |
| DSV4-Pro/b200_sxm-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink5 | infiniband_ndr | 55 | 73.48 us | 1,360.9 tok/s | 13,609.0 tok/s | 49 x point_to_point span 2 on nvlink5 (traversals 1.0) = 59.58 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.90 us |
| DSV4-Pro/b200_sxm-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink5 | infiniband_ndr | 244 | 883.17 us | 113.2 tok/s | 1,132.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 585.27 us |
| DSV4-Pro/b200_sxm-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink5 | infiniband_ndr | 128 | 311.80 us | 320.7 tok/s | 3,207.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.90 us |
| DSV4-Pro/b200_sxm-x56-nvl72-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.53 us | 335.0 tok/s | 3,349.8 tok/s | 122 x all_reduce span 56 on nvlink5_nvl72 (traversals 2.0) = 298.53 us |
| DSV4-Pro/b200_sxm-x56-expert | DeepSeek-V4-Pro-0813 | 56 | expert | nvlink5 | infiniband_ndr | 244 | 544.94 us | 183.5 tok/s | 1,835.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.53 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 251.41 us |
| DSV4-Pro/b200_sxm-x56-nvl72-expert | DeepSeek-V4-Pro-0813 | 56 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.13 us | 224.7 tok/s | 2,246.5 tok/s | 122 x all_reduce span 56 on nvlink5_nvl72 (traversals 2.0) = 298.53 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.61 us |
| DSV4-Pro/b200_sxm-x58-pipeline | DeepSeek-V4-Pro-0813 | 58 | pipeline | nvlink5 | infiniband_ndr | 57 | 77.01 us | 1,298.5 tok/s | 12,984.7 tok/s | 50 x point_to_point span 2 on nvlink5 (traversals 1.0) = 60.80 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x58-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5 | infiniband_ndr | 244 | 885.04 us | 113.0 tok/s | 1,129.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 587.14 us |
| DSV4-Pro/b200_sxm-x58-hybrid | DeepSeek-V4-Pro-0813 | 58 | hybrid | nvlink5 | infiniband_ndr | 129 | 314.12 us | 318.4 tok/s | 3,183.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x58-nvl72-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 122 | 298.53 us | 335.0 tok/s | 3,349.8 tok/s | 122 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 298.53 us |
| DSV4-Pro/b200_sxm-x58-expert | DeepSeek-V4-Pro-0813 | 58 | expert | nvlink5 | infiniband_ndr | 244 | 544.81 us | 183.6 tok/s | 1,835.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.53 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 251.28 us |
| DSV4-Pro/b200_sxm-x58-nvl72-expert | DeepSeek-V4-Pro-0813 | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 445.13 us | 224.7 tok/s | 2,246.5 tok/s | 122 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 298.53 us; 122 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 146.60 us |
| DSV4-Pro/b200_sxm-x75-pipeline | DeepSeek-V4-Pro-0813 | 75 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x75-tensor | DeepSeek-V4-Pro-0813 | 75 | tensor | nvlink5 | infiniband_ndr | 244 | 887.67 us | 112.7 tok/s | 1,126.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 589.77 us |
| DSV4-Pro/b200_sxm-x75-hybrid | DeepSeek-V4-Pro-0813 | 75 | hybrid | nvlink5 | infiniband_ndr | 131 | 318.75 us | 313.7 tok/s | 3,137.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| DSV4-Pro/b200_sxm-x75-nvl72-tensor | DeepSeek-V4-Pro-0813 | 75 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x75-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 75 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x75-expert | DeepSeek-V4-Pro-0813 | 75 | expert | nvlink5 | infiniband_ndr | 244 | 543.83 us | 183.9 tok/s | 1,838.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.37 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.46 us |
| DSV4-Pro/b200_sxm-x75-nvl72-expert | DeepSeek-V4-Pro-0813 | 75 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 549.01 us | 182.1 tok/s | 1,821.5 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.46 us |
| DSV4-Pro/b200_sxm-x79-pipeline | DeepSeek-V4-Pro-0813 | 79 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x79-tensor | DeepSeek-V4-Pro-0813 | 79 | tensor | nvlink5 | infiniband_ndr | 244 | 887.67 us | 112.7 tok/s | 1,126.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 589.77 us |
| DSV4-Pro/b200_sxm-x79-hybrid | DeepSeek-V4-Pro-0813 | 79 | hybrid | nvlink5 | infiniband_ndr | 131 | 318.75 us | 313.7 tok/s | 3,137.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| DSV4-Pro/b200_sxm-x79-nvl72-tensor | DeepSeek-V4-Pro-0813 | 79 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x79-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 79 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x79-expert | DeepSeek-V4-Pro-0813 | 79 | expert | nvlink5 | infiniband_ndr | 244 | 543.68 us | 183.9 tok/s | 1,839.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.37 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.32 us |
| DSV4-Pro/b200_sxm-x79-nvl72-expert | DeepSeek-V4-Pro-0813 | 79 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.87 us | 182.2 tok/s | 1,821.9 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.32 us |
| DSV4-Pro/b200_sxm-x80-pipeline | DeepSeek-V4-Pro-0813 | 80 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x80-tensor | DeepSeek-V4-Pro-0813 | 80 | tensor | nvlink5 | infiniband_ndr | 244 | 887.67 us | 112.7 tok/s | 1,126.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 589.77 us |
| DSV4-Pro/b200_sxm-x80-hybrid | DeepSeek-V4-Pro-0813 | 80 | hybrid | nvlink5 | infiniband_ndr | 131 | 318.75 us | 313.7 tok/s | 3,137.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| DSV4-Pro/b200_sxm-x80-nvl72-tensor | DeepSeek-V4-Pro-0813 | 80 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x80-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 80 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x80-expert | DeepSeek-V4-Pro-0813 | 80 | expert | nvlink5 | infiniband_ndr | 244 | 543.59 us | 184.0 tok/s | 1,839.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.31 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.28 us |
| DSV4-Pro/b200_sxm-x80-nvl72-expert | DeepSeek-V4-Pro-0813 | 80 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.83 us | 182.2 tok/s | 1,822.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.28 us |
| DSV4-Pro/b200_sxm-x83-pipeline | DeepSeek-V4-Pro-0813 | 83 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x83-tensor | DeepSeek-V4-Pro-0813 | 83 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x83-hybrid | DeepSeek-V4-Pro-0813 | 83 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x83-nvl72-tensor | DeepSeek-V4-Pro-0813 | 83 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x83-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 83 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x83-expert | DeepSeek-V4-Pro-0813 | 83 | expert | nvlink5 | infiniband_ndr | 244 | 543.50 us | 184.0 tok/s | 1,839.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.31 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.19 us |
| DSV4-Pro/b200_sxm-x83-nvl72-expert | DeepSeek-V4-Pro-0813 | 83 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.74 us | 182.2 tok/s | 1,822.4 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.19 us |
| DSV4-Pro/b200_sxm-x87-pipeline | DeepSeek-V4-Pro-0813 | 87 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x87-tensor | DeepSeek-V4-Pro-0813 | 87 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x87-hybrid | DeepSeek-V4-Pro-0813 | 87 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x87-nvl72-tensor | DeepSeek-V4-Pro-0813 | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x87-expert | DeepSeek-V4-Pro-0813 | 87 | expert | nvlink5 | infiniband_ndr | 244 | 543.38 us | 184.0 tok/s | 1,840.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.31 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.07 us |
| DSV4-Pro/b200_sxm-x87-nvl72-expert | DeepSeek-V4-Pro-0813 | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.62 us | 182.3 tok/s | 1,822.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 250.07 us |
| DSV4-Pro/b200_sxm-x92-pipeline | DeepSeek-V4-Pro-0813 | 92 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x92-tensor | DeepSeek-V4-Pro-0813 | 92 | tensor | nvlink5 | infiniband_ndr | 244 | 889.42 us | 112.4 tok/s | 1,124.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 591.51 us |
| DSV4-Pro/b200_sxm-x92-hybrid | DeepSeek-V4-Pro-0813 | 92 | hybrid | nvlink5 | infiniband_ndr | 133 | 323.39 us | 309.2 tok/s | 3,092.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| DSV4-Pro/b200_sxm-x92-nvl72-tensor | DeepSeek-V4-Pro-0813 | 92 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x92-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 92 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x92-expert | DeepSeek-V4-Pro-0813 | 92 | expert | nvlink5 | infiniband_ndr | 244 | 543.21 us | 184.1 tok/s | 1,840.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.26 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.94 us |
| DSV4-Pro/b200_sxm-x92-nvl72-expert | DeepSeek-V4-Pro-0813 | 92 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.49 us | 182.3 tok/s | 1,823.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.94 us |
| DSV4-Pro/b200_sxm-x98-pipeline | DeepSeek-V4-Pro-0813 | 98 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x98-tensor | DeepSeek-V4-Pro-0813 | 98 | tensor | nvlink5 | infiniband_ndr | 244 | 890.09 us | 112.3 tok/s | 1,123.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 592.19 us |
| DSV4-Pro/b200_sxm-x98-hybrid | DeepSeek-V4-Pro-0813 | 98 | hybrid | nvlink5 | infiniband_ndr | 134 | 325.70 us | 307.0 tok/s | 3,070.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 27.80 us |
| DSV4-Pro/b200_sxm-x98-nvl72-tensor | DeepSeek-V4-Pro-0813 | 98 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x98-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 98 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x98-expert | DeepSeek-V4-Pro-0813 | 98 | expert | nvlink5 | infiniband_ndr | 244 | 543.03 us | 184.2 tok/s | 1,841.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.23 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.80 us |
| DSV4-Pro/b200_sxm-x98-nvl72-expert | DeepSeek-V4-Pro-0813 | 98 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.35 us | 182.4 tok/s | 1,823.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.80 us |
| DSV4-Pro/b200_sxm-x100-pipeline | DeepSeek-V4-Pro-0813 | 100 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x100-tensor | DeepSeek-V4-Pro-0813 | 100 | tensor | nvlink5 | infiniband_ndr | 244 | 890.09 us | 112.3 tok/s | 1,123.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 592.19 us |
| DSV4-Pro/b200_sxm-x100-hybrid | DeepSeek-V4-Pro-0813 | 100 | hybrid | nvlink5 | infiniband_ndr | 134 | 325.70 us | 307.0 tok/s | 3,070.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 27.80 us |
| DSV4-Pro/b200_sxm-x100-nvl72-tensor | DeepSeek-V4-Pro-0813 | 100 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x100-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 100 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x100-expert | DeepSeek-V4-Pro-0813 | 100 | expert | nvlink5 | infiniband_ndr | 244 | 542.98 us | 184.2 tok/s | 1,841.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.23 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.76 us |
| DSV4-Pro/b200_sxm-x100-nvl72-expert | DeepSeek-V4-Pro-0813 | 100 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.31 us | 182.4 tok/s | 1,823.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.76 us |
| DSV4-Pro/b200_sxm-x106-pipeline | DeepSeek-V4-Pro-0813 | 106 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x106-tensor | DeepSeek-V4-Pro-0813 | 106 | tensor | nvlink5 | infiniband_ndr | 244 | 890.67 us | 112.3 tok/s | 1,122.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 592.76 us |
| DSV4-Pro/b200_sxm-x106-hybrid | DeepSeek-V4-Pro-0813 | 106 | hybrid | nvlink5 | infiniband_ndr | 135 | 328.02 us | 304.9 tok/s | 3,048.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.12 us |
| DSV4-Pro/b200_sxm-x106-nvl72-tensor | DeepSeek-V4-Pro-0813 | 106 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x106-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 106 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x106-expert | DeepSeek-V4-Pro-0813 | 106 | expert | nvlink5 | infiniband_ndr | 244 | 542.83 us | 184.2 tok/s | 1,842.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.19 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.64 us |
| DSV4-Pro/b200_sxm-x106-nvl72-expert | DeepSeek-V4-Pro-0813 | 106 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.19 us | 182.4 tok/s | 1,824.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.64 us |
| DSV4-Pro/b200_sxm-x110-pipeline | DeepSeek-V4-Pro-0813 | 110 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x110-tensor | DeepSeek-V4-Pro-0813 | 110 | tensor | nvlink5 | infiniband_ndr | 244 | 890.67 us | 112.3 tok/s | 1,122.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 592.76 us |
| DSV4-Pro/b200_sxm-x110-hybrid | DeepSeek-V4-Pro-0813 | 110 | hybrid | nvlink5 | infiniband_ndr | 135 | 328.02 us | 304.9 tok/s | 3,048.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.12 us |
| DSV4-Pro/b200_sxm-x110-nvl72-tensor | DeepSeek-V4-Pro-0813 | 110 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x110-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 110 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x110-expert | DeepSeek-V4-Pro-0813 | 110 | expert | nvlink5 | infiniband_ndr | 244 | 542.76 us | 184.2 tok/s | 1,842.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.19 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.57 us |
| DSV4-Pro/b200_sxm-x110-nvl72-expert | DeepSeek-V4-Pro-0813 | 110 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 548.12 us | 182.4 tok/s | 1,824.4 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.57 us |
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
| DSV4-Pro/b200_sxm-x118-pipeline | DeepSeek-V4-Pro-0813 | 118 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x118-tensor | DeepSeek-V4-Pro-0813 | 118 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x118-hybrid | DeepSeek-V4-Pro-0813 | 118 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x118-nvl72-tensor | DeepSeek-V4-Pro-0813 | 118 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x118-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 118 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x118-expert | DeepSeek-V4-Pro-0813 | 118 | expert | nvlink5 | infiniband_ndr | 244 | 542.60 us | 184.3 tok/s | 1,843.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.16 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.44 us |
| DSV4-Pro/b200_sxm-x118-nvl72-expert | DeepSeek-V4-Pro-0813 | 118 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.99 us | 182.5 tok/s | 1,824.9 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.44 us |
| DSV4-Pro/b200_sxm-x120-pipeline | DeepSeek-V4-Pro-0813 | 120 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x120-tensor | DeepSeek-V4-Pro-0813 | 120 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x120-hybrid | DeepSeek-V4-Pro-0813 | 120 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x120-nvl72-tensor | DeepSeek-V4-Pro-0813 | 120 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x120-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 120 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x120-expert | DeepSeek-V4-Pro-0813 | 120 | expert | nvlink5 | infiniband_ndr | 244 | 542.55 us | 184.3 tok/s | 1,843.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.14 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.41 us |
| DSV4-Pro/b200_sxm-x120-nvl72-expert | DeepSeek-V4-Pro-0813 | 120 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.96 us | 182.5 tok/s | 1,825.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.41 us |
| DSV4-Pro/b200_sxm-x124-pipeline | DeepSeek-V4-Pro-0813 | 124 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x124-tensor | DeepSeek-V4-Pro-0813 | 124 | tensor | nvlink5 | infiniband_ndr | 244 | 891.60 us | 112.2 tok/s | 1,121.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 593.70 us |
| DSV4-Pro/b200_sxm-x124-hybrid | DeepSeek-V4-Pro-0813 | 124 | hybrid | nvlink5 | infiniband_ndr | 137 | 332.65 us | 300.6 tok/s | 3,006.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 34.75 us |
| DSV4-Pro/b200_sxm-x124-nvl72-tensor | DeepSeek-V4-Pro-0813 | 124 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x124-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 124 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x124-expert | DeepSeek-V4-Pro-0813 | 124 | expert | nvlink5 | infiniband_ndr | 244 | 542.49 us | 184.3 tok/s | 1,843.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.14 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.35 us |
| DSV4-Pro/b200_sxm-x124-nvl72-expert | DeepSeek-V4-Pro-0813 | 124 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.90 us | 182.5 tok/s | 1,825.1 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.35 us |
| DSV4-Pro/b200_sxm-x132-pipeline | DeepSeek-V4-Pro-0813 | 132 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x132-tensor | DeepSeek-V4-Pro-0813 | 132 | tensor | nvlink5 | infiniband_ndr | 244 | 891.99 us | 112.1 tok/s | 1,121.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 594.09 us |
| DSV4-Pro/b200_sxm-x132-hybrid | DeepSeek-V4-Pro-0813 | 132 | hybrid | nvlink5 | infiniband_ndr | 138 | 334.97 us | 298.5 tok/s | 2,985.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 37.07 us |
| DSV4-Pro/b200_sxm-x132-nvl72-tensor | DeepSeek-V4-Pro-0813 | 132 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x132-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 132 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x132-expert | DeepSeek-V4-Pro-0813 | 132 | expert | nvlink5 | infiniband_ndr | 244 | 542.37 us | 184.4 tok/s | 1,843.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.12 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.25 us |
| DSV4-Pro/b200_sxm-x132-nvl72-expert | DeepSeek-V4-Pro-0813 | 132 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.80 us | 182.5 tok/s | 1,825.5 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.25 us |
| DSV4-Pro/b200_sxm-x133-pipeline | DeepSeek-V4-Pro-0813 | 133 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x133-tensor | DeepSeek-V4-Pro-0813 | 133 | tensor | nvlink5 | infiniband_ndr | 244 | 891.99 us | 112.1 tok/s | 1,121.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 594.09 us |
| DSV4-Pro/b200_sxm-x133-hybrid | DeepSeek-V4-Pro-0813 | 133 | hybrid | nvlink5 | infiniband_ndr | 138 | 334.97 us | 298.5 tok/s | 2,985.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 37.07 us |
| DSV4-Pro/b200_sxm-x133-nvl72-tensor | DeepSeek-V4-Pro-0813 | 133 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x133-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 133 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x133-expert | DeepSeek-V4-Pro-0813 | 133 | expert | nvlink5 | infiniband_ndr | 244 | 542.36 us | 184.4 tok/s | 1,843.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.12 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.24 us |
| DSV4-Pro/b200_sxm-x133-nvl72-expert | DeepSeek-V4-Pro-0813 | 133 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.79 us | 182.6 tok/s | 1,825.5 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.24 us |
| DSV4-Pro/b200_sxm-x134-pipeline | DeepSeek-V4-Pro-0813 | 134 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x134-tensor | DeepSeek-V4-Pro-0813 | 134 | tensor | nvlink5 | infiniband_ndr | 244 | 891.99 us | 112.1 tok/s | 1,121.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 594.09 us |
| DSV4-Pro/b200_sxm-x134-hybrid | DeepSeek-V4-Pro-0813 | 134 | hybrid | nvlink5 | infiniband_ndr | 138 | 334.97 us | 298.5 tok/s | 2,985.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 37.07 us |
| DSV4-Pro/b200_sxm-x134-nvl72-tensor | DeepSeek-V4-Pro-0813 | 134 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 846.34 us | 118.2 tok/s | 1,181.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x134-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 134 | hybrid | nvlink5_nvl72 | infiniband_ndr | 123 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x134-expert | DeepSeek-V4-Pro-0813 | 134 | expert | nvlink5 | infiniband_ndr | 244 | 542.35 us | 184.4 tok/s | 1,843.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.12 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.23 us |
| DSV4-Pro/b200_sxm-x134-nvl72-expert | DeepSeek-V4-Pro-0813 | 134 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 547.78 us | 182.6 tok/s | 1,825.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.23 us |
| DSV4-Pro/b200_sxm-x147-pipeline | DeepSeek-V4-Pro-0813 | 147 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x147-tensor | DeepSeek-V4-Pro-0813 | 147 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x147-hybrid | DeepSeek-V4-Pro-0813 | 147 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x147-nvl72-tensor | DeepSeek-V4-Pro-0813 | 147 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x147-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 147 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x147-expert | DeepSeek-V4-Pro-0813 | 147 | expert | nvlink5 | infiniband_ndr | 244 | 542.17 us | 184.4 tok/s | 1,844.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.09 us |
| DSV4-Pro/b200_sxm-x147-nvl72-expert | DeepSeek-V4-Pro-0813 | 147 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.76 us | 183.6 tok/s | 1,835.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.09 us |
| DSV4-Pro/b200_sxm-x150-pipeline | DeepSeek-V4-Pro-0813 | 150 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x150-tensor | DeepSeek-V4-Pro-0813 | 150 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x150-hybrid | DeepSeek-V4-Pro-0813 | 150 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x150-nvl72-tensor | DeepSeek-V4-Pro-0813 | 150 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x150-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 150 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x150-expert | DeepSeek-V4-Pro-0813 | 150 | expert | nvlink5 | infiniband_ndr | 244 | 542.14 us | 184.5 tok/s | 1,844.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.06 us |
| DSV4-Pro/b200_sxm-x150-nvl72-expert | DeepSeek-V4-Pro-0813 | 150 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.73 us | 183.6 tok/s | 1,835.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.06 us |
| DSV4-Pro/b200_sxm-x151-pipeline | DeepSeek-V4-Pro-0813 | 151 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x151-tensor | DeepSeek-V4-Pro-0813 | 151 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x151-hybrid | DeepSeek-V4-Pro-0813 | 151 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x151-nvl72-tensor | DeepSeek-V4-Pro-0813 | 151 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x151-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 151 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x151-expert | DeepSeek-V4-Pro-0813 | 151 | expert | nvlink5 | infiniband_ndr | 244 | 542.13 us | 184.5 tok/s | 1,844.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.08 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.05 us |
| DSV4-Pro/b200_sxm-x151-nvl72-expert | DeepSeek-V4-Pro-0813 | 151 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.72 us | 183.6 tok/s | 1,835.8 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.05 us |
| DSV4-Pro/b200_sxm-x157-pipeline | DeepSeek-V4-Pro-0813 | 157 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x157-tensor | DeepSeek-V4-Pro-0813 | 157 | tensor | nvlink5 | infiniband_ndr | 244 | 892.91 us | 112.0 tok/s | 1,119.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 595.01 us |
| DSV4-Pro/b200_sxm-x157-hybrid | DeepSeek-V4-Pro-0813 | 157 | hybrid | nvlink5 | infiniband_ndr | 141 | 341.92 us | 292.5 tok/s | 2,924.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 19 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 44.02 us |
| DSV4-Pro/b200_sxm-x157-nvl72-tensor | DeepSeek-V4-Pro-0813 | 157 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x157-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 157 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x157-expert | DeepSeek-V4-Pro-0813 | 157 | expert | nvlink5 | infiniband_ndr | 244 | 542.07 us | 184.5 tok/s | 1,844.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.07 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.00 us |
| DSV4-Pro/b200_sxm-x157-nvl72-expert | DeepSeek-V4-Pro-0813 | 157 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.67 us | 183.6 tok/s | 1,836.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 249.00 us |
| DSV4-Pro/b200_sxm-x173-pipeline | DeepSeek-V4-Pro-0813 | 173 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x173-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5 | infiniband_ndr | 244 | 893.39 us | 111.9 tok/s | 1,119.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 595.49 us |
| DSV4-Pro/b200_sxm-x173-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5 | infiniband_ndr | 143 | 346.55 us | 288.6 tok/s | 2,885.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| DSV4-Pro/b200_sxm-x173-nvl72-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 565.28 us |
| DSV4-Pro/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 124 | 303.18 us | 329.8 tok/s | 3,298.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| DSV4-Pro/b200_sxm-x173-expert | DeepSeek-V4-Pro-0813 | 173 | expert | nvlink5 | infiniband_ndr | 244 | 541.92 us | 184.5 tok/s | 1,845.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 293.04 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.87 us |
| DSV4-Pro/b200_sxm-x173-nvl72-expert | DeepSeek-V4-Pro-0813 | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 544.55 us | 183.6 tok/s | 1,836.4 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 295.67 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.87 us |
| DSV4-Pro/b200_sxm-x231-pipeline | DeepSeek-V4-Pro-0813 | 231 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x231-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5 | infiniband_ndr | 244 | 894.54 us | 111.8 tok/s | 1,117.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 596.64 us |
| DSV4-Pro/b200_sxm-x231-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5 | infiniband_ndr | 150 | 362.77 us | 275.7 tok/s | 2,756.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 64.87 us |
| DSV4-Pro/b200_sxm-x231-nvl72-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 872.57 us | 114.6 tok/s | 1,146.0 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 125 | 305.50 us | 327.3 tok/s | 3,273.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x231-expert | DeepSeek-V4-Pro-0813 | 231 | expert | nvlink5 | infiniband_ndr | 244 | 541.55 us | 184.7 tok/s | 1,846.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.98 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.57 us |
| DSV4-Pro/b200_sxm-x231-nvl72-expert | DeepSeek-V4-Pro-0813 | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 543.28 us | 184.1 tok/s | 1,840.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.72 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.57 us |
| DSV4-Pro/b200_sxm-x289-pipeline | DeepSeek-V4-Pro-0813 | 289 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x289-tensor | DeepSeek-V4-Pro-0813 | 289 | tensor | nvlink5 | infiniband_ndr | 244 | 895.32 us | 111.7 tok/s | 1,116.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 37 on infiniband_ndr (traversals 2.0) = 597.42 us |
| DSV4-Pro/b200_sxm-x289-hybrid | DeepSeek-V4-Pro-0813 | 289 | hybrid | nvlink5 | infiniband_ndr | 158 | 381.30 us | 262.3 tok/s | 2,622.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 36 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 83.40 us |
| DSV4-Pro/b200_sxm-x289-nvl72-tensor | DeepSeek-V4-Pro-0813 | 289 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 877.82 us | 113.9 tok/s | 1,139.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x289-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 289 | hybrid | nvlink5_nvl72 | infiniband_ndr | 126 | 307.82 us | 324.9 tok/s | 3,248.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x289-expert | DeepSeek-V4-Pro-0813 | 289 | expert | nvlink5 | infiniband_ndr | 244 | 541.33 us | 184.7 tok/s | 1,847.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.94 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.39 us |
| DSV4-Pro/b200_sxm-x289-nvl72-expert | DeepSeek-V4-Pro-0813 | 289 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 542.62 us | 184.3 tok/s | 1,842.9 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.24 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.39 us |
| DSV4-Pro/b200_sxm-x347-pipeline | DeepSeek-V4-Pro-0813 | 347 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x347-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5 | infiniband_ndr | 244 | 895.78 us | 111.6 tok/s | 1,116.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 597.87 us |
| DSV4-Pro/b200_sxm-x347-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5 | infiniband_ndr | 165 | 397.52 us | 251.6 tok/s | 2,515.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 99.62 us |
| DSV4-Pro/b200_sxm-x347-nvl72-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 244 | 877.82 us | 113.9 tok/s | 1,139.2 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 579.27 us |
| DSV4-Pro/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 126 | 307.82 us | 324.9 tok/s | 3,248.7 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 298.55 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.27 us |
| DSV4-Pro/b200_sxm-x347-expert | DeepSeek-V4-Pro-0813 | 347 | expert | nvlink5 | infiniband_ndr | 244 | 541.18 us | 184.8 tok/s | 1,847.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 292.92 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.26 us |
| DSV4-Pro/b200_sxm-x347-nvl72-expert | DeepSeek-V4-Pro-0813 | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 244 | 542.50 us | 184.3 tok/s | 1,843.3 tok/s | 122 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 294.24 us; 122 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 248.26 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x4 | 184,900 | 2,132.7 | 0.012 | 1,889.2 (176,040) | 2,132.7 (184,900) | 1.13x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill | 462,250 | 2,080.6 | 0.005 | 1,900.6 (198,860) | 2,080.6 (462,250) | 1.09x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill | 462,250 | 2,080.6 | 0.005 | 1,900.6 (198,860) | 2,080.6 (462,250) | 1.09x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill | 462,250 | 2,080.6 | 0.005 | 1,900.6 (198,860) | 2,080.6 (462,250) | 1.09x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill | 462,250 | 2,080.6 | 0.005 | 1,900.6 (198,860) | 2,080.6 (462,250) | 1.09x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-romfill | 462,250 | 2,080.6 | 0.005 | 1,925.8 (211,900) | 2,080.6 (462,250) | 1.08x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 64 | array | array | DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x295 | 240,425 | 1,936.3 | 0.008 | 1,859.2 (211,900) | 1,998.4 (462,250) | 1.07x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 256 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,479.2 | 0.003 | 1,320.2 (277,100) | 1,479.2 (554,700) | 1.12x | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 1024 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 671.5 | 0.001 | 529.2 (277,100) | 671.5 (554,700) | 1.27x | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | wafer | array | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 198.8 | 0.000 | 149.7 (277,100) | 198.8 (554,700) | 1.33x | kv_read |

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
| DeepSeek-V4-Pro-0813 | 1 | sram | 464,878.4 | 26,113.2 | 26,113.2 | 17.80x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 464,878.4 | 26,113.2 | 26,113.2 | 17.80x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 464,878.4 | 26,113.2 | 26,113.2 | 17.80x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 464,878.4 | 26,113.2 | 26,113.2 | 17.80x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 464,878.4 | 26,113.2 | 26,113.2 | 17.80x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 464,878.4 | 26,113.2 | 40,338.1 | 17.80x | 1.54x | weight_read | weight_read | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 64 | sram | 464,878.4 | 26,113.2 | 54,637.4 | 17.80x | 2.09x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 464,878.4 | 26,113.2 | 138,770.2 | 17.80x | 5.31x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1024 | sram | 672,501.7 | 26,113.2 | 258,057.6 | 25.75x | 9.88x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4096 | sram | 814,285.6 | 26,113.2 | 400,925.7 | 31.18x | 15.35x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 623,124.0 | 182,843.6 | 182,843.6 | 3.41x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 623,124.0 | 182,843.6 | 182,843.6 | 3.41x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 623,124.0 | 182,843.6 | 182,843.6 | 3.41x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 623,124.0 | 182,843.6 | 182,843.6 | 3.41x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 623,124.0 | 182,843.6 | 182,843.6 | 3.41x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 623,124.0 | 182,843.6 | 182,843.6 | 3.41x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 623,124.0 | 182,843.6 | 182,843.6 | 3.41x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 623,124.0 | 182,843.6 | 303,750.8 | 3.41x | 1.66x | kv_read | weight_read | layer_fixed_latency |
| DeepSeek-V4-Pro-0813 | 1024 | rom | 687,650.0 | 191,093.3 | 572,974.0 | 3.60x | 3.00x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | rom | 809,992.5 | 199,508.3 | 686,459.4 | 4.06x | 3.44x | kv_read | weight_read | kv_read |

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
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 464,878.4 | 0.838 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 623,124.0 | 1.123 | kv_read | 1.34x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 464,878.4 | 0.838 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 623,124.0 | 1.123 | kv_read | 1.34x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 464,878.4 | 0.838 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 623,124.0 | 1.123 | kv_read | 1.34x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 464,878.4 | 0.838 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 623,124.0 | 1.123 | kv_read | 1.34x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 464,878.4 | 0.838 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 623,124.0 | 1.123 | kv_read | 1.34x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 464,878.4 | 0.838 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 623,124.0 | 1.123 | kv_read | 1.34x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.99 | 40,338.1 | 0.436 | layer_fixed_latency | 0.09x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 464,878.4 | 0.838 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 623,124.0 | 1.123 | kv_read | 1.34x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 1.82 | 54,637.4 | 0.118 | weight_read | 0.12x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 464,878.4 | 0.838 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 623,124.0 | 1.123 | kv_read | 1.34x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream | 462,250 | 1.00 | 1.00 | 26,113.2 | 0.056 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.00 | 182,843.6 | 0.396 | weight_read | 0.39x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 3.17 | 138,770.2 | 0.300 | weight_read | 0.30x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-perregion-romfill | 462,250 | 7.66 | 1.91 | 303,750.8 | 0.657 | layer_fixed_latency | 0.65x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 672,501.7 | 1.212 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 687,650.0 | 1.240 | kv_read | 1.02x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-perstream | 462,250 | 1.00 | 102.40 | 26,113.2 | 0.056 | weight_read | 0.04x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 1.80 | 191,093.3 | 0.413 | weight_read | 0.28x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 4.63 | 258,057.6 | 0.558 | weight_read | 0.38x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-perregion-romfill | 462,250 | 7.66 | 1.92 | 572,974.0 | 1.240 | kv_read | 0.85x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 814,285.6 | 1.468 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 809,992.5 | 1.460 | kv_read | 0.99x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-perstream | 462,250 | 1.00 | 409.60 | 26,113.2 | 0.056 | weight_read | 0.03x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perstream-romfill | 462,250 | 7.66 | 7.21 | 199,508.3 | 0.432 | weight_read | 0.25x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x10-perregion | 462,250 | 1.00 | 6.73 | 400,925.7 | 0.867 | weight_read | 0.49x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x10-perregion-romfill | 462,250 | 7.66 | 1.92 | 686,459.4 | 1.485 | kv_read | 0.84x |

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
| DeepSeek-V4-Pro-0813 | 1 | 74 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 81 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 81 | 3.16 | 1.017 | 1.274 | 1.25x |
| DeepSeek-V4-Pro-0813 | 1024 | 81 | 12.64 | 1.094 | 2.301 | 2.10x |
| DeepSeek-V4-Pro-0813 | 4096 | 81 | 50.57 | 1.439 | 4.371 | 3.04x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 2 | 29 | 9.90 | 5.83 | 1.70x |
| DeepSeek-V4-Pro-0813 | 4 | 29 | 16.26 | 7.87 | 2.07x |
| DeepSeek-V4-Pro-0813 | 8 | 29 | 23.12 | 10.16 | 2.27x |
| DeepSeek-V4-Pro-0813 | 16 | 29 | 27.56 | 12.57 | 2.19x |
| DeepSeek-V4-Pro-0813 | 32 | 29 | 28.86 | 14.82 | 1.95x |
| DeepSeek-V4-Pro-0813 | 64 | 29 | 28.99 | 16.64 | 1.74x |
| DeepSeek-V4-Pro-0813 | 256 | 29 | 29.00 | 18.25 | 1.59x |
| DeepSeek-V4-Pro-0813 | 1024 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4-Pro-0813 | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 2 | 38 | 10.34 | 6.29 | 1.64x |
| DeepSeek-V4-Pro-0813 | 4 | 38 | 17.66 | 8.67 | 2.04x |
| DeepSeek-V4-Pro-0813 | 8 | 38 | 26.69 | 11.45 | 2.33x |
| DeepSeek-V4-Pro-0813 | 16 | 38 | 34.12 | 14.46 | 2.36x |
| DeepSeek-V4-Pro-0813 | 32 | 38 | 37.34 | 17.39 | 2.15x |
| DeepSeek-V4-Pro-0813 | 64 | 38 | 37.94 | 19.83 | 1.91x |
| DeepSeek-V4-Pro-0813 | 256 | 38 | 38.00 | 22.03 | 1.72x |
| DeepSeek-V4-Pro-0813 | 1024 | 38 | 38.00 | 22.12 | 1.72x |
| DeepSeek-V4-Pro-0813 | 1 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4-Pro-0813 | 2 | 41 | 10.44 | 6.42 | 1.63x |
| DeepSeek-V4-Pro-0813 | 4 | 41 | 18.02 | 8.90 | 2.02x |
| DeepSeek-V4-Pro-0813 | 8 | 41 | 27.65 | 11.82 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 41 | 36.04 | 15.02 | 2.40x |
| DeepSeek-V4-Pro-0813 | 32 | 41 | 40.04 | 18.16 | 2.20x |
| DeepSeek-V4-Pro-0813 | 64 | 41 | 40.90 | 20.80 | 1.97x |
| DeepSeek-V4-Pro-0813 | 256 | 41 | 41.00 | 23.19 | 1.77x |
| DeepSeek-V4-Pro-0813 | 1024 | 41 | 41.00 | 23.29 | 1.76x |
| DeepSeek-V4-Pro-0813 | 1 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Pro-0813 | 2 | 43 | 10.51 | 6.50 | 1.62x |
| DeepSeek-V4-Pro-0813 | 4 | 43 | 18.23 | 9.04 | 2.02x |
| DeepSeek-V4-Pro-0813 | 8 | 43 | 28.24 | 12.05 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 43 | 37.25 | 15.38 | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | 43 | 41.80 | 18.66 | 2.24x |
| DeepSeek-V4-Pro-0813 | 64 | 43 | 42.86 | 21.42 | 2.00x |
| DeepSeek-V4-Pro-0813 | 256 | 43 | 42.99 | 23.94 | 1.80x |
| DeepSeek-V4-Pro-0813 | 1024 | 43 | 42.99 | 24.04 | 1.79x |
| DeepSeek-V4-Pro-0813 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4-Pro-0813 | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4-Pro-0813 | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4-Pro-0813 | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4-Pro-0813 | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4-Pro-0813 | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4-Pro-0813 | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4-Pro-0813 | 4096 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4-Pro-0813 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4-Pro-0813 | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4-Pro-0813 | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4-Pro-0813 | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4-Pro-0813 | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4-Pro-0813 | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4-Pro-0813 | 4096 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4-Pro-0813 | 1 | 75 | 5.80 | 5.10 | 1.14x |
| DeepSeek-V4-Pro-0813 | 2 | 75 | 11.08 | 7.51 | 1.47x |
| DeepSeek-V4-Pro-0813 | 4 | 75 | 20.25 | 10.63 | 1.91x |
| DeepSeek-V4-Pro-0813 | 8 | 75 | 34.25 | 14.85 | 2.31x |
| DeepSeek-V4-Pro-0813 | 16 | 75 | 51.21 | 19.78 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 75 | 65.25 | 24.96 | 2.61x |
| DeepSeek-V4-Pro-0813 | 64 | 75 | 72.16 | 29.58 | 2.44x |
| DeepSeek-V4-Pro-0813 | 256 | 75 | 74.53 | 34.01 | 2.19x |
| DeepSeek-V4-Pro-0813 | 1024 | 75 | 74.57 | 34.20 | 2.18x |
| DeepSeek-V4-Pro-0813 | 4096 | 75 | 74.57 | 34.20 | 2.18x |
| DeepSeek-V4-Pro-0813 | 1 | 79 | 5.81 | 5.13 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 79 | 11.12 | 7.61 | 1.46x |
| DeepSeek-V4-Pro-0813 | 4 | 79 | 20.40 | 10.76 | 1.89x |
| DeepSeek-V4-Pro-0813 | 8 | 79 | 34.73 | 15.12 | 2.30x |
| DeepSeek-V4-Pro-0813 | 16 | 79 | 52.43 | 20.21 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 79 | 67.61 | 25.59 | 2.64x |
| DeepSeek-V4-Pro-0813 | 64 | 79 | 75.46 | 30.42 | 2.48x |
| DeepSeek-V4-Pro-0813 | 256 | 79 | 78.35 | 35.08 | 2.23x |
| DeepSeek-V4-Pro-0813 | 1024 | 79 | 78.41 | 35.27 | 2.22x |
| DeepSeek-V4-Pro-0813 | 4096 | 79 | 78.41 | 35.27 | 2.22x |
| DeepSeek-V4-Pro-0813 | 1 | 80 | 5.82 | 5.14 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 80 | 11.13 | 7.64 | 1.46x |
| DeepSeek-V4-Pro-0813 | 4 | 80 | 20.43 | 10.80 | 1.89x |
| DeepSeek-V4-Pro-0813 | 8 | 80 | 34.84 | 15.19 | 2.29x |
| DeepSeek-V4-Pro-0813 | 16 | 80 | 52.72 | 20.32 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 80 | 68.18 | 25.75 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 80 | 76.28 | 30.63 | 2.49x |
| DeepSeek-V4-Pro-0813 | 256 | 80 | 79.30 | 35.34 | 2.24x |
| DeepSeek-V4-Pro-0813 | 1024 | 80 | 79.36 | 35.53 | 2.23x |
| DeepSeek-V4-Pro-0813 | 4096 | 80 | 79.36 | 35.53 | 2.23x |
| DeepSeek-V4-Pro-0813 | 1 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 83 | 11.15 | 7.71 | 1.45x |
| DeepSeek-V4-Pro-0813 | 4 | 83 | 20.53 | 10.90 | 1.88x |
| DeepSeek-V4-Pro-0813 | 8 | 83 | 35.16 | 15.38 | 2.29x |
| DeepSeek-V4-Pro-0813 | 16 | 83 | 53.57 | 20.63 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 83 | 69.85 | 26.20 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 83 | 78.68 | 31.24 | 2.52x |
| DeepSeek-V4-Pro-0813 | 256 | 83 | 82.14 | 36.11 | 2.27x |
| DeepSeek-V4-Pro-0813 | 1024 | 83 | 82.21 | 36.31 | 2.26x |
| DeepSeek-V4-Pro-0813 | 4096 | 83 | 82.21 | 36.31 | 2.26x |
| DeepSeek-V4-Pro-0813 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 87 | 11.19 | 7.80 | 1.44x |
| DeepSeek-V4-Pro-0813 | 4 | 87 | 20.65 | 11.02 | 1.87x |
| DeepSeek-V4-Pro-0813 | 8 | 87 | 35.56 | 15.63 | 2.27x |
| DeepSeek-V4-Pro-0813 | 16 | 87 | 54.63 | 21.03 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 87 | 71.99 | 26.79 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 87 | 81.81 | 32.02 | 2.55x |
| DeepSeek-V4-Pro-0813 | 256 | 87 | 85.89 | 37.11 | 2.31x |
| DeepSeek-V4-Pro-0813 | 1024 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4-Pro-0813 | 4096 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4-Pro-0813 | 1 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 92 | 11.23 | 7.90 | 1.42x |
| DeepSeek-V4-Pro-0813 | 4 | 92 | 20.79 | 11.17 | 1.86x |
| DeepSeek-V4-Pro-0813 | 8 | 92 | 36.02 | 15.94 | 2.26x |
| DeepSeek-V4-Pro-0813 | 16 | 92 | 55.87 | 21.51 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 92 | 74.53 | 27.50 | 2.71x |
| DeepSeek-V4-Pro-0813 | 64 | 92 | 85.60 | 32.97 | 2.60x |
| DeepSeek-V4-Pro-0813 | 256 | 92 | 90.51 | 38.32 | 2.36x |
| DeepSeek-V4-Pro-0813 | 1024 | 92 | 90.62 | 38.54 | 2.35x |
| DeepSeek-V4-Pro-0813 | 4096 | 92 | 90.62 | 38.54 | 2.35x |
| DeepSeek-V4-Pro-0813 | 1 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 98 | 11.27 | 8.02 | 1.40x |
| DeepSeek-V4-Pro-0813 | 4 | 98 | 20.94 | 11.34 | 1.85x |
| DeepSeek-V4-Pro-0813 | 8 | 98 | 36.52 | 16.28 | 2.24x |
| DeepSeek-V4-Pro-0813 | 16 | 98 | 57.24 | 22.06 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 98 | 77.39 | 28.31 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 98 | 89.96 | 34.06 | 2.64x |
| DeepSeek-V4-Pro-0813 | 256 | 98 | 95.95 | 39.72 | 2.42x |
| DeepSeek-V4-Pro-0813 | 1024 | 98 | 96.09 | 39.95 | 2.41x |
| DeepSeek-V4-Pro-0813 | 4096 | 98 | 96.09 | 39.95 | 2.41x |
| DeepSeek-V4-Pro-0813 | 1 | 100 | 5.85 | 5.28 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 100 | 11.28 | 8.06 | 1.40x |
| DeepSeek-V4-Pro-0813 | 4 | 100 | 20.99 | 11.39 | 1.84x |
| DeepSeek-V4-Pro-0813 | 8 | 100 | 36.67 | 16.39 | 2.24x |
| DeepSeek-V4-Pro-0813 | 16 | 100 | 57.67 | 22.23 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 100 | 78.30 | 28.57 | 2.74x |
| DeepSeek-V4-Pro-0813 | 64 | 100 | 91.38 | 34.42 | 2.66x |
| DeepSeek-V4-Pro-0813 | 256 | 100 | 97.74 | 40.17 | 2.43x |
| DeepSeek-V4-Pro-0813 | 1024 | 100 | 97.89 | 40.41 | 2.42x |
| DeepSeek-V4-Pro-0813 | 4096 | 100 | 97.89 | 40.41 | 2.42x |
| DeepSeek-V4-Pro-0813 | 1 | 106 | 5.86 | 5.32 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 106 | 11.31 | 8.17 | 1.38x |
| DeepSeek-V4-Pro-0813 | 4 | 106 | 21.12 | 11.55 | 1.83x |
| DeepSeek-V4-Pro-0813 | 8 | 106 | 37.11 | 16.71 | 2.22x |
| DeepSeek-V4-Pro-0813 | 16 | 106 | 58.88 | 22.74 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 106 | 80.91 | 29.33 | 2.76x |
| DeepSeek-V4-Pro-0813 | 64 | 106 | 95.49 | 35.44 | 2.69x |
| DeepSeek-V4-Pro-0813 | 256 | 106 | 103.03 | 41.49 | 2.48x |
| DeepSeek-V4-Pro-0813 | 1024 | 106 | 103.22 | 41.75 | 2.47x |
| DeepSeek-V4-Pro-0813 | 4096 | 106 | 103.22 | 41.75 | 2.47x |
| DeepSeek-V4-Pro-0813 | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 110 | 11.33 | 8.24 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 110 | 21.20 | 11.65 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 110 | 37.37 | 16.92 | 2.21x |
| DeepSeek-V4-Pro-0813 | 16 | 110 | 59.63 | 23.06 | 2.59x |
| DeepSeek-V4-Pro-0813 | 32 | 110 | 82.55 | 29.82 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 110 | 98.14 | 36.10 | 2.72x |
| DeepSeek-V4-Pro-0813 | 256 | 110 | 106.49 | 42.35 | 2.51x |
| DeepSeek-V4-Pro-0813 | 1024 | 110 | 106.70 | 42.61 | 2.50x |
| DeepSeek-V4-Pro-0813 | 4096 | 110 | 106.70 | 42.61 | 2.50x |
| DeepSeek-V4-Pro-0813 | 1 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 113 | 11.35 | 8.30 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 113 | 21.26 | 11.72 | 1.81x |
| DeepSeek-V4-Pro-0813 | 8 | 113 | 37.56 | 17.07 | 2.20x |
| DeepSeek-V4-Pro-0813 | 16 | 113 | 60.17 | 23.29 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 113 | 83.74 | 30.18 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 113 | 100.07 | 36.59 | 2.74x |
| DeepSeek-V4-Pro-0813 | 256 | 113 | 109.05 | 42.97 | 2.54x |
| DeepSeek-V4-Pro-0813 | 1024 | 113 | 109.28 | 43.24 | 2.53x |
| DeepSeek-V4-Pro-0813 | 4096 | 113 | 109.28 | 43.24 | 2.53x |
| DeepSeek-V4-Pro-0813 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 116 | 11.36 | 8.35 | 1.36x |
| DeepSeek-V4-Pro-0813 | 4 | 116 | 21.31 | 11.79 | 1.81x |
| DeepSeek-V4-Pro-0813 | 8 | 116 | 37.74 | 17.21 | 2.19x |
| DeepSeek-V4-Pro-0813 | 16 | 116 | 60.68 | 23.52 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 116 | 84.89 | 30.52 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 116 | 101.95 | 37.06 | 2.75x |
| DeepSeek-V4-Pro-0813 | 256 | 116 | 111.57 | 43.59 | 2.56x |
| DeepSeek-V4-Pro-0813 | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4-Pro-0813 | 4096 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4-Pro-0813 | 1 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 118 | 11.37 | 8.38 | 1.36x |
| DeepSeek-V4-Pro-0813 | 4 | 118 | 21.34 | 11.84 | 1.80x |
| DeepSeek-V4-Pro-0813 | 8 | 118 | 37.86 | 17.30 | 2.19x |
| DeepSeek-V4-Pro-0813 | 16 | 118 | 61.02 | 23.67 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 118 | 85.64 | 30.75 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 118 | 103.19 | 37.37 | 2.76x |
| DeepSeek-V4-Pro-0813 | 256 | 118 | 113.24 | 43.99 | 2.57x |
| DeepSeek-V4-Pro-0813 | 1024 | 118 | 113.51 | 44.27 | 2.56x |
| DeepSeek-V4-Pro-0813 | 4096 | 118 | 113.51 | 44.27 | 2.56x |
| DeepSeek-V4-Pro-0813 | 1 | 120 | 5.88 | 5.39 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 120 | 11.38 | 8.41 | 1.35x |
| DeepSeek-V4-Pro-0813 | 4 | 120 | 21.38 | 11.88 | 1.80x |
| DeepSeek-V4-Pro-0813 | 8 | 120 | 37.97 | 17.40 | 2.18x |
| DeepSeek-V4-Pro-0813 | 16 | 120 | 61.34 | 23.81 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 120 | 86.37 | 30.98 | 2.79x |
| DeepSeek-V4-Pro-0813 | 64 | 120 | 104.41 | 37.68 | 2.77x |
| DeepSeek-V4-Pro-0813 | 256 | 120 | 114.89 | 44.39 | 2.59x |
| DeepSeek-V4-Pro-0813 | 1024 | 120 | 115.17 | 44.68 | 2.58x |
| DeepSeek-V4-Pro-0813 | 4096 | 120 | 115.17 | 44.68 | 2.58x |
| DeepSeek-V4-Pro-0813 | 1 | 124 | 5.88 | 5.40 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 124 | 11.40 | 8.47 | 1.35x |
| DeepSeek-V4-Pro-0813 | 4 | 124 | 21.44 | 11.97 | 1.79x |
| DeepSeek-V4-Pro-0813 | 8 | 124 | 38.18 | 17.58 | 2.17x |
| DeepSeek-V4-Pro-0813 | 16 | 124 | 61.96 | 24.09 | 2.57x |
| DeepSeek-V4-Pro-0813 | 32 | 124 | 87.79 | 31.41 | 2.79x |
| DeepSeek-V4-Pro-0813 | 64 | 124 | 106.78 | 38.28 | 2.79x |
| DeepSeek-V4-Pro-0813 | 256 | 124 | 118.15 | 45.18 | 2.62x |
| DeepSeek-V4-Pro-0813 | 1024 | 124 | 118.47 | 45.47 | 2.61x |
| DeepSeek-V4-Pro-0813 | 4096 | 124 | 118.47 | 45.47 | 2.61x |
| DeepSeek-V4-Pro-0813 | 1 | 132 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 132 | 11.43 | 8.59 | 1.33x |
| DeepSeek-V4-Pro-0813 | 4 | 132 | 21.55 | 12.15 | 1.77x |
| DeepSeek-V4-Pro-0813 | 8 | 132 | 38.58 | 17.92 | 2.15x |
| DeepSeek-V4-Pro-0813 | 16 | 132 | 63.12 | 24.63 | 2.56x |
| DeepSeek-V4-Pro-0813 | 32 | 132 | 90.45 | 32.25 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 132 | 111.33 | 39.45 | 2.82x |
| DeepSeek-V4-Pro-0813 | 256 | 132 | 124.50 | 46.70 | 2.67x |
| DeepSeek-V4-Pro-0813 | 1024 | 132 | 124.88 | 47.00 | 2.66x |
| DeepSeek-V4-Pro-0813 | 4096 | 132 | 124.88 | 47.00 | 2.66x |
| DeepSeek-V4-Pro-0813 | 1 | 133 | 5.89 | 5.44 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 133 | 11.43 | 8.60 | 1.33x |
| DeepSeek-V4-Pro-0813 | 4 | 133 | 21.57 | 12.17 | 1.77x |
| DeepSeek-V4-Pro-0813 | 8 | 133 | 38.62 | 17.96 | 2.15x |
| DeepSeek-V4-Pro-0813 | 16 | 133 | 63.26 | 24.69 | 2.56x |
| DeepSeek-V4-Pro-0813 | 32 | 133 | 90.77 | 32.35 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 133 | 111.88 | 39.59 | 2.83x |
| DeepSeek-V4-Pro-0813 | 256 | 133 | 125.28 | 46.88 | 2.67x |
| DeepSeek-V4-Pro-0813 | 1024 | 133 | 125.67 | 47.19 | 2.66x |
| DeepSeek-V4-Pro-0813 | 4096 | 133 | 125.67 | 47.19 | 2.66x |
| DeepSeek-V4-Pro-0813 | 1 | 134 | 5.89 | 5.44 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 134 | 11.43 | 8.62 | 1.33x |
| DeepSeek-V4-Pro-0813 | 4 | 134 | 21.58 | 12.19 | 1.77x |
| DeepSeek-V4-Pro-0813 | 8 | 134 | 38.67 | 18.00 | 2.15x |
| DeepSeek-V4-Pro-0813 | 16 | 134 | 63.39 | 24.76 | 2.56x |
| DeepSeek-V4-Pro-0813 | 32 | 134 | 91.09 | 32.45 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 134 | 112.43 | 39.73 | 2.83x |
| DeepSeek-V4-Pro-0813 | 256 | 134 | 126.06 | 47.07 | 2.68x |
| DeepSeek-V4-Pro-0813 | 1024 | 134 | 126.45 | 47.38 | 2.67x |
| DeepSeek-V4-Pro-0813 | 4096 | 134 | 126.45 | 47.38 | 2.67x |
| DeepSeek-V4-Pro-0813 | 1 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 147 | 11.47 | 8.79 | 1.31x |
| DeepSeek-V4-Pro-0813 | 4 | 147 | 21.74 | 12.45 | 1.75x |
| DeepSeek-V4-Pro-0813 | 8 | 147 | 39.21 | 18.49 | 2.12x |
| DeepSeek-V4-Pro-0813 | 16 | 147 | 65.01 | 25.54 | 2.55x |
| DeepSeek-V4-Pro-0813 | 32 | 147 | 94.92 | 33.70 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 147 | 119.17 | 41.48 | 2.87x |
| DeepSeek-V4-Pro-0813 | 256 | 147 | 135.80 | 49.37 | 2.75x |
| DeepSeek-V4-Pro-0813 | 1024 | 147 | 136.31 | 49.71 | 2.74x |
| DeepSeek-V4-Pro-0813 | 4096 | 147 | 136.31 | 49.71 | 2.74x |
| DeepSeek-V4-Pro-0813 | 1 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 150 | 11.48 | 8.83 | 1.30x |
| DeepSeek-V4-Pro-0813 | 4 | 150 | 21.77 | 12.51 | 1.74x |
| DeepSeek-V4-Pro-0813 | 8 | 150 | 39.33 | 18.59 | 2.12x |
| DeepSeek-V4-Pro-0813 | 16 | 150 | 65.35 | 25.71 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 150 | 95.74 | 33.98 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 150 | 120.64 | 41.87 | 2.88x |
| DeepSeek-V4-Pro-0813 | 256 | 150 | 137.97 | 49.89 | 2.77x |
| DeepSeek-V4-Pro-0813 | 1024 | 150 | 138.50 | 50.23 | 2.76x |
| DeepSeek-V4-Pro-0813 | 4096 | 150 | 138.50 | 50.23 | 2.76x |
| DeepSeek-V4-Pro-0813 | 1 | 151 | 5.90 | 5.50 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 151 | 11.49 | 8.84 | 1.30x |
| DeepSeek-V4-Pro-0813 | 4 | 151 | 21.78 | 12.53 | 1.74x |
| DeepSeek-V4-Pro-0813 | 8 | 151 | 39.36 | 18.63 | 2.11x |
| DeepSeek-V4-Pro-0813 | 16 | 151 | 65.46 | 25.77 | 2.54x |
| DeepSeek-V4-Pro-0813 | 32 | 151 | 96.00 | 34.07 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 151 | 121.12 | 41.99 | 2.88x |
| DeepSeek-V4-Pro-0813 | 256 | 151 | 138.68 | 50.06 | 2.77x |
| DeepSeek-V4-Pro-0813 | 1024 | 151 | 139.23 | 50.40 | 2.76x |
| DeepSeek-V4-Pro-0813 | 4096 | 151 | 139.23 | 50.40 | 2.76x |
| DeepSeek-V4-Pro-0813 | 1 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 157 | 11.50 | 8.91 | 1.29x |
| DeepSeek-V4-Pro-0813 | 4 | 157 | 21.84 | 12.64 | 1.73x |
| DeepSeek-V4-Pro-0813 | 8 | 157 | 39.58 | 18.83 | 2.10x |
| DeepSeek-V4-Pro-0813 | 16 | 157 | 66.10 | 26.10 | 2.53x |
| DeepSeek-V4-Pro-0813 | 32 | 157 | 97.56 | 34.60 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 157 | 123.95 | 42.74 | 2.90x |
| DeepSeek-V4-Pro-0813 | 256 | 157 | 142.90 | 51.05 | 2.80x |
| DeepSeek-V4-Pro-0813 | 1024 | 157 | 143.50 | 51.41 | 2.79x |
| DeepSeek-V4-Pro-0813 | 4096 | 157 | 143.50 | 51.41 | 2.79x |
| DeepSeek-V4-Pro-0813 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 173 | 11.54 | 9.09 | 1.27x |
| DeepSeek-V4-Pro-0813 | 4 | 173 | 21.98 | 12.94 | 1.70x |
| DeepSeek-V4-Pro-0813 | 8 | 173 | 40.08 | 19.31 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 173 | 67.63 | 26.93 | 2.51x |
| DeepSeek-V4-Pro-0813 | 32 | 173 | 101.33 | 35.95 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 173 | 130.91 | 44.63 | 2.93x |
| DeepSeek-V4-Pro-0813 | 256 | 173 | 153.57 | 53.58 | 2.87x |
| DeepSeek-V4-Pro-0813 | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4-Pro-0813 | 4096 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4-Pro-0813 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 231 | 11.63 | 9.58 | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | 231 | 22.34 | 13.86 | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | 231 | 41.34 | 20.63 | 2.00x |
| DeepSeek-V4-Pro-0813 | 16 | 231 | 71.61 | 29.55 | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | 231 | 111.55 | 40.16 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 231 | 150.80 | 50.51 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 231 | 186.03 | 61.46 | 3.03x |
| DeepSeek-V4-Pro-0813 | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4-Pro-0813 | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 289 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 289 | 11.68 | 9.92 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 289 | 22.56 | 14.64 | 1.54x |
| DeepSeek-V4-Pro-0813 | 8 | 289 | 42.13 | 21.55 | 1.96x |
| DeepSeek-V4-Pro-0813 | 16 | 289 | 74.15 | 31.75 | 2.33x |
| DeepSeek-V4-Pro-0813 | 32 | 289 | 118.36 | 43.43 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 289 | 164.88 | 55.14 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 289 | 210.82 | 67.86 | 3.11x |
| DeepSeek-V4-Pro-0813 | 1024 | 289 | 212.64 | 68.42 | 3.11x |
| DeepSeek-V4-Pro-0813 | 4096 | 289 | 212.64 | 68.42 | 3.11x |
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
| gpu | DeepSeek-V4-Pro-0813 | 1 | 1,259.70 | 52.1% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 371.74 | 79.3% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
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
| DeepSeek-V4-Pro-0813 | 1 | 74 | 96.99% | 159.24 | 2.22 |
| DeepSeek-V4-Pro-0813 | 2 | 2 | 2.42% | 6.13 | 2.22 |
| DeepSeek-V4-Pro-0813 | 4 | 2 | 2.42% | 6.13 | 2.22 |
| DeepSeek-V4-Pro-0813 | 8 | 2 | 2.42% | 6.13 | 2.22 |
| DeepSeek-V4-Pro-0813 | 16 | 2 | 2.42% | 6.13 | 2.22 |
| DeepSeek-V4-Pro-0813 | 32 | 2 | 2.42% | 6.13 | 2.22 |

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
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 92.3 | 14,588.9 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 92.3 | 14,588.9 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 92.3 | 14,588.9 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 92.3 | 14,588.9 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 92.3 | 14,588.9 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 92.3 | 14,588.9 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 92.3 | 14,588.9 |
| DeepSeek-V4-Pro-0813 | 256 | 2.52% | 47.5 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 57.5 | 14,715.6 |
| DeepSeek-V4-Pro-0813 | 1024 | 9.70% | 106.6 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 14.5 | 14,849.4 |
| DeepSeek-V4-Pro-0813 | 4096 | 33.52% | 302.4 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 3.6 | 14,864.7 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 25 |
| gpu | layer_fixed_latency | 381 |
| gpu | link_latency | 1239 |
| gpu | thermal | 60 |
| gpu | weight_read | 475 |
| rom | compute | 649 |
| rom | infeasible | 1752 |
| rom | kv_read | 48 |
| rom | layer_fixed_latency | 345 |
| rom | link_latency | 934 |
| rom | weight_read | 292 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 25 |
| rom | CAPACITY | 1752 |

## Mechanical consistency audit

**FAIL** over 134,509 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x147', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x156', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x180', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x197', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x216', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x221', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x235', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x288', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x147', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x156', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x180', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x197', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x216', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x221', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x235', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x288', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x147', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x156', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x180', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x197', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x216', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x221', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x235', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x288', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x147', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x156', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x180', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x197', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x216', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x221', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x235', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x288', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x147', 'DeepSeek-V4-Pro-0813', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 75 |
| derived | 49 |
| assumed | 84 |

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

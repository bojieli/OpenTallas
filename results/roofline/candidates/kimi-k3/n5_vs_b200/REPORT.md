# Area-constrained roofline: n5_vs_b200-kimi-k3

> CANDIDATE MODEL under n5_vs_b200: Kimi-K3 at 200,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 91x (ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream, 908 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 3 devices. On the GPU side the correction reaches 10x (b200_sxm-x462-pipeline, 462 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 58 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Kimi-K3 takes 6 x 46,225 mm2 (277,350 mm2, wafer, KV in SRAM) at 2,100 tok/s per user and 8 tok/s per 1,000 mm2, holding 1 session, against 173 copies of one unified HBM die at the same silicon: 7.4x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Kimi-K3 on 369,800 mm2 of ROM silicon at 2,251 tok/s per user against 369,600 mm2 of b200_sxm-x231-nvl72-hybrid at 284 tok/s: **7.9x**, ROM binding on `layer_fixed_latency` and the GPU on `layer_fixed_latency`. It holds 1 resident session against the GPU cluster's 11,157. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 6.76x to it.** At 223,310 mm2 on Kimi-K3 the pipeline-only GPU delivers 42.86 tok/s and the same silicon running hybrid delivers 290 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (Kimi-K3, ROM binding on `link_latency`) to 1.01x (Kimi-K3, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** Kimi-K3 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 73 to 23,845 tok/s, and its rate with every slot occupied from 23,717 to 23,845. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 327 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,367 us over NVLink, capping per-user decode at 732 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 482.1 us and cap it at 2,074 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 10 of 10 operating points and an array 0; on tokens per second per square millimetre the same points go 5 to the array and 5 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 61 of 3331 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 5.8x of aggregate throughput (Kimi-K3). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 5.76x, on Kimi-K3 at batch 4096, where the busiest region carries 3.43x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 10 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 279 of 3,331 feasible points (8.4%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `Kimi-K3/b200_sxm-x91-pipeline` at batch 4096 on 145,600 mm2, throttled 1.20x from 6 to 5 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 74% weight read against 73.7% weight read. The ROM sweep is not what melts it.


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

### Kimi-K3 at 200,000 tokens

**Recommended: `ROM-N5-native-SRAMKV-wafer-hybrid-x6`** -- 6 x 46,225 mm2 wafers, 277,350 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **2,099.9 tok/s per user** (0.48 ms/token), binding on `layer_fixed_latency`
- **7.6 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 2,100 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 19,429 W at 0.070 W/mm2, 9,252.4 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 173 copies of one unified HBM die -- `b200_sxm-x173-nvl72-hybrid`, 276,800 mm2, area ratio 1.0020 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 277,350 | 276,800 | 1.0020 |
| user tok/s | 2,099.9 | 284.2 | 7.39x |
| aggregate tok/s | 2,100 | 853 | 0.28x |
| resident sessions | 1 | 8,233 | -- |
| J/token | 9.2524 | 228.4939 | 24.7x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 8,233 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x72-nvl72-tensor` at 115,200 mm2 and 291.3 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 323,575 | 2,254.6 | 7.0 | 1 | 7.82x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 323,575 | 2,254.6 | 7.0 | 1 | 7.82x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-hybrid-x274` | 223,310 | 890.9 | 4.0 | 1 | 3.07x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 2,099.9 | 7.6 | 1 | 7.39x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 2,099.9 | 7.6 | -- | 7.6 | ACCEPT |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 323,575 | 2,254.6 | 7.0 | 3.3 | 7.6 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x6` **<-- recommended** | 277,350 | 6 | 2,099.9 | 2,100 | 7.6 | 1 | `layer_fixed_latency` | 19,429 | 9,252.4 | `b200_sxm-x173-nvl72-hybrid` | 7.39x |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 323,575 | 7 | 2,254.6 | 2,255 | 7.0 | 1 | `layer_fixed_latency` | 26,147 | 11,597.2 | `b200_sxm-x202-nvl72-hybrid` | 7.82x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 180 | densest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x313` | 255,095 | 1,240.1 | 4.9 | 1 |
| array | 180 | fastest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 321,925 | 1,428.2 | 4.4 | 1 |
| array | 180 | smallest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x274` | 223,310 | 890.9 | 4.0 | 1 |
| wafer | 30 | densest | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 2,099.9 | 7.6 | 1 |
| wafer | 30 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 323,575 | 2,254.6 | 7.0 | 1 |
| wafer | 30 | smallest | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 2,099.9 | 7.6 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 321,925 | 1,428.2 | 1,428 | 1 | 25,825 | 18,082.1 | `layer_fixed_latency` | `b200_sxm-x201-nvl72-hybrid` | 288.3 | 9,645 | 259,473.6 | 1.001 | 4.95x | 14.3x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 323,575 | 2,254.6 | 2,255 | 1 | 26,147 | 11,597.2 | `layer_fixed_latency` | `b200_sxm-x202-nvl72-hybrid` | 288.4 | 9,695 | 260,580.0 | 1.001 | 7.82x | 22.5x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | 321,925 | 1,428.2 | 1,428 | 1 | 25,825 | 18,082.1 | `layer_fixed_latency` | `b200_sxm-x201-nvl72-hybrid` | 288.3 | 9,645 | 259,473.6 | 1.001 | 4.95x | 14.3x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 323,575 | 2,254.6 | -- | 1 | -- | 11,597.2 | -- | -- | -- | -- | -- | 0.995 | 1.58x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,322.3 | 9,256 | 12,474 | 35,850 | 12,367.5 | `layer_fixed_latency` | `b200_sxm-x202-nvl72-hybrid` | 288.4 | 9,695 | 137,868.0 | 0.999 | 4.58x | 11.1x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 739,600 | 2,224.5 | 35,592 | 4,334 | 105,204 | 20,317.0 | `layer_fixed_latency` | `b200_sxm-x462-nvl72-hybrid` | 286.0 | 22,800 | 298,185.2 | 1.001 | 7.78x | 14.7x |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,322.3 | 9,256 | 12,474 | 35,850 | 6,421.6 | `layer_fixed_latency` | `b200_sxm-x202-nvl72-hybrid` | 286.0 | 9,695 | 74,098.6 | 0.999 | 4.62x | 11.5x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 739,600 | 2,224.5 | 35,592 | 4,334 | 105,204 | 10,396.3 | `layer_fixed_latency` | `b200_sxm-x462-nvl72-hybrid` | 286.0 | 22,800 | 156,670.6 | 1.001 | 7.78x | 15.1x |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,301.1 | 16,914 | 12,474 | 39,493 | 3,496.9 | `layer_fixed_latency` | `b200_sxm-x202-nvl72-hybrid` | 276.9 | 9,695 | 39,770.8 | 0.999 | 4.70x | 11.4x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 739,600 | 2,224.5 | 35,592 | 4,334 | 105,204 | 5,436.0 | `layer_fixed_latency` | `b200_sxm-x462-nvl72-hybrid` | 284.8 | 22,800 | 84,749.2 | 1.001 | 7.81x | 15.6x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,154.8 | 18,476 | 12,474 | 40,116 | 2,171.2 | `layer_fixed_latency` | `b200_sxm-x202-nvl72-hybrid` | 260.6 | 9,695 | 22,537.1 | 0.999 | 4.43x | 10.4x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 739,600 | 2,224.5 | 35,592 | 4,334 | 105,204 | 2,955.8 | `layer_fixed_latency` | `b200_sxm-x462-nvl72-hybrid` | 275.6 | 22,800 | 45,273.4 | 1.001 | 8.07x | 15.3x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 911.1 | 29,155 | 12,474 | 45,094 | 1,546.7 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 234.2 | 9,695 | 13,788.4 | 0.999 | 3.89x | 8.9x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 739,600 | 1,760.7 | 56,343 | 4,334 | 114,890 | 2,039.1 | `layer_fixed_latency` | `b200_sxm-x462-nvl72-hybrid` | 259.0 | 22,800 | 25,475.2 | 1.001 | 6.80x | 12.5x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 580.6 | 37,157 | 12,474 | 48,840 | 1,314.4 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 197.6 | 9,695 | 9,177.8 | 0.999 | 2.94x | 7.0x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 739,600 | 1,342.9 | 85,946 | 4,334 | 128,828 | 1,498.9 | `kv_read` | `b200_sxm-x462-nvl72-hybrid` | 232.1 | 22,800 | 15,461.2 | 1.001 | 5.79x | 10.3x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 176.3 | 45,126 | 12,474 | 52,557 | 1,164.7 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 117.0 | 9,695 | 4,655.8 | 0.999 | 1.51x | 4.0x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 739,600 | 511.9 | 131,034 | 4,334 | 150,084 | 1,145.4 | `kv_read` | `b200_sxm-x462-nvl72-hybrid` | 152.2 | 22,800 | 7,956.2 | 1.001 | 3.36x | 6.9x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 322,740 | 45.9 | 46,989 | 12,474 | 52,798 | 1,123.6 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 58.0 | 9,695 | 2,426.5 | 0.999 | 0.79x | 2.2x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 739,600 | 144.2 | 147,684 | 4,334 | 157,938 | 1,069.4 | `kv_read` | `b200_sxm-x462-nvl72-hybrid` | 78.2 | 22,800 | 4,525.0 | 1.001 | 1.84x | 4.2x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x396` | 322,740 | 11.5 | 47,169 | 12,474 | 52,384 | 1,110.6 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 25.1 | 9,695 | 1,962.7 | 0.999 | 0.46x | 1.8x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 739,600 | 36.9 | 151,170 | 4,334 | 156,082 | 1,032.5 | `kv_read` | `b200_sxm-x462-nvl72-hybrid` | 36.7 | 22,800 | 2,430.1 | 1.001 | 1.01x | 2.4x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 277,350 | wafer | SRAM | 1 |
| 2-4 | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | array | HBM | 10,710 |
| 8 | `ROM-N5-native-HBMKV-array-hw-hybrid-x368` | 299,920 | array | HBM | 11,592 |
| 16 | `ROM-N5-native-HBMKV-array-hw-hybrid-x389` | 317,035 | array | HBM | 12,253 |
| 32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | array | HBM | 12,474 |
| 64-256 | `ROM-N5-native-HBMKV-wafer-hybrid-x16` | 739,600 | wafer | HBM | 4,334 |
| 1024-4096 | `ROM-N5-native-HBMKV-wafer-pipeline-x16` | 739,600 | wafer | HBM | 4,334 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Kimi-K3 | HBM | rom | 327, 338, 340, 368, 389, 395, 396 |
| Kimi-K3 | HBM | sram | 327, 338, 340, 368, 389, 395, 396 |
| Kimi-K3 | SRAM | rom | 274, 299, 313, 314, 340, 377, 383, 395 |
| Kimi-K3 | SRAM | sram | 274, 299, 313, 314, 340, 377, 383, 395 |

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
| Kimi-K3 | `ROM-N5-native-SRAMKV-wafer-hybrid-x6` | 1 | 57 on `rom_wafer_express` | 5.24 | centre_mesh, one_shot | 301.06 | 59.95 | 130.49 | 53.51 | 2,099.9 |
| Kimi-K3 | `b200_sxm-x173-nvl72-hybrid` | 1 | 64 | 5.24 | measured_floor | 2,180.10 | 976.93 | 376.40 | 487.52 | 284.2 |
| Kimi-K3 | `b200_sxm-x173-nvl72-hybrid` | 64 | 64 | 5.24 | measured_floor | 2,180.10 | 1,441.30 | 1,741.96 | 677.09 | 188.6 |

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

- **279 of 3,331 feasible points (8.4%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 279.
- By area class: wafer (>=40,000 mm2) 279.
- By KV store: hbm 279.
- By batch: B=1 26, B=2 26, B=4 26, B=8 26, B=16 26, B=32 26, B=64 26, B=256 27, B=1024 31, B=4096 39.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 43% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 1,735 | 279 | 41.6% | 100.0% | 0.625 | 84% |
| rom | wafer (>=40,000 mm2) | 1,596 | 0 | 22.6% | 44.2% | 0.221 | 78% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `Kimi-K3/b200_sxm-x91-pipeline` | Kimi-K3 | 4096 | 145,600 | hbm | 1.203x | 91,000.0 / 91,000.0 W | 35% | 5.0 | 6.0 |
| `Kimi-K3/b200_sxm-x116-pipeline` | Kimi-K3 | 4096 | 185,600 | hbm | 1.191x | 116,000.0 / 116,000.0 W | 35% | 5.9 | 7.0 |
| `Kimi-K3/b200_sxm-x140-pipeline` | Kimi-K3 | 4096 | 224,000 | hbm | 1.182x | 140,000.0 / 140,000.0 W | 35% | 6.8 | 8.0 |
| `Kimi-K3/b200_sxm-x116-nvl72-hybrid` | Kimi-K3 | 4096 | 185,600 | hbm | 1.179x | 116,000.0 / 116,000.0 W | 35% | 17.1 | 20.1 |
| `Kimi-K3/b200_sxm-x152-pipeline` | Kimi-K3 | 4096 | 243,200 | hbm | 1.179x | 152,000.0 / 152,000.0 W | 35% | 7.2 | 8.5 |
| `Kimi-K3/b200_sxm-x159-pipeline` | Kimi-K3 | 4096 | 254,400 | hbm | 1.177x | 159,000.0 / 159,000.0 W | 35% | 7.4 | 8.7 |
| `Kimi-K3/b200_sxm-x160-pipeline` | Kimi-K3 | 4096 | 256,000 | hbm | 1.177x | 160,000.0 / 160,000.0 W | 35% | 7.4 | 8.8 |
| `Kimi-K3/b200_sxm-x161-pipeline` | Kimi-K3 | 4096 | 257,600 | hbm | 1.177x | 161,000.0 / 161,000.0 W | 35% | 7.5 | 8.8 |
| `Kimi-K3/b200_sxm-x162-pipeline` | Kimi-K3 | 4096 | 259,200 | hbm | 1.177x | 162,000.0 / 162,000.0 W | 35% | 7.5 | 8.8 |
| `Kimi-K3/b200_sxm-x167-pipeline` | Kimi-K3 | 4096 | 267,200 | hbm | 1.175x | 167,000.0 / 167,000.0 W | 35% | 7.7 | 9.0 |
| `Kimi-K3/b200_sxm-x172-pipeline` | Kimi-K3 | 4096 | 275,200 | hbm | 1.174x | 172,000.0 / 172,000.0 W | 35% | 7.8 | 9.2 |
| `Kimi-K3/b200_sxm-x173-pipeline` | Kimi-K3 | 4096 | 276,800 | hbm | 1.174x | 173,000.0 / 173,000.0 W | 35% | 7.9 | 9.3 |

The worst point's dynamic energy is weight read 73.7%, kv read 13.3%, arithmetic 12.9%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| Kimi-K3 | 1 | 323,575 | `Kimi-K3/ROM-N5-native-SRAMKV-wafer-hybrid-x7` | 11.597174 | 26,147.2 | layer_fixed_latency | `Kimi-K3/b200_sxm-x202-nvl72-hybrid` | 260.579961 | 83,903.4 | layer_fixed_latency | 22.47x |
| Kimi-K3 | 2 | 739,600 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16` | 20.316974 | 105,203.6 | layer_fixed_latency | `Kimi-K3/b200_sxm-x462-nvl72-hybrid` | 298.185223 | 192,247.5 | layer_fixed_latency | 14.68x |
| Kimi-K3 | 4 | 739,600 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16` | 10.396293 | 105,203.6 | layer_fixed_latency | `Kimi-K3/b200_sxm-x462-nvl72-hybrid` | 156.670602 | 192,247.5 | layer_fixed_latency | 15.07x |
| Kimi-K3 | 8 | 739,600 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16` | 5.435952 | 105,203.6 | layer_fixed_latency | `Kimi-K3/b200_sxm-x462-nvl72-hybrid` | 84.749248 | 193,100.3 | layer_fixed_latency | 15.59x |
| Kimi-K3 | 16 | 739,600 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16` | 2.955782 | 105,203.6 | layer_fixed_latency | `Kimi-K3/b200_sxm-x462-nvl72-hybrid` | 45.273358 | 199,611.8 | layer_fixed_latency | 15.32x |
| Kimi-K3 | 32 | 739,600 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16` | 2.039115 | 114,890.5 | layer_fixed_latency | `Kimi-K3/b200_sxm-x462-nvl72-hybrid` | 25.475157 | 211,159.9 | layer_fixed_latency | 12.49x |
| Kimi-K3 | 64 | 739,600 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1.498933 | 128,827.7 | kv_read | `Kimi-K3/b200_sxm-x462-nvl72-hybrid` | 15.461171 | 229,640.7 | layer_fixed_latency | 10.31x |
| Kimi-K3 | 256 | 739,600 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16` | 1.145380 | 150,084.1 | kv_read | `Kimi-K3/b200_sxm-x462-nvl72-hybrid` | 7.956176 | 309,921.3 | weight_read | 6.95x |
| Kimi-K3 | 1024 | 739,600 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16` | 1.069428 | 157,937.9 | kv_read | `Kimi-K3/b200_sxm-x462-nvl72-hybrid` | 4.524954 | 362,551.7 | weight_read | 4.23x |
| Kimi-K3 | 4096 | 739,600 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16` | 1.032489 | 156,081.9 | kv_read | `Kimi-K3/b200_sxm-x462-nvl72-hybrid` | 2.430105 | 365,084.4 | link_latency | 2.35x |

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
| Kimi-K3 | 200,000 | 2,800 B | 1,560.9 GB | 4.46 | 3.214 GB | 3.214 GB | 42.6 |

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
| Kimi-K3 | 6 | 277,350 | 2,689.1 | wafer-pipeline | 2,099.9 | wafer-hybrid | 1.28x | 401.4 | pipeline | 284.2 | hybrid | 1.41x | 6.70x | 7.39x | 1.10x |
| Kimi-K3 | 8 | 369,800 | 2,918.3 | wafer-pipeline | 2,251.0 | wafer-hybrid | 1.30x | 406.4 | pipeline | 283.8 | hybrid | 1.43x | 7.18x | 7.93x | 1.10x |
| Kimi-K3 | 12 | 554,700 | 2,918.3 | wafer-pipeline | 2,055.0 | wafer-hybrid | 1.42x | 411.4 | pipeline | 288.2 | hybrid | 1.43x | 7.09x | 7.13x | 1.01x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.01x to 1.10x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Kimi-K3 | 1 | fastest | Kimi-K3/ROM-N5-native-SRAMKV-wafer-hybrid-x7 | 323,575 | 2,254.6 | 2,254.6 | layer_fixed_latency | Kimi-K3/b200_sxm-x202-nvl72-hybrid | 323,200 | 1.00x | hybrid | 976.96 | 288.4 | 865.3 | layer_fixed_latency | 7.82x | 0.26x | 52.61x | 7.82x |
| Kimi-K3 | 1 | smallest silicon | Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x274 | 223,310 | 890.9 | 890.9 | layer_fixed_latency | Kimi-K3/b200_sxm-x140-nvl72-hybrid | 224,000 | 1.00x | hybrid | 971.20 | 289.9 | 579.8 | layer_fixed_latency | 3.07x | 0.15x | 20.79x | 3.07x |
| Kimi-K3 | 2 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 2,224.5 | 35,592.5 | layer_fixed_latency | Kimi-K3/b200_sxm-x462-nvl72-hybrid | 739,200 | 1.00x | hybrid | 999.98 | 286.0 | 2,002.1 | layer_fixed_latency | 7.78x | 1.80x | 51.90x | 7.78x |
| Kimi-K3 | 2 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x327 | 266,505 | 1,176.0 | 7,056.2 | layer_fixed_latency | Kimi-K3/b200_sxm-x167-nvl72-hybrid | 267,200 | 1.00x | hybrid | 976.93 | 283.1 | 849.4 | layer_fixed_latency | 4.15x | 0.99x | 27.44x | 4.15x |
| Kimi-K3 | 4 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 2,224.5 | 35,592.5 | layer_fixed_latency | Kimi-K3/b200_sxm-x462-nvl72-hybrid | 739,200 | 1.00x | hybrid | 999.98 | 286.0 | 2,002.1 | layer_fixed_latency | 7.78x | 1.80x | 51.90x | 7.78x |
| Kimi-K3 | 4 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x327 | 266,505 | 1,176.0 | 7,056.2 | layer_fixed_latency | Kimi-K3/b200_sxm-x167-nvl72-hybrid | 267,200 | 1.00x | hybrid | 984.54 | 280.5 | 1,121.8 | layer_fixed_latency | 4.19x | 0.99x | 27.44x | 4.19x |
| Kimi-K3 | 8 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 2,224.5 | 35,592.5 | layer_fixed_latency | Kimi-K3/b200_sxm-x462-nvl72-hybrid | 739,200 | 1.00x | hybrid | 1,005.38 | 284.8 | 2,278.5 | layer_fixed_latency | 7.81x | 1.80x | 51.90x | 7.81x |
| Kimi-K3 | 8 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x327 | 266,505 | 1,057.2 | 11,628.8 | compute | Kimi-K3/b200_sxm-x167-nvl72-hybrid | 267,200 | 1.00x | hybrid | 1,014.99 | 270.4 | 2,162.9 | layer_fixed_latency | 3.91x | 1.62x | 24.67x | 3.91x |
| Kimi-K3 | 16 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 2,224.5 | 35,592.5 | layer_fixed_latency | Kimi-K3/b200_sxm-x462-nvl72-hybrid | 739,200 | 1.00x | hybrid | 1,048.55 | 275.6 | 4,409.0 | layer_fixed_latency | 8.07x | 1.80x | 51.90x | 8.07x |
| Kimi-K3 | 16 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x327 | 266,505 | 838.1 | 13,410.4 | compute | Kimi-K3/b200_sxm-x167-nvl72-hybrid | 267,200 | 1.00x | hybrid | 1,075.89 | 252.6 | 4,041.4 | layer_fixed_latency | 3.32x | 1.87x | 19.56x | 3.32x |
| Kimi-K3 | 32 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 1,760.7 | 56,343.3 | layer_fixed_latency | Kimi-K3/b200_sxm-x462-nvl72-hybrid | 739,200 | 1.00x | hybrid | 1,134.89 | 259.0 | 8,288.9 | layer_fixed_latency | 6.80x | 2.85x | 41.08x | 6.80x |
| Kimi-K3 | 32 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x327 | 266,505 | 568.3 | 18,184.7 | compute | Kimi-K3/b200_sxm-x167-nvl72-hybrid | 267,200 | 1.00x | hybrid | 1,197.70 | 224.4 | 7,182.2 | layer_fixed_latency | 2.53x | 2.53x | 13.26x | 2.53x |
| Kimi-K3 | 64 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 1,342.9 | 85,946.3 | kv_read | Kimi-K3/b200_sxm-x462-nvl72-hybrid | 739,200 | 1.00x | hybrid | 1,307.58 | 232.1 | 14,852.7 | layer_fixed_latency | 5.79x | 4.34x | 31.33x | 5.79x |
| Kimi-K3 | 64 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x327 | 266,505 | 327.8 | 20,981.1 | compute | Kimi-K3/b200_sxm-x167-nvl72-hybrid | 267,200 | 1.00x | hybrid | 1,441.30 | 186.5 | 11,933.5 | layer_fixed_latency | 1.76x | 1.76x | 7.65x | 1.76x |
| Kimi-K3 | 256 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 511.9 | 131,034.4 | kv_read | Kimi-K3/b200_sxm-x462-nvl72-hybrid | 739,200 | 1.00x | hybrid | 1,701.05 | 152.2 | 38,953.6 | weight_read | 3.36x | 3.36x | 11.94x | 3.36x |
| Kimi-K3 | 256 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x327 | 266,505 | 91.4 | 23,390.9 | compute | Kimi-K3/b200_sxm-x167-nvl72-hybrid | 267,200 | 1.00x | hybrid | 2,902.94 | 107.9 | 27,618.5 | weight_read | 0.85x | 0.85x | 2.39x | 0.85x |
| Kimi-K3 | 1024 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 144.2 | 147,684.4 | kv_read | Kimi-K3/b200_sxm-x462-nvl72-hybrid | 739,200 | 1.00x | hybrid | 3,886.28 | 78.2 | 80,122.7 | weight_read | 1.84x | 1.84x | 4.29x | 1.84x |
| Kimi-K3 | 1024 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x327 | 266,505 | 23.3 | 23,847.4 | compute | Kimi-K3/b200_sxm-x167-nvl72-hybrid | 267,200 | 1.00x | hybrid | 4,919.74 | 54.0 | 55,336.6 | weight_read | 0.43x | 0.43x | 1.16x | 0.43x |
| Kimi-K3 | 4096 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 36.9 | 151,170.4 | kv_read | Kimi-K3/b200_sxm-x462-nvl72-hybrid | 739,200 | 1.00x | hybrid | 12,627.19 | 36.7 | 150,234.0 | link_latency | 1.01x | 1.01x | 2.32x | 1.01x |
| Kimi-K3 | 4096 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x327 | 266,505 | 5.8 | 23,845.4 | compute | Kimi-K3/b200_sxm-x167-nvl72-hybrid | 267,200 | 1.00x | hybrid | 9,811.85 | 22.1 | 90,690.9 | thermal | 0.26x | 0.26x | 0.76x | 0.26x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| Kimi-K3 | 29 | 46,400 | 963.09 | 454.98 | 258.9 | 298.1 |
| Kimi-K3 | 58 | 92,800 | 963.36 | 455.14 | 285.4 | 333.9 |
| Kimi-K3 | 66 | 105,600 | 963.39 | 455.15 | 289.0 | 338.8 |
| Kimi-K3 | 72 | 115,200 | 963.41 | 455.16 | 291.3 | 341.9 |
| Kimi-K3 | 73 | 116,800 | 971.17 | 457.48 | 268.6 | 311.6 |
| Kimi-K3 | 87 | 139,200 | 971.17 | 457.48 | 275.4 | 320.8 |
| Kimi-K3 | 91 | 145,600 | 971.17 | 457.48 | 277.0 | 323.0 |
| Kimi-K3 | 116 | 185,600 | 971.17 | 457.48 | 284.8 | 333.6 |
| Kimi-K3 | 140 | 224,000 | 971.20 | 457.48 | 289.9 | 340.6 |
| Kimi-K3 | 152 | 243,200 | 976.93 | 459.80 | 280.2 | 327.7 |
| Kimi-K3 | 159 | 254,400 | 976.93 | 459.80 | 281.6 | 329.6 |
| Kimi-K3 | 160 | 256,000 | 976.93 | 459.80 | 281.8 | 329.9 |
| Kimi-K3 | 161 | 257,600 | 976.93 | 459.80 | 282.0 | 330.2 |
| Kimi-K3 | 162 | 259,200 | 976.93 | 459.80 | 282.2 | 330.4 |
| Kimi-K3 | 167 | 267,200 | 976.93 | 459.80 | 283.1 | 331.7 |
| Kimi-K3 | 172 | 275,200 | 976.93 | 459.80 | 284.0 | 332.9 |
| Kimi-K3 | 173 | 276,800 | 976.93 | 459.80 | 284.2 | 333.1 |
| Kimi-K3 | 187 | 299,200 | 976.93 | 459.80 | 286.4 | 336.2 |
| Kimi-K3 | 192 | 307,200 | 976.93 | 459.80 | 287.1 | 337.2 |
| Kimi-K3 | 195 | 312,000 | 976.96 | 459.80 | 287.5 | 337.7 |
| Kimi-K3 | 198 | 316,800 | 976.96 | 459.80 | 287.9 | 338.3 |
| Kimi-K3 | 201 | 321,600 | 976.96 | 459.80 | 288.3 | 338.8 |
| Kimi-K3 | 202 | 323,200 | 976.96 | 459.80 | 288.4 | 339.0 |
| Kimi-K3 | 231 | 369,600 | 982.69 | 462.12 | 283.8 | 332.9 |
| Kimi-K3 | 347 | 555,200 | 988.47 | 464.43 | 288.2 | 339.5 |
| Kimi-K3 | 462 | 739,200 | 999.98 | 469.07 | 286.0 | 337.2 |

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
| Kimi-K3 | 29 | 46,400 | 42.9 | 258.9 | 165.6 | tensor | 963.09 | 24.9% | layer_fixed_latency |
| Kimi-K3 | 58 | 92,800 | 42.9 | 285.4 | 164.9 | tensor | 963.36 | 27.5% | layer_fixed_latency |
| Kimi-K3 | 66 | 105,600 | 42.9 | 289.0 | 165.7 | tensor | 963.39 | 27.8% | layer_fixed_latency |
| Kimi-K3 | 72 | 115,200 | 42.9 | 291.3 | 172.5 | tensor | 963.41 | 28.1% | layer_fixed_latency |
| Kimi-K3 | 73 | 116,800 | 42.9 | 170.8 | 268.6 | hybrid | 971.17 | 26.1% | layer_fixed_latency |
| Kimi-K3 | 87 | 139,200 | 42.9 | 172.1 | 275.4 | hybrid | 971.17 | 26.7% | layer_fixed_latency |
| Kimi-K3 | 91 | 145,600 | 42.9 | 172.4 | 277.0 | hybrid | 971.17 | 26.9% | layer_fixed_latency |
| Kimi-K3 | 116 | 185,600 | 42.9 | 173.9 | 284.8 | hybrid | 971.17 | 27.7% | layer_fixed_latency |
| Kimi-K3 | 140 | 224,000 | 42.9 | 174.9 | 289.9 | hybrid | 971.20 | 28.2% | layer_fixed_latency |
| Kimi-K3 | 152 | 243,200 | 42.9 | 173.8 | 280.2 | hybrid | 976.93 | 27.4% | layer_fixed_latency |
| Kimi-K3 | 159 | 254,400 | 42.9 | 174.0 | 281.6 | hybrid | 976.93 | 27.5% | layer_fixed_latency |
| Kimi-K3 | 160 | 256,000 | 42.9 | 174.0 | 281.8 | hybrid | 976.93 | 27.5% | layer_fixed_latency |
| Kimi-K3 | 161 | 257,600 | 42.9 | 174.0 | 282.0 | hybrid | 976.93 | 27.6% | layer_fixed_latency |
| Kimi-K3 | 162 | 259,200 | 42.9 | 174.1 | 282.2 | hybrid | 976.93 | 27.6% | layer_fixed_latency |
| Kimi-K3 | 167 | 267,200 | 42.9 | 174.2 | 283.1 | hybrid | 976.93 | 27.7% | layer_fixed_latency |
| Kimi-K3 | 172 | 275,200 | 42.9 | 174.3 | 284.0 | hybrid | 976.93 | 27.7% | layer_fixed_latency |
| Kimi-K3 | 173 | 276,800 | 42.9 | 174.3 | 284.2 | hybrid | 976.93 | 27.8% | layer_fixed_latency |
| Kimi-K3 | 187 | 299,200 | 42.9 | 174.6 | 286.4 | hybrid | 976.93 | 28.0% | layer_fixed_latency |
| Kimi-K3 | 192 | 307,200 | 42.9 | 174.7 | 287.1 | hybrid | 976.93 | 28.0% | layer_fixed_latency |
| Kimi-K3 | 195 | 312,000 | 42.9 | 174.7 | 287.5 | hybrid | 976.96 | 28.1% | layer_fixed_latency |
| Kimi-K3 | 198 | 316,800 | 42.9 | 174.8 | 287.9 | hybrid | 976.96 | 28.1% | layer_fixed_latency |
| Kimi-K3 | 201 | 321,600 | 42.9 | 174.8 | 288.3 | hybrid | 976.96 | 28.2% | layer_fixed_latency |
| Kimi-K3 | 202 | 323,200 | 42.9 | 174.8 | 288.4 | hybrid | 976.96 | 28.2% | layer_fixed_latency |
| Kimi-K3 | 231 | 369,600 | 42.9 | 174.5 | 283.8 | hybrid | 982.69 | 27.9% | layer_fixed_latency |
| Kimi-K3 | 347 | 555,200 | 42.9 | 175.0 | 288.2 | hybrid | 988.47 | 28.5% | layer_fixed_latency |
| Kimi-K3 | 462 | 739,200 | 42.9 | 175.0 | 286.0 | hybrid | 999.98 | 28.6% | layer_fixed_latency |

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
| Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x274 | Kimi-K3 | 274 | tensor | rom_package_ucie | rom_board_serdes | 372 | 336.96 us | 296.8 tok/s | 2,967.7 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 186 x all_reduce span 69 on rom_board_serdes (traversals 17.6) = 331.74 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x313 | Kimi-K3 | 313 | hybrid | rom_package_ucie | rom_board_serdes | 264 | 13.64 us | 7,330.8 tok/s | 73,307.7 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 78 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 8.42 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x395 | Kimi-K3 | 395 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x7 | Kimi-K3 | 7 | pipeline | on_wafer_n5 | rom_wafer_serdes | 92 | 11.48 us | 8,712.7 tok/s | 87,127.5 tok/s | 91 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 11.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x299 | Kimi-K3 | 299 | tensor | nvlink5 | infiniband_ndr | 372 | 1,365.12 us | 73.3 tok/s | 732.5 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 38 on infiniband_ndr (traversals 2.0) = 910.94 us |
| Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x6 | Kimi-K3 | 6 | tensor | on_wafer_n5 | rom_wafer_serdes | 372 | 441.00 us | 226.8 tok/s | 2,267.6 tok/s | 186 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 358.05 us; 186 x all_reduce span 6 on rom_wafer_serdes (traversals 4.4) = 82.95 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x383 | Kimi-K3 | 383 | hybrid | nvlink5 | infiniband_ndr | 233 | 563.06 us | 177.6 tok/s | 1,776.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 47 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 108.89 us |
| Kimi-K3/ROM-N5-native-SRAMKV-wafer-hybrid-x7 | Kimi-K3 | 7 | hybrid | on_wafer_n5 | rom_wafer_serdes | 192 | 358.66 us | 278.8 tok/s | 2,788.1 tok/s | 186 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 358.05 us; 6 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.61 us |
| Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x396 | Kimi-K3 | 396 | pipeline | rom_package_ucie | rom_board_serdes | 92 | 3.42 us | 29,235.7 tok/s | 292,356.8 tok/s | 69 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.94 us; 23 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.48 us |
| Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x327 | Kimi-K3 | 327 | tensor | rom_package_ucie | rom_board_serdes | 372 | 377.89 us | 264.6 tok/s | 2,646.3 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 186 x all_reduce span 82 on rom_board_serdes (traversals 19.8) = 372.67 us |
| Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x368 | Kimi-K3 | 368 | hybrid | rom_package_ucie | rom_board_serdes | 277 | 15.04 us | 6,646.9 tok/s | 66,468.7 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 91 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 9.82 us |
| Kimi-K3/ROM-N5-native-HBMKV-array-pipeline-x395 | Kimi-K3 | 395 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | Kimi-K3 | 16 | pipeline | on_wafer_n5 | rom_wafer_serdes | 92 | 11.48 us | 8,712.7 tok/s | 87,127.5 tok/s | 91 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 11.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| Kimi-K3/ROM-N5-native-HBMKV-array-tensor-x327 | Kimi-K3 | 327 | tensor | nvlink5 | infiniband_ndr | 372 | 1,365.42 us | 73.2 tok/s | 732.4 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 41 on infiniband_ndr (traversals 2.0) = 911.25 us |
| Kimi-K3/ROM-N5-native-HBMKV-wafer-tensor-x16 | Kimi-K3 | 16 | tensor | on_wafer_n5 | rom_wafer_serdes | 372 | 482.06 us | 207.4 tok/s | 2,074.4 tok/s | 186 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 358.05 us; 186 x all_reduce span 16 on rom_wafer_serdes (traversals 6.6) = 124.01 us |
| Kimi-K3/ROM-N5-native-HBMKV-array-hybrid-x389 | Kimi-K3 | 389 | hybrid | nvlink5 | infiniband_ndr | 234 | 565.38 us | 176.9 tok/s | 1,768.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 48 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 111.20 us |
| Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | Kimi-K3 | 16 | hybrid | on_wafer_n5 | rom_wafer_serdes | 201 | 359.59 us | 278.1 tok/s | 2,781.0 tok/s | 186 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 358.05 us; 15 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 1.54 us |
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
| Kimi-K3/b200_sxm-x66-pipeline | Kimi-K3 | 66 | pipeline | nvlink5 | infiniband_ndr | 65 | 87.84 us | 1,138.4 tok/s | 11,384.1 tok/s | 57 x point_to_point span 2 on nvlink5 (traversals 1.0) = 69.31 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.53 us |
| Kimi-K3/b200_sxm-x66-tensor | Kimi-K3 | 66 | tensor | nvlink5 | infiniband_ndr | 372 | 1,351.55 us | 74.0 tok/s | 739.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 897.37 us |
| Kimi-K3/b200_sxm-x66-hybrid | Kimi-K3 | 66 | hybrid | nvlink5 | infiniband_ndr | 194 | 472.71 us | 211.5 tok/s | 2,115.5 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.53 us |
| Kimi-K3/b200_sxm-x66-nvl72-tensor | Kimi-K3 | 66 | tensor | nvlink5_nvl72 | infiniband_ndr | 186 | 455.15 us | 219.7 tok/s | 2,197.1 tok/s | 186 x all_reduce span 66 on nvlink5_nvl72 (traversals 2.0) = 455.15 us |
| Kimi-K3/b200_sxm-x66-expert | Kimi-K3 | 66 | expert | nvlink5 | infiniband_ndr | 372 | 837.88 us | 119.3 tok/s | 1,193.5 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 447.37 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 390.51 us |
| Kimi-K3/b200_sxm-x66-nvl72-expert | Kimi-K3 | 66 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 679.07 us | 147.3 tok/s | 1,472.6 tok/s | 186 x all_reduce span 66 on nvlink5_nvl72 (traversals 2.0) = 455.15 us; 186 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 223.92 us |
| Kimi-K3/b200_sxm-x72-pipeline | Kimi-K3 | 72 | pipeline | nvlink5 | infiniband_ndr | 71 | 95.14 us | 1,051.1 tok/s | 10,511.1 tok/s | 63 x point_to_point span 2 on nvlink5 (traversals 1.0) = 76.60 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.53 us |
| Kimi-K3/b200_sxm-x72-tensor | Kimi-K3 | 72 | tensor | nvlink5 | infiniband_ndr | 372 | 1,351.55 us | 74.0 tok/s | 739.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 897.37 us |
| Kimi-K3/b200_sxm-x72-hybrid | Kimi-K3 | 72 | hybrid | nvlink5 | infiniband_ndr | 194 | 472.71 us | 211.5 tok/s | 2,115.5 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.53 us |
| Kimi-K3/b200_sxm-x72-nvl72-tensor | Kimi-K3 | 72 | tensor | nvlink5_nvl72 | infiniband_ndr | 186 | 455.16 us | 219.7 tok/s | 2,197.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us |
| Kimi-K3/b200_sxm-x72-expert | Kimi-K3 | 72 | expert | nvlink5 | infiniband_ndr | 372 | 836.70 us | 119.5 tok/s | 1,195.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 447.26 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 389.43 us |
| Kimi-K3/b200_sxm-x72-nvl72-expert | Kimi-K3 | 72 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 679.02 us | 147.3 tok/s | 1,472.7 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 223.86 us |
| Kimi-K3/b200_sxm-x73-pipeline | Kimi-K3 | 73 | pipeline | nvlink5 | infiniband_ndr | 72 | 97.45 us | 1,026.1 tok/s | 10,261.3 tok/s | 63 x point_to_point span 2 on nvlink5 (traversals 1.0) = 76.60 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| Kimi-K3/b200_sxm-x73-tensor | Kimi-K3 | 73 | tensor | nvlink5 | infiniband_ndr | 372 | 1,353.33 us | 73.9 tok/s | 738.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 899.15 us |
| Kimi-K3/b200_sxm-x73-hybrid | Kimi-K3 | 73 | hybrid | nvlink5 | infiniband_ndr | 195 | 475.03 us | 210.5 tok/s | 2,105.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| Kimi-K3/b200_sxm-x73-nvl72-tensor | Kimi-K3 | 73 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,290.32 us | 77.5 tok/s | 775.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 835.15 us |
| Kimi-K3/b200_sxm-x73-nvl72-hybrid | Kimi-K3 | 73 | hybrid | nvlink5_nvl72 | infiniband_ndr | 187 | 457.48 us | 218.6 tok/s | 2,185.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| Kimi-K3/b200_sxm-x73-expert | Kimi-K3 | 73 | expert | nvlink5 | infiniband_ndr | 372 | 836.53 us | 119.5 tok/s | 1,195.4 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 447.26 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 389.27 us |
| Kimi-K3/b200_sxm-x73-nvl72-expert | Kimi-K3 | 73 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 844.43 us | 118.4 tok/s | 1,184.2 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 389.27 us |
| Kimi-K3/b200_sxm-x87-pipeline | Kimi-K3 | 87 | pipeline | nvlink5 | infiniband_ndr | 86 | 115.58 us | 865.2 tok/s | 8,652.2 tok/s | 76 x point_to_point span 2 on nvlink5 (traversals 1.0) = 92.41 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| Kimi-K3/b200_sxm-x87-tensor | Kimi-K3 | 87 | tensor | nvlink5 | infiniband_ndr | 372 | 1,354.78 us | 73.8 tok/s | 738.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 900.61 us |
| Kimi-K3/b200_sxm-x87-hybrid | Kimi-K3 | 87 | hybrid | nvlink5 | infiniband_ndr | 196 | 477.34 us | 209.5 tok/s | 2,094.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| Kimi-K3/b200_sxm-x87-nvl72-tensor | Kimi-K3 | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,290.32 us | 77.5 tok/s | 775.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 835.15 us |
| Kimi-K3/b200_sxm-x87-nvl72-hybrid | Kimi-K3 | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 187 | 457.48 us | 218.6 tok/s | 2,185.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| Kimi-K3/b200_sxm-x87-expert | Kimi-K3 | 87 | expert | nvlink5 | infiniband_ndr | 372 | 834.57 us | 119.8 tok/s | 1,198.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 447.18 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 387.39 us |
| Kimi-K3/b200_sxm-x87-nvl72-expert | Kimi-K3 | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 842.55 us | 118.7 tok/s | 1,186.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 387.39 us |
| Kimi-K3/b200_sxm-x91-pipeline | Kimi-K3 | 91 | pipeline | nvlink5 | infiniband_ndr | 90 | 121.54 us | 822.8 tok/s | 8,227.6 tok/s | 79 x point_to_point span 2 on nvlink5 (traversals 1.0) = 96.06 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x91-tensor | Kimi-K3 | 91 | tensor | nvlink5 | infiniband_ndr | 372 | 1,355.99 us | 73.7 tok/s | 737.5 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 901.82 us |
| Kimi-K3/b200_sxm-x91-hybrid | Kimi-K3 | 91 | hybrid | nvlink5 | infiniband_ndr | 197 | 479.66 us | 208.5 tok/s | 2,084.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x91-nvl72-tensor | Kimi-K3 | 91 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,290.32 us | 77.5 tok/s | 775.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 835.15 us |
| Kimi-K3/b200_sxm-x91-nvl72-hybrid | Kimi-K3 | 91 | hybrid | nvlink5_nvl72 | infiniband_ndr | 187 | 457.48 us | 218.6 tok/s | 2,185.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| Kimi-K3/b200_sxm-x91-expert | Kimi-K3 | 91 | expert | nvlink5 | infiniband_ndr | 372 | 834.06 us | 119.9 tok/s | 1,198.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 447.11 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 386.96 us |
| Kimi-K3/b200_sxm-x91-nvl72-expert | Kimi-K3 | 91 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 842.12 us | 118.7 tok/s | 1,187.5 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 386.96 us |
| Kimi-K3/b200_sxm-x116-pipeline | Kimi-K3 | 116 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x116-tensor | Kimi-K3 | 116 | tensor | nvlink5 | infiniband_ndr | 372 | 1,358.66 us | 73.6 tok/s | 736.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 904.48 us |
| Kimi-K3/b200_sxm-x116-hybrid | Kimi-K3 | 116 | hybrid | nvlink5 | infiniband_ndr | 200 | 486.61 us | 205.5 tok/s | 2,055.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| Kimi-K3/b200_sxm-x116-nvl72-tensor | Kimi-K3 | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,290.32 us | 77.5 tok/s | 775.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 835.15 us |
| Kimi-K3/b200_sxm-x116-nvl72-hybrid | Kimi-K3 | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 187 | 457.48 us | 218.6 tok/s | 2,185.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| Kimi-K3/b200_sxm-x116-expert | Kimi-K3 | 116 | expert | nvlink5 | infiniband_ndr | 372 | 831.89 us | 120.2 tok/s | 1,202.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.96 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 384.94 us |
| Kimi-K3/b200_sxm-x116-nvl72-expert | Kimi-K3 | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 840.10 us | 119.0 tok/s | 1,190.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 384.94 us |
| Kimi-K3/b200_sxm-x140-pipeline | Kimi-K3 | 140 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x140-tensor | Kimi-K3 | 140 | tensor | nvlink5 | infiniband_ndr | 372 | 1,360.44 us | 73.5 tok/s | 735.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 18 on infiniband_ndr (traversals 2.0) = 906.26 us |
| Kimi-K3/b200_sxm-x140-hybrid | Kimi-K3 | 140 | hybrid | nvlink5 | infiniband_ndr | 203 | 493.56 us | 202.6 tok/s | 2,026.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 39.38 us |
| Kimi-K3/b200_sxm-x140-nvl72-tensor | Kimi-K3 | 140 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,290.32 us | 77.5 tok/s | 775.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 835.15 us |
| Kimi-K3/b200_sxm-x140-nvl72-hybrid | Kimi-K3 | 140 | hybrid | nvlink5_nvl72 | infiniband_ndr | 187 | 457.48 us | 218.6 tok/s | 2,185.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| Kimi-K3/b200_sxm-x140-expert | Kimi-K3 | 140 | expert | nvlink5 | infiniband_ndr | 372 | 830.53 us | 120.4 tok/s | 1,204.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.86 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 383.67 us |
| Kimi-K3/b200_sxm-x140-nvl72-expert | Kimi-K3 | 140 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 838.84 us | 119.2 tok/s | 1,192.1 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 383.67 us |
| Kimi-K3/b200_sxm-x152-pipeline | Kimi-K3 | 152 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x152-tensor | Kimi-K3 | 152 | tensor | nvlink5 | infiniband_ndr | 372 | 1,360.91 us | 73.5 tok/s | 734.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 906.73 us |
| Kimi-K3/b200_sxm-x152-hybrid | Kimi-K3 | 152 | hybrid | nvlink5 | infiniband_ndr | 204 | 495.88 us | 201.7 tok/s | 2,016.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| Kimi-K3/b200_sxm-x152-nvl72-tensor | Kimi-K3 | 152 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x152-nvl72-hybrid | Kimi-K3 | 152 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x152-expert | Kimi-K3 | 152 | expert | nvlink5 | infiniband_ndr | 372 | 830.00 us | 120.5 tok/s | 1,204.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.81 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 383.19 us |
| Kimi-K3/b200_sxm-x152-nvl72-expert | Kimi-K3 | 152 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 833.98 us | 119.9 tok/s | 1,199.1 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 383.19 us |
| Kimi-K3/b200_sxm-x159-pipeline | Kimi-K3 | 159 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x159-tensor | Kimi-K3 | 159 | tensor | nvlink5 | infiniband_ndr | 372 | 1,361.33 us | 73.5 tok/s | 734.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 907.15 us |
| Kimi-K3/b200_sxm-x159-hybrid | Kimi-K3 | 159 | hybrid | nvlink5 | infiniband_ndr | 205 | 498.19 us | 200.7 tok/s | 2,007.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 19 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 44.02 us |
| Kimi-K3/b200_sxm-x159-nvl72-tensor | Kimi-K3 | 159 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x159-nvl72-hybrid | Kimi-K3 | 159 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x159-expert | Kimi-K3 | 159 | expert | nvlink5 | infiniband_ndr | 372 | 829.76 us | 120.5 tok/s | 1,205.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.81 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.95 us |
| Kimi-K3/b200_sxm-x159-nvl72-expert | Kimi-K3 | 159 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 833.73 us | 119.9 tok/s | 1,199.4 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.95 us |
| Kimi-K3/b200_sxm-x160-pipeline | Kimi-K3 | 160 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x160-tensor | Kimi-K3 | 160 | tensor | nvlink5 | infiniband_ndr | 372 | 1,361.33 us | 73.5 tok/s | 734.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 907.15 us |
| Kimi-K3/b200_sxm-x160-hybrid | Kimi-K3 | 160 | hybrid | nvlink5 | infiniband_ndr | 205 | 498.19 us | 200.7 tok/s | 2,007.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 19 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 44.02 us |
| Kimi-K3/b200_sxm-x160-nvl72-tensor | Kimi-K3 | 160 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x160-nvl72-hybrid | Kimi-K3 | 160 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x160-expert | Kimi-K3 | 160 | expert | nvlink5 | infiniband_ndr | 372 | 829.70 us | 120.5 tok/s | 1,205.3 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.79 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.91 us |
| Kimi-K3/b200_sxm-x160-nvl72-expert | Kimi-K3 | 160 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 833.70 us | 119.9 tok/s | 1,199.5 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.91 us |
| Kimi-K3/b200_sxm-x161-pipeline | Kimi-K3 | 161 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x161-tensor | Kimi-K3 | 161 | tensor | nvlink5 | infiniband_ndr | 372 | 1,361.71 us | 73.4 tok/s | 734.4 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 21 on infiniband_ndr (traversals 2.0) = 907.53 us |
| Kimi-K3/b200_sxm-x161-hybrid | Kimi-K3 | 161 | hybrid | nvlink5 | infiniband_ndr | 206 | 500.51 us | 199.8 tok/s | 1,998.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 20 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.33 us |
| Kimi-K3/b200_sxm-x161-nvl72-tensor | Kimi-K3 | 161 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x161-nvl72-hybrid | Kimi-K3 | 161 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x161-expert | Kimi-K3 | 161 | expert | nvlink5 | infiniband_ndr | 372 | 829.67 us | 120.5 tok/s | 1,205.3 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.79 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.88 us |
| Kimi-K3/b200_sxm-x161-nvl72-expert | Kimi-K3 | 161 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 833.66 us | 120.0 tok/s | 1,199.5 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.88 us |
| Kimi-K3/b200_sxm-x162-pipeline | Kimi-K3 | 162 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x162-tensor | Kimi-K3 | 162 | tensor | nvlink5 | infiniband_ndr | 372 | 1,361.71 us | 73.4 tok/s | 734.4 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 21 on infiniband_ndr (traversals 2.0) = 907.53 us |
| Kimi-K3/b200_sxm-x162-hybrid | Kimi-K3 | 162 | hybrid | nvlink5 | infiniband_ndr | 206 | 500.51 us | 199.8 tok/s | 1,998.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 20 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.33 us |
| Kimi-K3/b200_sxm-x162-nvl72-tensor | Kimi-K3 | 162 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x162-nvl72-hybrid | Kimi-K3 | 162 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x162-expert | Kimi-K3 | 162 | expert | nvlink5 | infiniband_ndr | 372 | 829.64 us | 120.5 tok/s | 1,205.3 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.79 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.85 us |
| Kimi-K3/b200_sxm-x162-nvl72-expert | Kimi-K3 | 162 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 833.63 us | 120.0 tok/s | 1,199.6 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.85 us |
| Kimi-K3/b200_sxm-x167-pipeline | Kimi-K3 | 167 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x167-tensor | Kimi-K3 | 167 | tensor | nvlink5 | infiniband_ndr | 372 | 1,361.71 us | 73.4 tok/s | 734.4 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 21 on infiniband_ndr (traversals 2.0) = 907.53 us |
| Kimi-K3/b200_sxm-x167-hybrid | Kimi-K3 | 167 | hybrid | nvlink5 | infiniband_ndr | 206 | 500.51 us | 199.8 tok/s | 1,998.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 20 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.33 us |
| Kimi-K3/b200_sxm-x167-nvl72-tensor | Kimi-K3 | 167 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x167-nvl72-hybrid | Kimi-K3 | 167 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x167-expert | Kimi-K3 | 167 | expert | nvlink5 | infiniband_ndr | 372 | 829.48 us | 120.6 tok/s | 1,205.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.79 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.69 us |
| Kimi-K3/b200_sxm-x167-nvl72-expert | Kimi-K3 | 167 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 833.47 us | 120.0 tok/s | 1,199.8 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.69 us |
| Kimi-K3/b200_sxm-x172-pipeline | Kimi-K3 | 172 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x172-tensor | Kimi-K3 | 172 | tensor | nvlink5 | infiniband_ndr | 372 | 1,362.05 us | 73.4 tok/s | 734.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 907.88 us |
| Kimi-K3/b200_sxm-x172-hybrid | Kimi-K3 | 172 | hybrid | nvlink5 | infiniband_ndr | 207 | 502.83 us | 198.9 tok/s | 1,988.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| Kimi-K3/b200_sxm-x172-nvl72-tensor | Kimi-K3 | 172 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x172-nvl72-hybrid | Kimi-K3 | 172 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x172-expert | Kimi-K3 | 172 | expert | nvlink5 | infiniband_ndr | 372 | 829.31 us | 120.6 tok/s | 1,205.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.77 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.54 us |
| Kimi-K3/b200_sxm-x172-nvl72-expert | Kimi-K3 | 172 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 833.32 us | 120.0 tok/s | 1,200.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.54 us |
| Kimi-K3/b200_sxm-x173-pipeline | Kimi-K3 | 173 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x173-tensor | Kimi-K3 | 173 | tensor | nvlink5 | infiniband_ndr | 372 | 1,362.05 us | 73.4 tok/s | 734.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 907.88 us |
| Kimi-K3/b200_sxm-x173-hybrid | Kimi-K3 | 173 | hybrid | nvlink5 | infiniband_ndr | 207 | 502.83 us | 198.9 tok/s | 1,988.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| Kimi-K3/b200_sxm-x173-nvl72-tensor | Kimi-K3 | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x173-nvl72-hybrid | Kimi-K3 | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x173-expert | Kimi-K3 | 173 | expert | nvlink5 | infiniband_ndr | 372 | 829.28 us | 120.6 tok/s | 1,205.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.77 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.51 us |
| Kimi-K3/b200_sxm-x173-nvl72-expert | Kimi-K3 | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 833.29 us | 120.0 tok/s | 1,200.1 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.51 us |
| Kimi-K3/b200_sxm-x187-pipeline | Kimi-K3 | 187 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x187-tensor | Kimi-K3 | 187 | tensor | nvlink5 | infiniband_ndr | 372 | 1,362.66 us | 73.4 tok/s | 733.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 908.48 us |
| Kimi-K3/b200_sxm-x187-hybrid | Kimi-K3 | 187 | hybrid | nvlink5 | infiniband_ndr | 209 | 507.46 us | 197.1 tok/s | 1,970.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 53.28 us |
| Kimi-K3/b200_sxm-x187-nvl72-tensor | Kimi-K3 | 187 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x187-nvl72-hybrid | Kimi-K3 | 187 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x187-expert | Kimi-K3 | 187 | expert | nvlink5 | infiniband_ndr | 372 | 828.88 us | 120.6 tok/s | 1,206.4 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.74 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.14 us |
| Kimi-K3/b200_sxm-x187-nvl72-expert | Kimi-K3 | 187 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 832.93 us | 120.1 tok/s | 1,200.6 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.14 us |
| Kimi-K3/b200_sxm-x192-pipeline | Kimi-K3 | 192 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x192-tensor | Kimi-K3 | 192 | tensor | nvlink5 | infiniband_ndr | 372 | 1,362.66 us | 73.4 tok/s | 733.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 908.48 us |
| Kimi-K3/b200_sxm-x192-hybrid | Kimi-K3 | 192 | hybrid | nvlink5 | infiniband_ndr | 209 | 507.46 us | 197.1 tok/s | 1,970.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 53.28 us |
| Kimi-K3/b200_sxm-x192-nvl72-tensor | Kimi-K3 | 192 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x192-nvl72-hybrid | Kimi-K3 | 192 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x192-expert | Kimi-K3 | 192 | expert | nvlink5 | infiniband_ndr | 372 | 828.75 us | 120.7 tok/s | 1,206.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.72 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.02 us |
| Kimi-K3/b200_sxm-x192-nvl72-expert | Kimi-K3 | 192 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 832.81 us | 120.1 tok/s | 1,200.8 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.02 us |
| Kimi-K3/b200_sxm-x195-pipeline | Kimi-K3 | 195 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x195-tensor | Kimi-K3 | 195 | tensor | nvlink5 | infiniband_ndr | 372 | 1,362.93 us | 73.4 tok/s | 733.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 908.75 us |
| Kimi-K3/b200_sxm-x195-hybrid | Kimi-K3 | 195 | hybrid | nvlink5 | infiniband_ndr | 210 | 509.78 us | 196.2 tok/s | 1,961.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 55.60 us |
| Kimi-K3/b200_sxm-x195-nvl72-tensor | Kimi-K3 | 195 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x195-nvl72-hybrid | Kimi-K3 | 195 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x195-expert | Kimi-K3 | 195 | expert | nvlink5 | infiniband_ndr | 372 | 828.68 us | 120.7 tok/s | 1,206.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.72 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.96 us |
| Kimi-K3/b200_sxm-x195-nvl72-expert | Kimi-K3 | 195 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 832.74 us | 120.1 tok/s | 1,200.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.96 us |
| Kimi-K3/b200_sxm-x198-pipeline | Kimi-K3 | 198 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x198-tensor | Kimi-K3 | 198 | tensor | nvlink5 | infiniband_ndr | 372 | 1,362.93 us | 73.4 tok/s | 733.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 908.75 us |
| Kimi-K3/b200_sxm-x198-hybrid | Kimi-K3 | 198 | hybrid | nvlink5 | infiniband_ndr | 210 | 509.78 us | 196.2 tok/s | 1,961.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 55.60 us |
| Kimi-K3/b200_sxm-x198-nvl72-tensor | Kimi-K3 | 198 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x198-nvl72-hybrid | Kimi-K3 | 198 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x198-expert | Kimi-K3 | 198 | expert | nvlink5 | infiniband_ndr | 372 | 828.61 us | 120.7 tok/s | 1,206.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.72 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.89 us |
| Kimi-K3/b200_sxm-x198-nvl72-expert | Kimi-K3 | 198 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 832.67 us | 120.1 tok/s | 1,201.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.89 us |
| Kimi-K3/b200_sxm-x201-pipeline | Kimi-K3 | 201 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x201-tensor | Kimi-K3 | 201 | tensor | nvlink5 | infiniband_ndr | 372 | 1,363.17 us | 73.4 tok/s | 733.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 26 on infiniband_ndr (traversals 2.0) = 909.00 us |
| Kimi-K3/b200_sxm-x201-hybrid | Kimi-K3 | 201 | hybrid | nvlink5 | infiniband_ndr | 211 | 512.10 us | 195.3 tok/s | 1,952.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 25 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 57.92 us |
| Kimi-K3/b200_sxm-x201-nvl72-tensor | Kimi-K3 | 201 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x201-nvl72-hybrid | Kimi-K3 | 201 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x201-expert | Kimi-K3 | 201 | expert | nvlink5 | infiniband_ndr | 372 | 828.54 us | 120.7 tok/s | 1,206.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.71 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.83 us |
| Kimi-K3/b200_sxm-x201-nvl72-expert | Kimi-K3 | 201 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 832.61 us | 120.1 tok/s | 1,201.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.83 us |
| Kimi-K3/b200_sxm-x202-pipeline | Kimi-K3 | 202 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x202-tensor | Kimi-K3 | 202 | tensor | nvlink5 | infiniband_ndr | 372 | 1,363.17 us | 73.4 tok/s | 733.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 26 on infiniband_ndr (traversals 2.0) = 909.00 us |
| Kimi-K3/b200_sxm-x202-hybrid | Kimi-K3 | 202 | hybrid | nvlink5 | infiniband_ndr | 211 | 512.10 us | 195.3 tok/s | 1,952.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 25 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 57.92 us |
| Kimi-K3/b200_sxm-x202-nvl72-tensor | Kimi-K3 | 202 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x202-nvl72-hybrid | Kimi-K3 | 202 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x202-expert | Kimi-K3 | 202 | expert | nvlink5 | infiniband_ndr | 372 | 828.52 us | 120.7 tok/s | 1,207.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.71 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.80 us |
| Kimi-K3/b200_sxm-x202-nvl72-expert | Kimi-K3 | 202 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 832.59 us | 120.1 tok/s | 1,201.1 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.80 us |
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
| Kimi-K3/b200_sxm-x462-pipeline | Kimi-K3 | 462 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x462-tensor | Kimi-K3 | 462 | tensor | nvlink5 | infiniband_ndr | 372 | 1,366.57 us | 73.2 tok/s | 731.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 58 on infiniband_ndr (traversals 2.0) = 912.39 us |
| Kimi-K3/b200_sxm-x462-hybrid | Kimi-K3 | 462 | hybrid | nvlink5 | infiniband_ndr | 243 | 586.23 us | 170.6 tok/s | 1,705.8 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 57 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 132.05 us |
| Kimi-K3/b200_sxm-x462-nvl72-tensor | Kimi-K3 | 462 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,347.46 us | 74.2 tok/s | 742.1 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 892.29 us |
| Kimi-K3/b200_sxm-x462-nvl72-hybrid | Kimi-K3 | 462 | hybrid | nvlink5_nvl72 | infiniband_ndr | 192 | 469.07 us | 213.2 tok/s | 2,131.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.90 us |
| Kimi-K3/b200_sxm-x462-expert | Kimi-K3 | 462 | expert | nvlink5 | infiniband_ndr | 372 | 825.96 us | 121.1 tok/s | 1,210.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.54 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 379.43 us |
| Kimi-K3/b200_sxm-x462-nvl72-expert | Kimi-K3 | 462 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 827.29 us | 120.9 tok/s | 1,208.8 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 447.86 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 379.43 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Kimi-K3 | 1 | wafer | wafer | Kimi-K3/ROM-N5-native-SRAMKV-wafer-hybrid-x7 | 323,575 | 2,254.6 | 0.007 | 1,412.3 (307,255) | 2,254.6 (323,575) | 1.60x | layer_fixed_latency |
| Kimi-K3 | 2 | wafer | array | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 2,224.5 | 0.003 | 1,304.6 (299,920) | 2,224.5 (739,600) | 1.71x | layer_fixed_latency |
| Kimi-K3 | 4 | wafer | array | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 2,224.5 | 0.003 | 1,304.6 (299,920) | 2,224.5 (739,600) | 1.71x | layer_fixed_latency |
| Kimi-K3 | 8 | wafer | array | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 2,224.5 | 0.003 | 1,241.3 (299,920) | 2,224.5 (739,600) | 1.79x | layer_fixed_latency |
| Kimi-K3 | 16 | wafer | array | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 2,224.5 | 0.003 | 1,136.1 (317,035) | 2,224.5 (739,600) | 1.96x | layer_fixed_latency |
| Kimi-K3 | 32 | wafer | array | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 1,760.7 | 0.002 | 887.3 (317,035) | 1,760.7 (739,600) | 1.98x | layer_fixed_latency |
| Kimi-K3 | 64 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 1,342.9 | 0.002 | 558.4 (317,035) | 1,342.9 (739,600) | 2.40x | kv_read |
| Kimi-K3 | 256 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16 | 739,600 | 511.9 | 0.001 | 168.4 (317,035) | 511.9 (739,600) | 3.04x | kv_read |
| Kimi-K3 | 1024 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 144.2 | 0.000 | 43.7 (317,035) | 144.2 (739,600) | 3.30x | kv_read |
| Kimi-K3 | 4096 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 36.9 | 0.000 | 11.0 (317,035) | 36.9 (739,600) | 3.36x | kv_read |

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
| Kimi-K3 | 1 | sram | 147,099.7 | 26,113.2 | 26,113.2 | 5.63x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 2 | sram | 147,099.7 | 26,113.2 | 26,113.2 | 5.63x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 4 | sram | 147,099.7 | 26,113.2 | 26,113.2 | 5.63x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 8 | sram | 147,099.7 | 26,113.2 | 26,113.2 | 5.63x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 16 | sram | 147,099.7 | 26,113.2 | 26,113.2 | 5.63x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 32 | sram | 147,099.7 | 26,113.2 | 31,041.9 | 5.63x | 1.19x | kv_read | weight_read | weight_read |
| Kimi-K3 | 64 | sram | 147,099.7 | 26,113.2 | 48,575.7 | 5.63x | 1.86x | kv_read | weight_read | weight_read |
| Kimi-K3 | 256 | sram | 147,099.7 | 26,113.2 | 101,589.3 | 5.63x | 3.89x | kv_read | weight_read | weight_read |
| Kimi-K3 | 1024 | sram | 147,684.4 | 26,113.2 | 138,184.1 | 5.66x | 5.29x | kv_read | weight_read | weight_read |
| Kimi-K3 | 4096 | sram | 151,170.4 | 26,113.2 | 150,512.6 | 5.79x | 5.76x | kv_read | weight_read | kv_read |
| Kimi-K3 | 1 | rom | 146,307.4 | 147,426.1 | 147,426.1 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 2 | rom | 146,307.4 | 147,426.1 | 147,426.1 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 4 | rom | 146,307.4 | 147,426.1 | 147,426.1 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 8 | rom | 146,307.4 | 147,426.1 | 147,426.1 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 16 | rom | 146,307.4 | 147,426.1 | 147,426.1 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 32 | rom | 146,307.4 | 147,426.1 | 147,426.1 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 64 | rom | 146,307.4 | 147,426.1 | 147,426.1 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 256 | rom | 146,307.4 | 147,426.1 | 147,426.1 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 1024 | rom | 146,916.5 | 148,132.5 | 148,007.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 4096 | rom | 150,712.7 | 152,114.4 | 151,435.7 | 0.99x | 1.00x | kv_read | kv_read | kv_read |

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
| Kimi-K3 | 1 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 1.00 | 1.00 | 147,099.7 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 1 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-romfill | 739,600 | 2.09 | 1.00 | 146,307.4 | 0.198 | kv_read | 0.99x |
| Kimi-K3 | 1 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 1 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 1 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 1 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 2 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 1.00 | 1.00 | 147,099.7 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 2 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-romfill | 739,600 | 2.09 | 1.00 | 146,307.4 | 0.198 | kv_read | 0.99x |
| Kimi-K3 | 2 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 2 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 2 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 2 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 4 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 1.00 | 1.00 | 147,099.7 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 4 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-romfill | 739,600 | 2.09 | 1.00 | 146,307.4 | 0.198 | kv_read | 0.99x |
| Kimi-K3 | 4 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 4 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 4 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 4 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 8 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 1.00 | 1.00 | 147,099.7 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 8 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-romfill | 739,600 | 2.09 | 1.00 | 146,307.4 | 0.198 | kv_read | 0.99x |
| Kimi-K3 | 8 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 8 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 8 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 8 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 16 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 1.00 | 1.00 | 147,099.7 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 16 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-romfill | 739,600 | 2.09 | 1.00 | 146,307.4 | 0.198 | kv_read | 0.99x |
| Kimi-K3 | 16 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 16 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 16 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 16 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 32 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 1.00 | 1.00 | 147,099.7 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 32 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-romfill | 739,600 | 2.09 | 1.00 | 146,307.4 | 0.198 | kv_read | 0.99x |
| Kimi-K3 | 32 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 32 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 32 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16-perregion | 739,600 | 1.00 | 1.83 | 31,041.9 | 0.042 | weight_read | 0.21x |
| Kimi-K3 | 32 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 64 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 1.00 | 1.00 | 147,099.7 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 64 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-romfill | 739,600 | 2.09 | 1.00 | 146,307.4 | 0.198 | kv_read | 0.99x |
| Kimi-K3 | 64 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 64 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 64 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16-perregion | 739,600 | 1.00 | 2.24 | 48,575.7 | 0.066 | weight_read | 0.33x |
| Kimi-K3 | 64 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 256 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 1.00 | 1.00 | 147,099.7 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 256 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-romfill | 739,600 | 2.09 | 1.00 | 146,307.4 | 0.198 | kv_read | 0.99x |
| Kimi-K3 | 256 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream | 739,600 | 1.00 | 1.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 256 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 256 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16-perregion | 739,600 | 1.00 | 3.05 | 101,589.3 | 0.137 | weight_read | 0.69x |
| Kimi-K3 | 256 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion-romfill | 739,600 | 7.01 | 1.00 | 147,426.1 | 0.199 | kv_read | 1.00x |
| Kimi-K3 | 1024 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 1.00 | 1.00 | 147,684.4 | 0.200 | kv_read | 1.00x |
| Kimi-K3 | 1024 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-romfill | 739,600 | 2.09 | 1.00 | 146,916.5 | 0.199 | kv_read | 0.99x |
| Kimi-K3 | 1024 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16-perstream | 739,600 | 1.00 | 64.00 | 26,113.2 | 0.035 | weight_read | 0.18x |
| Kimi-K3 | 1024 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream-romfill | 739,600 | 7.01 | 1.13 | 148,132.5 | 0.200 | kv_read | 1.00x |
| Kimi-K3 | 1024 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16-perregion | 739,600 | 1.00 | 3.18 | 138,184.1 | 0.187 | weight_read | 0.94x |
| Kimi-K3 | 1024 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion-romfill | 739,600 | 7.01 | 1.03 | 148,007.2 | 0.200 | kv_read | 1.00x |
| Kimi-K3 | 4096 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16 | 739,600 | 1.00 | 1.00 | 151,170.4 | 0.204 | kv_read | 1.00x |
| Kimi-K3 | 4096 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-romfill | 739,600 | 2.09 | 1.00 | 150,712.7 | 0.204 | kv_read | 1.00x |
| Kimi-K3 | 4096 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16-perstream | 739,600 | 1.00 | 256.00 | 26,113.2 | 0.035 | weight_read | 0.17x |
| Kimi-K3 | 4096 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream-romfill | 739,600 | 7.01 | 4.51 | 152,114.4 | 0.206 | kv_read | 1.01x |
| Kimi-K3 | 4096 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x16-perregion | 739,600 | 1.00 | 4.32 | 150,512.6 | 0.204 | kv_read | 1.00x |
| Kimi-K3 | 4096 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x16-perregion-romfill | 739,600 | 7.01 | 1.91 | 151,435.7 | 0.205 | kv_read | 1.00x |

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
| Kimi-K3 | 1 | 130 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 2 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 4 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 8 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 16 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 32 | 142 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 64 | 142 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 256 | 142 | 1.80 | 1.007 | 1.200 | 1.19x |
| Kimi-K3 | 1024 | 142 | 7.21 | 1.057 | 2.173 | 2.06x |
| Kimi-K3 | 4096 | 142 | 28.85 | 1.271 | 3.906 | 3.07x |

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
| Kimi-K3 | 256 | 29 | 29.00 | 21.07 | 1.38x |
| Kimi-K3 | 1 | 58 | 14.09 | 8.11 | 1.74x |
| Kimi-K3 | 2 | 58 | 24.59 | 11.50 | 2.14x |
| Kimi-K3 | 4 | 58 | 38.37 | 15.54 | 2.47x |
| Kimi-K3 | 8 | 58 | 50.84 | 20.16 | 2.52x |
| Kimi-K3 | 16 | 58 | 56.83 | 24.95 | 2.28x |
| Kimi-K3 | 32 | 58 | 57.94 | 29.37 | 1.97x |
| Kimi-K3 | 64 | 58 | 58.00 | 32.85 | 1.77x |
| Kimi-K3 | 256 | 58 | 58.00 | 35.61 | 1.63x |
| Kimi-K3 | 1024 | 58 | 58.00 | 35.69 | 1.63x |
| Kimi-K3 | 1 | 66 | 14.30 | 8.38 | 1.71x |
| Kimi-K3 | 2 | 66 | 25.33 | 12.01 | 2.11x |
| Kimi-K3 | 4 | 66 | 40.51 | 16.38 | 2.47x |
| Kimi-K3 | 8 | 66 | 55.48 | 21.46 | 2.59x |
| Kimi-K3 | 16 | 66 | 63.85 | 26.82 | 2.38x |
| Kimi-K3 | 32 | 66 | 65.84 | 31.85 | 2.07x |
| Kimi-K3 | 64 | 66 | 65.99 | 35.84 | 1.84x |
| Kimi-K3 | 256 | 66 | 66.00 | 39.05 | 1.69x |
| Kimi-K3 | 1024 | 66 | 66.00 | 39.14 | 1.69x |
| Kimi-K3 | 1 | 72 | 14.44 | 8.57 | 1.68x |
| Kimi-K3 | 2 | 72 | 25.79 | 12.35 | 2.09x |
| Kimi-K3 | 4 | 72 | 41.88 | 16.95 | 2.47x |
| Kimi-K3 | 8 | 72 | 58.61 | 22.35 | 2.62x |
| Kimi-K3 | 16 | 72 | 68.88 | 28.13 | 2.45x |
| Kimi-K3 | 32 | 72 | 71.70 | 33.59 | 2.13x |
| Kimi-K3 | 64 | 72 | 71.99 | 37.96 | 1.90x |
| Kimi-K3 | 256 | 72 | 72.00 | 41.51 | 1.73x |
| Kimi-K3 | 1024 | 72 | 72.00 | 41.60 | 1.73x |
| Kimi-K3 | 1 | 73 | 14.46 | 8.60 | 1.68x |
| Kimi-K3 | 2 | 73 | 25.87 | 12.41 | 2.08x |
| Kimi-K3 | 4 | 73 | 42.09 | 17.04 | 2.47x |
| Kimi-K3 | 8 | 73 | 59.11 | 22.50 | 2.63x |
| Kimi-K3 | 16 | 73 | 69.70 | 28.33 | 2.46x |
| Kimi-K3 | 32 | 73 | 72.68 | 33.87 | 2.15x |
| Kimi-K3 | 64 | 73 | 72.98 | 38.31 | 1.91x |
| Kimi-K3 | 256 | 73 | 73.00 | 41.91 | 1.74x |
| Kimi-K3 | 1024 | 73 | 73.00 | 42.01 | 1.74x |
| Kimi-K3 | 1 | 87 | 14.69 | 8.99 | 1.63x |
| Kimi-K3 | 2 | 87 | 26.70 | 13.07 | 2.04x |
| Kimi-K3 | 4 | 87 | 44.67 | 18.18 | 2.46x |
| Kimi-K3 | 8 | 87 | 65.34 | 24.36 | 2.68x |
| Kimi-K3 | 16 | 87 | 80.50 | 31.08 | 2.59x |
| Kimi-K3 | 32 | 87 | 86.07 | 37.58 | 2.29x |
| Kimi-K3 | 64 | 87 | 86.93 | 42.89 | 2.03x |
| Kimi-K3 | 256 | 87 | 87.00 | 47.26 | 1.84x |
| Kimi-K3 | 1024 | 87 | 87.00 | 47.37 | 1.84x |
| Kimi-K3 | 1 | 91 | 14.75 | 9.09 | 1.62x |
| Kimi-K3 | 2 | 91 | 26.90 | 13.24 | 2.03x |
| Kimi-K3 | 4 | 91 | 45.29 | 18.47 | 2.45x |
| Kimi-K3 | 8 | 91 | 66.91 | 24.85 | 2.69x |
| Kimi-K3 | 16 | 91 | 83.38 | 31.80 | 2.62x |
| Kimi-K3 | 32 | 91 | 89.81 | 38.58 | 2.33x |
| Kimi-K3 | 64 | 91 | 90.90 | 44.13 | 2.06x |
| Kimi-K3 | 256 | 91 | 90.99 | 48.70 | 1.87x |
| Kimi-K3 | 1024 | 91 | 91.00 | 48.83 | 1.86x |
| Kimi-K3 | 4096 | 91 | 91.00 | 48.83 | 1.86x |
| Kimi-K3 | 1 | 116 | 15.01 | 9.67 | 1.55x |
| Kimi-K3 | 2 | 116 | 27.85 | 14.10 | 1.98x |
| Kimi-K3 | 4 | 116 | 48.36 | 20.08 | 2.41x |
| Kimi-K3 | 8 | 116 | 75.06 | 27.51 | 2.73x |
| Kimi-K3 | 16 | 116 | 99.38 | 35.87 | 2.77x |
| Kimi-K3 | 32 | 116 | 112.13 | 44.21 | 2.54x |
| Kimi-K3 | 64 | 116 | 115.43 | 51.21 | 2.25x |
| Kimi-K3 | 256 | 116 | 115.95 | 57.08 | 2.03x |
| Kimi-K3 | 1024 | 116 | 115.95 | 57.24 | 2.03x |
| Kimi-K3 | 4096 | 116 | 115.95 | 57.24 | 2.03x |
| Kimi-K3 | 1 | 140 | 15.17 | 10.13 | 1.50x |
| Kimi-K3 | 2 | 140 | 28.47 | 14.72 | 1.93x |
| Kimi-K3 | 4 | 140 | 50.43 | 21.38 | 2.36x |
| Kimi-K3 | 8 | 140 | 80.89 | 29.66 | 2.73x |
| Kimi-K3 | 16 | 140 | 111.98 | 39.17 | 2.86x |
| Kimi-K3 | 32 | 140 | 131.61 | 48.88 | 2.69x |
| Kimi-K3 | 64 | 140 | 138.27 | 57.17 | 2.42x |
| Kimi-K3 | 256 | 140 | 139.76 | 64.24 | 2.18x |
| Kimi-K3 | 1024 | 140 | 139.77 | 64.43 | 2.17x |
| Kimi-K3 | 4096 | 140 | 139.77 | 64.43 | 2.17x |
| Kimi-K3 | 1 | 152 | 15.23 | 10.34 | 1.47x |
| Kimi-K3 | 2 | 152 | 28.71 | 14.99 | 1.92x |
| Kimi-K3 | 4 | 152 | 51.25 | 21.98 | 2.33x |
| Kimi-K3 | 8 | 152 | 83.29 | 30.63 | 2.72x |
| Kimi-K3 | 16 | 152 | 117.44 | 40.65 | 2.89x |
| Kimi-K3 | 32 | 152 | 140.61 | 51.00 | 2.76x |
| Kimi-K3 | 64 | 152 | 149.35 | 59.91 | 2.49x |
| Kimi-K3 | 256 | 152 | 151.56 | 67.55 | 2.24x |
| Kimi-K3 | 1024 | 152 | 151.59 | 67.76 | 2.24x |
| Kimi-K3 | 4096 | 152 | 151.59 | 67.76 | 2.24x |
| Kimi-K3 | 1 | 159 | 15.27 | 10.45 | 1.46x |
| Kimi-K3 | 2 | 159 | 28.83 | 15.13 | 1.91x |
| Kimi-K3 | 4 | 159 | 51.68 | 22.31 | 2.32x |
| Kimi-K3 | 8 | 159 | 84.56 | 31.16 | 2.71x |
| Kimi-K3 | 16 | 159 | 120.41 | 41.47 | 2.90x |
| Kimi-K3 | 32 | 159 | 145.65 | 52.18 | 2.79x |
| Kimi-K3 | 64 | 159 | 155.68 | 61.44 | 2.53x |
| Kimi-K3 | 256 | 159 | 158.41 | 69.41 | 2.28x |
| Kimi-K3 | 1024 | 159 | 158.44 | 69.63 | 2.28x |
| Kimi-K3 | 4096 | 159 | 158.44 | 69.63 | 2.28x |
| Kimi-K3 | 1 | 160 | 15.27 | 10.47 | 1.46x |
| Kimi-K3 | 2 | 160 | 28.85 | 15.15 | 1.90x |
| Kimi-K3 | 4 | 160 | 51.74 | 22.35 | 2.31x |
| Kimi-K3 | 8 | 160 | 84.73 | 31.24 | 2.71x |
| Kimi-K3 | 16 | 160 | 120.82 | 41.58 | 2.91x |
| Kimi-K3 | 32 | 160 | 146.35 | 52.35 | 2.80x |
| Kimi-K3 | 64 | 160 | 156.58 | 61.66 | 2.54x |
| Kimi-K3 | 256 | 160 | 159.39 | 69.67 | 2.29x |
| Kimi-K3 | 1024 | 160 | 159.42 | 69.89 | 2.28x |
| Kimi-K3 | 4096 | 160 | 159.42 | 69.89 | 2.28x |
| Kimi-K3 | 1 | 161 | 15.28 | 10.48 | 1.46x |
| Kimi-K3 | 2 | 161 | 28.87 | 15.17 | 1.90x |
| Kimi-K3 | 4 | 161 | 51.80 | 22.40 | 2.31x |
| Kimi-K3 | 8 | 161 | 84.90 | 31.31 | 2.71x |
| Kimi-K3 | 16 | 161 | 121.23 | 41.70 | 2.91x |
| Kimi-K3 | 32 | 161 | 147.05 | 52.51 | 2.80x |
| Kimi-K3 | 64 | 161 | 157.47 | 61.87 | 2.55x |
| Kimi-K3 | 256 | 161 | 160.36 | 69.93 | 2.29x |
| Kimi-K3 | 1024 | 161 | 160.39 | 70.15 | 2.29x |
| Kimi-K3 | 4096 | 161 | 160.39 | 70.15 | 2.29x |
| Kimi-K3 | 1 | 162 | 15.28 | 10.50 | 1.46x |
| Kimi-K3 | 2 | 162 | 28.88 | 15.19 | 1.90x |
| Kimi-K3 | 4 | 162 | 51.85 | 22.44 | 2.31x |
| Kimi-K3 | 8 | 162 | 85.08 | 31.39 | 2.71x |
| Kimi-K3 | 16 | 162 | 121.63 | 41.81 | 2.91x |
| Kimi-K3 | 32 | 162 | 147.75 | 52.68 | 2.80x |
| Kimi-K3 | 64 | 162 | 158.36 | 62.08 | 2.55x |
| Kimi-K3 | 256 | 162 | 161.33 | 70.19 | 2.30x |
| Kimi-K3 | 1024 | 162 | 161.37 | 70.41 | 2.29x |
| Kimi-K3 | 4096 | 162 | 161.37 | 70.41 | 2.29x |
| Kimi-K3 | 1 | 167 | 15.30 | 10.58 | 1.45x |
| Kimi-K3 | 2 | 167 | 28.96 | 15.29 | 1.89x |
| Kimi-K3 | 4 | 167 | 52.13 | 22.67 | 2.30x |
| Kimi-K3 | 8 | 167 | 85.91 | 31.75 | 2.71x |
| Kimi-K3 | 16 | 167 | 123.61 | 42.38 | 2.92x |
| Kimi-K3 | 32 | 167 | 151.20 | 53.49 | 2.83x |
| Kimi-K3 | 64 | 167 | 162.80 | 63.14 | 2.58x |
| Kimi-K3 | 256 | 167 | 166.19 | 71.48 | 2.33x |
| Kimi-K3 | 1024 | 167 | 166.23 | 71.70 | 2.32x |
| Kimi-K3 | 4096 | 167 | 166.23 | 71.70 | 2.32x |
| Kimi-K3 | 1 | 172 | 15.32 | 10.65 | 1.44x |
| Kimi-K3 | 2 | 172 | 29.04 | 15.38 | 1.89x |
| Kimi-K3 | 4 | 172 | 52.40 | 22.89 | 2.29x |
| Kimi-K3 | 8 | 172 | 86.70 | 32.10 | 2.70x |
| Kimi-K3 | 16 | 172 | 125.52 | 42.93 | 2.92x |
| Kimi-K3 | 32 | 172 | 154.57 | 54.28 | 2.85x |
| Kimi-K3 | 64 | 172 | 167.18 | 64.17 | 2.61x |
| Kimi-K3 | 256 | 172 | 171.02 | 72.74 | 2.35x |
| Kimi-K3 | 1024 | 172 | 171.07 | 72.97 | 2.34x |
| Kimi-K3 | 4096 | 172 | 171.07 | 72.97 | 2.34x |
| Kimi-K3 | 1 | 173 | 15.32 | 10.66 | 1.44x |
| Kimi-K3 | 2 | 173 | 29.05 | 15.40 | 1.89x |
| Kimi-K3 | 4 | 173 | 52.45 | 22.93 | 2.29x |
| Kimi-K3 | 8 | 173 | 86.86 | 32.17 | 2.70x |
| Kimi-K3 | 16 | 173 | 125.90 | 43.04 | 2.93x |
| Kimi-K3 | 32 | 173 | 155.23 | 54.44 | 2.85x |
| Kimi-K3 | 64 | 173 | 168.05 | 64.38 | 2.61x |
| Kimi-K3 | 256 | 173 | 171.99 | 72.99 | 2.36x |
| Kimi-K3 | 1024 | 173 | 172.04 | 73.22 | 2.35x |
| Kimi-K3 | 4096 | 173 | 172.04 | 73.22 | 2.35x |
| Kimi-K3 | 1 | 187 | 15.37 | 10.86 | 1.42x |
| Kimi-K3 | 2 | 187 | 29.24 | 15.65 | 1.87x |
| Kimi-K3 | 4 | 187 | 53.11 | 23.51 | 2.26x |
| Kimi-K3 | 8 | 187 | 88.88 | 33.09 | 2.69x |
| Kimi-K3 | 16 | 187 | 130.86 | 44.51 | 2.94x |
| Kimi-K3 | 32 | 187 | 164.22 | 56.56 | 2.90x |
| Kimi-K3 | 64 | 187 | 180.02 | 67.15 | 2.68x |
| Kimi-K3 | 256 | 187 | 185.39 | 76.39 | 2.43x |
| Kimi-K3 | 1024 | 187 | 185.47 | 76.64 | 2.42x |
| Kimi-K3 | 4096 | 187 | 185.47 | 76.64 | 2.42x |
| Kimi-K3 | 1 | 192 | 15.39 | 10.93 | 1.41x |
| Kimi-K3 | 2 | 192 | 29.30 | 15.74 | 1.86x |
| Kimi-K3 | 4 | 192 | 53.32 | 23.70 | 2.25x |
| Kimi-K3 | 8 | 192 | 89.55 | 33.40 | 2.68x |
| Kimi-K3 | 16 | 192 | 132.52 | 45.01 | 2.94x |
| Kimi-K3 | 32 | 192 | 167.29 | 57.29 | 2.92x |
| Kimi-K3 | 64 | 192 | 184.19 | 68.11 | 2.70x |
| Kimi-K3 | 256 | 192 | 190.13 | 77.56 | 2.45x |
| Kimi-K3 | 1024 | 192 | 190.22 | 77.82 | 2.44x |
| Kimi-K3 | 4096 | 192 | 190.22 | 77.82 | 2.44x |
| Kimi-K3 | 1 | 195 | 15.40 | 10.97 | 1.40x |
| Kimi-K3 | 2 | 195 | 29.34 | 15.79 | 1.86x |
| Kimi-K3 | 4 | 195 | 53.45 | 23.82 | 2.24x |
| Kimi-K3 | 8 | 195 | 89.93 | 33.58 | 2.68x |
| Kimi-K3 | 16 | 195 | 133.49 | 45.31 | 2.95x |
| Kimi-K3 | 32 | 195 | 169.10 | 57.72 | 2.93x |
| Kimi-K3 | 64 | 195 | 186.67 | 68.68 | 2.72x |
| Kimi-K3 | 256 | 195 | 192.96 | 78.26 | 2.47x |
| Kimi-K3 | 1024 | 195 | 193.05 | 78.52 | 2.46x |
| Kimi-K3 | 4096 | 195 | 193.05 | 78.52 | 2.46x |
| Kimi-K3 | 1 | 198 | 15.41 | 11.01 | 1.40x |
| Kimi-K3 | 2 | 198 | 29.37 | 15.84 | 1.85x |
| Kimi-K3 | 4 | 198 | 53.57 | 23.93 | 2.24x |
| Kimi-K3 | 8 | 198 | 90.31 | 33.76 | 2.67x |
| Kimi-K3 | 16 | 198 | 134.44 | 45.60 | 2.95x |
| Kimi-K3 | 32 | 198 | 170.88 | 58.14 | 2.94x |
| Kimi-K3 | 64 | 198 | 189.12 | 69.24 | 2.73x |
| Kimi-K3 | 256 | 198 | 195.78 | 78.95 | 2.48x |
| Kimi-K3 | 1024 | 198 | 195.88 | 79.21 | 2.47x |
| Kimi-K3 | 4096 | 198 | 195.88 | 79.21 | 2.47x |
| Kimi-K3 | 1 | 201 | 15.42 | 11.05 | 1.40x |
| Kimi-K3 | 2 | 201 | 29.41 | 15.89 | 1.85x |
| Kimi-K3 | 4 | 201 | 53.69 | 24.04 | 2.23x |
| Kimi-K3 | 8 | 201 | 90.68 | 33.94 | 2.67x |
| Kimi-K3 | 16 | 201 | 135.37 | 45.89 | 2.95x |
| Kimi-K3 | 32 | 201 | 172.64 | 58.56 | 2.95x |
| Kimi-K3 | 64 | 201 | 191.56 | 69.79 | 2.74x |
| Kimi-K3 | 256 | 201 | 198.59 | 79.63 | 2.49x |
| Kimi-K3 | 1024 | 201 | 198.70 | 79.90 | 2.49x |
| Kimi-K3 | 4096 | 201 | 198.70 | 79.90 | 2.49x |
| Kimi-K3 | 1 | 202 | 15.42 | 11.06 | 1.39x |
| Kimi-K3 | 2 | 202 | 29.42 | 15.91 | 1.85x |
| Kimi-K3 | 4 | 202 | 53.73 | 24.08 | 2.23x |
| Kimi-K3 | 8 | 202 | 90.80 | 33.99 | 2.67x |
| Kimi-K3 | 16 | 202 | 135.68 | 45.98 | 2.95x |
| Kimi-K3 | 32 | 202 | 173.22 | 58.70 | 2.95x |
| Kimi-K3 | 64 | 202 | 192.37 | 69.98 | 2.75x |
| Kimi-K3 | 256 | 202 | 199.53 | 79.86 | 2.50x |
| Kimi-K3 | 1024 | 202 | 199.63 | 80.13 | 2.49x |
| Kimi-K3 | 4096 | 202 | 199.63 | 80.13 | 2.49x |
| Kimi-K3 | 1 | 231 | 15.49 | 11.40 | 1.36x |
| Kimi-K3 | 2 | 231 | 29.69 | 16.36 | 1.81x |
| Kimi-K3 | 4 | 231 | 54.71 | 25.06 | 2.18x |
| Kimi-K3 | 8 | 231 | 93.92 | 35.53 | 2.64x |
| Kimi-K3 | 16 | 231 | 143.75 | 48.55 | 2.96x |
| Kimi-K3 | 32 | 231 | 188.94 | 62.52 | 3.02x |
| Kimi-K3 | 64 | 231 | 214.85 | 75.04 | 2.86x |
| Kimi-K3 | 256 | 231 | 226.08 | 86.12 | 2.63x |
| Kimi-K3 | 1024 | 231 | 226.26 | 86.42 | 2.62x |
| Kimi-K3 | 4096 | 231 | 226.26 | 86.42 | 2.62x |
| Kimi-K3 | 1 | 347 | 15.66 | 12.40 | 1.26x |
| Kimi-K3 | 2 | 347 | 30.35 | 17.89 | 1.70x |
| Kimi-K3 | 4 | 347 | 57.11 | 27.69 | 2.06x |
| Kimi-K3 | 8 | 347 | 101.77 | 40.21 | 2.53x |
| Kimi-K3 | 16 | 347 | 165.42 | 56.60 | 2.92x |
| Kimi-K3 | 32 | 347 | 235.25 | 74.67 | 3.15x |
| Kimi-K3 | 64 | 347 | 287.88 | 91.49 | 3.15x |
| Kimi-K3 | 256 | 347 | 320.18 | 106.82 | 3.00x |
| Kimi-K3 | 1024 | 347 | 320.86 | 107.24 | 2.99x |
| Kimi-K3 | 4096 | 347 | 320.86 | 107.24 | 2.99x |
| Kimi-K3 | 1 | 462 | 15.74 | 13.04 | 1.21x |
| Kimi-K3 | 2 | 462 | 30.68 | 19.13 | 1.60x |
| Kimi-K3 | 4 | 462 | 58.35 | 29.20 | 2.00x |
| Kimi-K3 | 8 | 462 | 106.00 | 43.95 | 2.41x |
| Kimi-K3 | 16 | 462 | 177.91 | 62.70 | 2.84x |
| Kimi-K3 | 32 | 462 | 264.68 | 83.86 | 3.16x |
| Kimi-K3 | 64 | 462 | 339.65 | 104.02 | 3.27x |
| Kimi-K3 | 256 | 462 | 394.42 | 122.81 | 3.21x |
| Kimi-K3 | 1024 | 462 | 395.71 | 123.34 | 3.21x |
| Kimi-K3 | 4096 | 462 | 395.71 | 123.34 | 3.21x |

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
| gpu | Kimi-K3 | 1 | 2,180.10 | 63.5% |
| rom | Kimi-K3 | 1 | 283.91 | 67.8% |

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
| Kimi-K3 | 1 | 130 | 66.82% | 918.14 | 10.57 |
| Kimi-K3 | 2 | 3 | 3.74% | 67.68 | 10.57 |
| Kimi-K3 | 4 | 3 | 3.74% | 67.68 | 10.57 |
| Kimi-K3 | 8 | 3 | 3.74% | 67.68 | 10.57 |
| Kimi-K3 | 16 | 3 | 3.74% | 67.68 | 10.57 |

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
| Kimi-K3 | 1 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 72.5 | 23,717.2 |
| Kimi-K3 | 2 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 72.5 | 23,717.2 |
| Kimi-K3 | 4 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 72.5 | 23,717.2 |
| Kimi-K3 | 8 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 72.5 | 23,717.2 |
| Kimi-K3 | 16 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 72.5 | 23,717.2 |
| Kimi-K3 | 32 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 72.5 | 23,717.2 |
| Kimi-K3 | 64 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 72.5 | 23,717.2 |
| Kimi-K3 | 256 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 72.5 | 23,717.2 |
| Kimi-K3 | 1024 | 5.49% | 190.5 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 23.3 | 23,847.4 |
| Kimi-K3 | 4096 | 20.20% | 403.4 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 5.8 | 23,845.4 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 8 |
| gpu | infeasible | 45 |
| gpu | layer_fixed_latency | 192 |
| gpu | link_latency | 869 |
| gpu | thermal | 279 |
| gpu | weight_read | 387 |
| rom | compute | 456 |
| rom | infeasible | 1704 |
| rom | kv_read | 61 |
| rom | layer_fixed_latency | 426 |
| rom | link_latency | 462 |
| rom | weight_read | 191 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 45 |
| rom | CAPACITY | 1704 |

## Mechanical consistency audit

**FAIL** over 102,456 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x274', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x299', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x313', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x314', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x377', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x383', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x395', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x274', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x299', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x313', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x314', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x377', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x383', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x395', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x274', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x299', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x313', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x314', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x377', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x383', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x395', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x274', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x299', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x313', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x314', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x377', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x383', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x395', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x6', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x7', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x8', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x12', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x274', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x299', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x313', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x314', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x377', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x383', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x395', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x6', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x7', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x8', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x12', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x274', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x299', 'Kimi-K3', 1)

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

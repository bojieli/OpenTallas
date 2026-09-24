# Area-constrained roofline: n5_vs_b200-deepseek-v41-flash-engram-hbm-1m

> CANDIDATE MODEL under n5_vs_b200: DeepSeek-V4.1-Flash-engram-hbm at 1,000,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 205x (ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream, 284 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 108 devices. On the GPU side the correction reaches 31x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 55 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash-engram-hbm takes 63 x 815 mm2 (51,345 mm2, array, KV in HBM) at 13,087 tok/s per user and 255 tok/s per 1,000 mm2, holding 6,918 sessions, against 32 copies of one unified HBM die at the same silicon: 3.5x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash-engram-hbm on 91,280 mm2 of ROM silicon at 15,785 tok/s per user against 91,200 mm2 of b200_sxm-x57-nvl72-tensor at 4,154 tok/s: **3.8x**, ROM binding on `compute` and the GPU on `link_latency`. It holds 12,475 resident sessions against the GPU cluster's 9,772. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 9.22x to it.** At 114,100 mm2 on DeepSeek-V4.1-Flash-engram-hbm the pipeline-only GPU delivers 464.13 tok/s and the same silicon running tensor delivers 4,280 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `link_latency`) to 2.94x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash-engram-hbm engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 679 to 38,970 tok/s, and its rate with every slot occupied from 38,676 to 38,970. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 57 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 567 us over NVLink, capping per-user decode at 1,763 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 189.5 us and cap it at 5,276 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 0 of 10 operating points and an array 10; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 105 of 5515 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 88.9x of aggregate throughput (DeepSeek-V4.1-Flash-engram-hbm). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 25.47x, on DeepSeek-V4.1-Flash-engram-hbm at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 405 of 5,515 feasible points (7.3%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x39-perregion-romfill` at batch 4096 on 31,785 mm2, throttled 1.34x from 147 to 109 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 91% kv read against 0.1% weight read. The ROM sweep is not what melts it.


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

### DeepSeek-V4.1-Flash-engram-hbm at 1,000,000 tokens

**Recommended: `ROM-N5-native-HBMKV-array-hw-tensor-x63`** -- 63 x 815 mm2 reticle dies, 51,345 mm2 total, `tensor`-parallel, KV in HBM, spare silicon to `sram`.

- **13,087.0 tok/s per user** (0.08 ms/token), binding on `link_latency`
- **254.9 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 13,087 tok/s aggregate with every slot full, over 6,918 resident sessions (fill limited by `batch`)
- 4,644 W at 0.090 W/mm2, 354.8 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 32 copies of one unified HBM die -- `b200_sxm-x32-nvl72-tensor`, 51,200 mm2, area ratio 1.0028 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 51,345 | 51,200 | 1.0028 |
| user tok/s | 13,087.0 | 3,720.4 | 3.52x |
| aggregate tok/s | 13,087 | 3,720 | 0.88x |
| resident sessions | 6,918 | 5,235 | -- |
| J/token | 0.3548 | 4.4137 | 12.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 6,918 sessions against one that holds 5,235 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x71-nvl72-tensor` at 113,600 mm2 and 4,280.3 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 88,020 | 15,405.4 | 175.0 | 12,022 | 3.73x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-array-hw-hybrid-x112` | 91,280 | 15,785.1 | 172.9 | 12,475 | 3.80x |
| smallest feasible machine | `ROM-N5-native-HBMKV-array-hw-tensor-x57` | 46,455 | 10,888.2 | 234.4 | 6,237 | 3.00x |
| **after -- this report's rule** | `ROM-N5-native-HBMKV-array-hw-tensor-x63` | 51,345 | 13,087.0 | 254.9 | 6,918 | 3.52x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-HBMKV-array-hw-tensor-x63` | 51,345 | 13,087.0 | 254.9 | -- | 254.9 | ACCEPT |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x91-romfill` | 74,165 | 13,129.8 | 177.0 | 1.9 | 254.9 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 88,020 | 15,405.4 | 175.0 | 63.2 | 254.9 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x112` | 91,280 | 15,785.1 | 172.9 | 67.6 | 254.9 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-HBMKV-array-hw-tensor-x63` **<-- recommended** | 51,345 | 63 | 13,087.0 | 13,087 | 254.9 | 6,918 | `link_latency` | 4,644 | 354.8 | `b200_sxm-x32-nvl72-tensor` | 3.52x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x91-romfill` | 74,165 | 91 | 13,129.8 | 301,985 | 177.0 | 10,094 | `compute` | 17,905 | 635.7 | `b200_sxm-x46-nvl72-tensor` | 3.27x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 88,020 | 108 | 15,405.4 | 415,946 | 175.0 | 12,022 | `compute` | 23,923 | 692.5 | `b200_sxm-x55-nvl72-tensor` | 3.73x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x112` | 91,280 | 112 | 15,785.1 | 441,982 | 172.9 | 12,475 | `compute` | 25,313 | 710.1 | `b200_sxm-x57-nvl72-tensor` | 3.80x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 318 | densest | `ROM-N5-native-HBMKV-array-hw-tensor-x63` | 51,345 | 13,087.0 | 254.9 | 6,918 |
| array | 318 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x112` | 91,280 | 15,785.1 | 172.9 | 12,475 |
| array | 318 | smallest | `ROM-N5-native-HBMKV-array-hw-tensor-x57` | 46,455 | 10,888.2 | 234.4 | 6,237 |
| wafer | 57 | densest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 5,850.1 | 42.2 | 1 |
| wafer | 57 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,898.3 | 16.0 | 1 |
| wafer | 57 | smallest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 5,850.1 | 42.2 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x112` | 91,280 | 15,785.1 | 441,982 | 12,475 | 25,313 | 710.1 | `compute` | `b200_sxm-x57-nvl72-tensor` | 4,154.3 | 9,772 | 6,207.8 | 1.001 | 3.80x | 8.7x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,898.3 | 5,898 | 1 | 28,756 | 4,875.2 | `link_latency` | `b200_sxm-x231-nvl72-hybrid` | 4,049.2 | 41,348 | 21,391.5 | 1.001 | 1.46x | 4.4x |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x112` | 91,280 | 15,785.1 | 441,982 | 12,475 | 25,313 | 371.6 | `compute` | `b200_sxm-x57-nvl72-tensor` | 3,904.5 | 9,772 | 3,505.8 | 1.001 | 4.04x | 9.4x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 231,125 | 5,821.8 | 29,109 | 4,649 | 21,463 | 1,793.7 | `link_latency` | `b200_sxm-x144-nvl72-hybrid` | 4,246.9 | 25,560 | 7,340.7 | 1.003 | 1.37x | 4.1x |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x112` | 91,280 | 15,785.1 | 441,982 | 12,475 | 25,313 | 202.4 | `compute` | `b200_sxm-x57-nvl72-tensor` | 3,492.3 | 9,772 | 2,146.6 | 1.001 | 4.52x | 10.6x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x5-romfill` | 231,125 | 5,821.8 | 29,109 | 4,649 | 21,463 | 913.4 | `link_latency` | `b200_sxm-x144-nvl72-hybrid` | 4,025.3 | 25,560 | 4,082.0 | 1.003 | 1.45x | 4.5x |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x112` | 91,280 | 15,785.1 | 441,982 | 12,475 | 25,313 | 117.7 | `compute` | `b200_sxm-x57-nvl72-tensor` | 2,901.5 | 9,772 | 1,451.1 | 1.001 | 5.44x | 12.3x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,811.4 | 46,491 | 7,576 | 34,338 | 738.6 | `link_latency` | `b200_sxm-x231-nvl72-hybrid` | 3,804.9 | 41,348 | 3,607.4 | 1.001 | 1.53x | 4.9x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x112` | 91,280 | 15,785.1 | 441,982 | 12,475 | 25,313 | 75.4 | `compute` | `b200_sxm-x57-nvl72-tensor` | 2,206.4 | 9,772 | 1,073.8 | 1.001 | 7.15x | 14.2x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,716.7 | 91,468 | 11,477 | 52,165 | 570.3 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 3,653.2 | 62,398 | 2,855.9 | 0.999 | 1.56x | 5.0x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 92,095 | 14,386.2 | 460,360 | 12,589 | 25,939 | 56.3 | `compute` | `b200_sxm-x58-nvl72-tensor` | 1,571.2 | 9,953 | 837.1 | 0.992 | 9.16x | 14.9x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,414.3 | 173,256 | 11,477 | 54,643 | 315.4 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 3,156.7 | 62,398 | 1,827.9 | 0.999 | 1.72x | 5.8x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 13,034.9 | 1,107,963 | 38,335 | 66,328 | 68.6 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 1,886.2 | 30,822 | 979.6 | 1.001 | 6.91x | 14.3x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,896.1 | 313,351 | 11,477 | 58,881 | 187.9 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 2,509.1 | 62,398 | 1,289.6 | 0.999 | 1.95x | 6.9x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 5,005.8 | 1,281,486 | 38,335 | 69,781 | 54.5 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 890.5 | 30,822 | 568.8 | 1.001 | 5.62x | 9.6x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,110.2 | 796,219 | 11,477 | 101,943 | 128.0 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 1,260.5 | 62,398 | 751.9 | 0.999 | 2.47x | 5.8x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 185,005 | 1,593.3 | 1,631,531 | 25,519 | 75,528 | 46.3 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 353.9 | 20,479 | 202.6 | 0.997 | 4.50x | 3.8x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,565.5 | 1,603,035 | 11,477 | 100,819 | 62.9 | `kv_read` | `b200_sxm-x347-expert` | 627.6 | 61,997 | 249.2 | 0.999 | 2.49x | 4.0x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 566.8 | 2,321,735 | 38,335 | 110,693 | 47.7 | `weight_read` | `b200_sxm-x173-expert` | 197.1 | 30,631 | 112.1 | 1.001 | 2.88x | 2.4x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 398.3 | 1,631,630 | 11,477 | 99,511 | 61.0 | `kv_read` | `b200_sxm-x347-expert` | 335.3 | 61,997 | 125.6 | 0.999 | 1.19x | 2.1x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-2 | `ROM-N5-native-HBMKV-array-hw-tensor-x63` | 51,345 | array | HBM | 6,918 |
| 4-16 | `ROM-N5-native-HBMKV-array-hw-hybrid-x91-romfill` | 74,165 | array | HBM | 10,094 |
| 32-64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x113` | 92,095 | array | HBM | 12,589 |
| 256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 138,550 | array | HBM | 19,054 |
| 1024 | `ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 185,005 | array | HBM | 25,519 |
| 4096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x227` | 185,005 | array | HBM | 25,519 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | rom | 57, 60, 63, 68, 79, 81, 91, 108, 113, 162, 170, 216, 227, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | sram | 57, 60, 63, 68, 80, 81, 108, 112, 113, 162, 170, 216, 227, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | rom | 135, 140, 159, 160, 170, 192, 227, 256, 340, 365, 368, 370, 384 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | sram | 135, 140, 160, 170, 173, 184, 185, 192, 227, 256, 340, 384 |

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

- **405 of 5,515 feasible points (7.3%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 388, rom 17.
- By area class: large array (5,000-40,000 mm2) 31, wafer (>=40,000 mm2) 374.
- By KV store: hbm 405.
- By batch: B=1 39, B=2 39, B=4 39, B=8 39, B=16 39, B=32 39, B=64 39, B=256 39, B=1024 43, B=4096 50.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 45% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 108 | 18 | 69.5% | 100.0% | 0.625 | 50% |
| gpu | wafer (>=40,000 mm2) | 2,440 | 370 | 52.0% | 100.0% | 0.625 | 67% |
| rom | large array (5,000-40,000 mm2) | 480 | 13 | 25.1% | 100.0% | 0.500 | 71% |
| rom | wafer (>=40,000 mm2) | 2,487 | 4 | 27.0% | 100.0% | 0.500 | 73% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x39-perregion-romfill` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 31,785 | hbm | 1.343x | 15,892.5 / 15,892.5 W | 18% | 109.1 | 146.5 |
| `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x39-perregion` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 31,785 | hbm | 1.342x | 15,892.5 / 15,892.5 W | 18% | 109.2 | 146.5 |
| `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x40-perregion-romfill` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 32,600 | hbm | 1.342x | 16,300.0 / 16,300.0 W | 18% | 111.9 | 150.1 |
| `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x44-perregion-romfill` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 35,860 | hbm | 1.341x | 17,930.0 / 17,930.0 W | 18% | 123.1 | 165.1 |
| `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x59-perregion-romfill` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 48,085 | hbm | 1.340x | 24,042.5 / 24,042.5 W | 18% | 164.9 | 221.0 |
| `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x39-perregion-romfill` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 31,785 | hbm | 1.338x | 15,892.5 / 15,892.5 W | 18% | 108.7 | 145.4 |
| `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x40-perregion-romfill` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 32,600 | hbm | 1.323x | 16,300.0 / 16,300.0 W | 18% | 111.5 | 147.5 |
| `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-pipeline-x39-perregion-romfill` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 31,785 | hbm | 1.307x | 15,892.5 / 15,892.5 W | 18% | 108.7 | 142.1 |
| `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-pipeline-x40-perregion-romfill` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 32,600 | hbm | 1.292x | 16,300.0 / 16,300.0 W | 18% | 111.5 | 144.1 |
| `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x39-perregion-romfill` | DeepSeek-V4.1-Flash-engram-hbm | 1024 | 31,785 | hbm | 1.280x | 15,892.5 / 15,892.5 W | 18% | 434.8 | 556.5 |
| `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x40-perregion-romfill` | DeepSeek-V4.1-Flash-engram-hbm | 1024 | 32,600 | hbm | 1.279x | 16,300.0 / 16,300.0 W | 18% | 446.0 | 570.2 |
| `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x44-perregion-romfill` | DeepSeek-V4.1-Flash-engram-hbm | 4096 | 35,860 | hbm | 1.269x | 17,930.0 / 17,930.0 W | 18% | 122.6 | 155.6 |

The worst point's dynamic energy is kv read 91.5%, arithmetic 7.8%, operand delivery 0.6%, weight read 0.1%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 88,020 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 0.692500 | 23,922.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-nvl72-tensor` | 6.064298 | 25,056.9 | link_latency | 8.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 88,020 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 0.362796 | 23,922.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-nvl72-tensor` | 3.433111 | 26,625.7 | link_latency | 9.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 88,020 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 0.197944 | 23,922.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-nvl72-tensor` | 2.109275 | 29,192.6 | link_latency | 10.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 88,020 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 0.115518 | 23,922.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-nvl72-tensor` | 1.431463 | 32,808.8 | link_latency | 12.39x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 88,020 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x108` | 0.074305 | 23,922.9 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-nvl72-tensor` | 1.063007 | 36,912.6 | link_latency | 14.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 91,280 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x112` | 0.056255 | 25,588.5 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x57-nvl72-tensor` | 0.833977 | 41,534.6 | weight_read | 14.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 277,100 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.068650 | 66,328.1 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-hybrid` | 0.979617 | 118,258.0 | link_latency | 14.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 277,100 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.054453 | 69,780.6 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-hybrid` | 0.568788 | 129,658.6 | weight_read | 9.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 185,005 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 0.046293 | 75,528.3 | compute | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-nvl72-hybrid` | 0.202585 | 73,424.9 | link_latency | 3.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 277,100 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 0.047677 | 110,693.0 | weight_read | `DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-expert` | 0.112139 | 90,527.8 | link_latency | 2.35x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1,000,000 | 552 B | 307.5 GB | 4.46 | 0.183 GB | 0.893 GB | 71.3 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 3 | 138,675 | 58,295.6 | wafer-pipeline | 5,850.1 | wafer-hybrid | 9.96x | 11,538.8 | pipeline | 3,935.1 | hybrid | 2.93x | 5.05x | 1.49x | 0.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 184,900 | 60,834.7 | wafer-pipeline | 5,868.5 | wafer-hybrid | 10.37x | 12,398.8 | pipeline | 4,126.4 | hybrid | 3.00x | 4.91x | 1.42x | 0.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 6 | 277,350 | 63,361.1 | wafer-pipeline | 5,892.9 | wafer-hybrid | 10.75x | 13,384.9 | pipeline | 4,085.3 | hybrid | 3.28x | 4.73x | 1.44x | 0.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 369,800 | 64,417.8 | wafer-pipeline | 5,898.3 | wafer-hybrid | 10.92x | 13,951.9 | pipeline | 4,049.2 | hybrid | 3.45x | 4.62x | 1.46x | 0.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 12 | 554,700 | 65,365.2 | wafer-pipeline | 5,895.1 | wafer-hybrid | 11.09x | 14,567.2 | pipeline | 4,111.2 | hybrid | 3.54x | 4.49x | 1.43x | 0.32x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.29x to 0.32x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x112 | 91,280 | 15,785.1 | 441,982.2 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x57-nvl72-tensor | 91,200 | 1.00x | tensor | 194.68 | 4,154.3 | 4,154.3 | link_latency | 3.80x | 16.71x | 34.01x | 3.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x57 | 46,455 | 10,888.2 | 10,888.2 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 194.64 | 3,631.0 | 3,631.0 | link_latency | 3.00x | 0.81x | 23.46x | 3.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x112 | 91,280 | 15,785.1 | 441,982.2 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x57-nvl72-tensor | 91,200 | 1.00x | tensor | 197.37 | 3,904.5 | 7,809.1 | link_latency | 4.04x | 16.71x | 34.01x | 4.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x57 | 46,455 | 8,386.9 | 16,773.8 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 197.27 | 3,299.9 | 6,599.9 | link_latency | 2.54x | 1.25x | 18.07x | 2.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x112 | 91,280 | 15,785.1 | 441,982.2 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x57-nvl72-tensor | 91,200 | 1.00x | tensor | 202.73 | 3,492.3 | 13,969.1 | link_latency | 4.52x | 16.71x | 34.01x | 4.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x57 | 46,455 | 5,746.6 | 22,986.4 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 202.55 | 2,799.6 | 11,198.6 | link_latency | 2.05x | 1.71x | 12.38x | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x112 | 91,280 | 15,785.1 | 441,982.2 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x57-nvl72-tensor | 91,200 | 1.00x | tensor | 213.46 | 2,901.5 | 23,211.8 | link_latency | 5.44x | 16.71x | 34.01x | 5.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x57 | 46,455 | 3,526.3 | 28,210.7 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 213.09 | 2,168.1 | 17,344.4 | link_latency | 1.63x | 1.63x | 7.60x | 1.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x112 | 91,280 | 15,785.1 | 441,982.2 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x57-nvl72-tensor | 91,200 | 1.00x | tensor | 234.92 | 2,206.4 | 35,302.7 | link_latency | 7.15x | 12.52x | 34.01x | 7.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x57 | 46,455 | 2,357.8 | 37,724.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 234.18 | 1,530.1 | 24,481.7 | weight_read | 1.54x | 1.54x | 5.08x | 1.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x113 | 92,095 | 14,386.2 | 460,359.6 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-nvl72-tensor | 92,800 | 0.99x | tensor | 277.87 | 1,571.2 | 50,279.4 | weight_read | 9.16x | 9.16x | 31.00x | 9.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x57 | 46,455 | 1,197.3 | 38,314.4 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 276.37 | 1,016.8 | 32,538.4 | weight_read | 1.18x | 1.18x | 2.67x | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 13,034.9 | 1,107,963.4 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 262.24 | 1,886.2 | 120,718.6 | link_latency | 6.91x | 9.18x | 28.08x | 6.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x57 | 46,455 | 604.8 | 38,708.7 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 360.74 | 676.3 | 43,281.5 | weight_read | 0.89x | 0.89x | 1.86x | 0.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 5,005.8 | 1,281,485.7 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 460.79 | 890.5 | 227,956.2 | weight_read | 5.62x | 5.62x | 12.63x | 5.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x57 | 46,455 | 152.0 | 38,907.2 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 866.95 | 359.9 | 92,130.2 | weight_read | 0.42x | 0.42x | 1.19x | 0.42x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 1,593.3 | 1,631,531.3 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-nvl72-hybrid | 185,600 | 1.00x | hybrid | 1,677.57 | 353.9 | 362,439.5 | link_latency | 4.50x | 4.50x | 12.50x | 4.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x57 | 46,455 | 38.0 | 38,957.2 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | 46,400 | 1.00x | tensor | 2,891.78 | 170.3 | 174,403.3 | link_latency | 0.22x | 0.22x | 0.87x | 0.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 566.8 | 2,321,735.4 | weight_read | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-expert | 276,800 | 1.00x | expert | 3,147.91 | 197.1 | 807,280.7 | link_latency | 2.88x | 2.88x | 9.63x | 2.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x57 | 46,455 | 9.5 | 38,969.7 | compute | DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 3,273.91 | 66.0 | 270,141.6 | weight_read | 0.14x | 0.14x | 0.47x | 0.14x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | 20 | 32,000 | 194.59 | 194.59 | 3,255.3 | 3,255.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 22 | 35,200 | 194.61 | 194.61 | 3,357.1 | 3,357.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 26 | 41,600 | 194.63 | 194.63 | 3,526.6 | 3,526.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 29 | 46,400 | 194.64 | 194.64 | 3,631.0 | 3,631.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 30 | 48,000 | 194.64 | 194.64 | 3,662.3 | 3,662.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 31 | 49,600 | 194.64 | 194.64 | 3,692.1 | 3,692.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 51,200 | 194.65 | 194.65 | 3,720.4 | 3,720.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 35 | 56,000 | 194.65 | 194.65 | 3,797.9 | 3,797.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 40 | 64,000 | 194.66 | 194.66 | 3,906.5 | 3,906.5 |
| DeepSeek-V4.1-Flash-engram-hbm | 41 | 65,600 | 194.66 | 194.66 | 3,925.6 | 3,925.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 46 | 73,600 | 194.67 | 194.67 | 4,011.1 | 4,011.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 55 | 88,000 | 194.68 | 194.68 | 4,131.9 | 4,131.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 57 | 91,200 | 194.68 | 194.68 | 4,154.3 | 4,154.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 58 | 92,800 | 194.68 | 194.68 | 4,165.0 | 4,165.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 65 | 104,000 | 194.69 | 194.69 | 4,232.0 | 4,232.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 69 | 110,400 | 194.69 | 194.69 | 4,265.0 | 4,265.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 71 | 113,600 | 194.69 | 194.69 | 4,280.3 | 4,280.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 81 | 129,600 | 196.93 | 196.93 | 3,881.7 | 3,881.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 82 | 131,200 | 196.93 | 196.93 | 3,891.0 | 3,891.0 |
| DeepSeek-V4.1-Flash-engram-hbm | 83 | 132,800 | 196.93 | 196.93 | 3,900.2 | 3,900.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 87 | 139,200 | 196.93 | 196.93 | 3,935.1 | 3,935.1 |
| DeepSeek-V4.1-Flash-engram-hbm | 88 | 140,800 | 196.93 | 196.93 | 3,943.4 | 3,943.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 94 | 150,400 | 196.93 | 196.93 | 3,990.2 | 3,990.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 98 | 156,800 | 196.93 | 196.93 | 4,018.7 | 4,018.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 110 | 176,000 | 196.93 | 196.93 | 4,093.9 | 4,093.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 116 | 185,600 | 196.93 | 196.93 | 4,126.4 | 4,126.4 |
| DeepSeek-V4.1-Flash-engram-hbm | 126 | 201,600 | 196.93 | 196.93 | 4,174.8 | 4,174.8 |
| DeepSeek-V4.1-Flash-engram-hbm | 130 | 208,000 | 196.93 | 196.93 | 4,192.3 | 4,192.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 144 | 230,400 | 196.93 | 196.93 | 4,246.9 | 4,246.9 |
| DeepSeek-V4.1-Flash-engram-hbm | 173 | 276,800 | 199.16 | 199.16 | 4,085.3 | 4,085.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 186 | 297,600 | 199.16 | 199.16 | 4,127.2 | 4,127.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 187 | 299,200 | 199.16 | 199.16 | 4,130.3 | 4,130.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 188 | 300,800 | 199.16 | 199.16 | 4,133.2 | 4,133.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 193 | 308,800 | 199.16 | 199.16 | 4,147.8 | 4,147.8 |
| DeepSeek-V4.1-Flash-engram-hbm | 194 | 310,400 | 199.16 | 199.16 | 4,150.6 | 4,150.6 |
| DeepSeek-V4.1-Flash-engram-hbm | 196 | 313,600 | 199.16 | 199.16 | 4,156.2 | 4,156.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 231 | 369,600 | 201.40 | 201.40 | 4,049.2 | 4,049.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 318 | 508,800 | 203.63 | 203.63 | 4,066.2 | 4,066.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 347 | 555,200 | 203.63 | 203.63 | 4,111.2 | 4,111.2 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 20 | 32,000 | 464.1 | 3,255.3 | 1,935.9 | tensor | 194.59 | 63.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 22 | 35,200 | 464.1 | 3,357.1 | 2,046.8 | tensor | 194.61 | 65.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 26 | 41,600 | 464.1 | 3,526.6 | 1,898.7 | tensor | 194.63 | 68.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 29 | 46,400 | 464.1 | 3,631.0 | 2,024.2 | tensor | 194.64 | 70.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 30 | 48,000 | 464.1 | 3,662.3 | 2,063.6 | tensor | 194.64 | 71.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 31 | 49,600 | 464.1 | 3,692.1 | 2,101.8 | tensor | 194.64 | 71.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 51,200 | 464.1 | 3,720.4 | 2,139.0 | tensor | 194.65 | 72.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 35 | 56,000 | 464.1 | 3,797.9 | 1,974.9 | tensor | 194.65 | 73.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 40 | 64,000 | 464.1 | 3,906.5 | 2,128.8 | tensor | 194.66 | 76.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 41 | 65,600 | 464.1 | 3,925.6 | 1,938.9 | tensor | 194.66 | 76.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 46 | 73,600 | 464.1 | 4,011.1 | 2,069.9 | tensor | 194.67 | 78.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 55 | 88,000 | 464.1 | 4,131.9 | 2,088.2 | tensor | 194.68 | 80.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 57 | 91,200 | 464.1 | 4,154.3 | 1,968.8 | tensor | 194.68 | 80.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 58 | 92,800 | 464.1 | 4,165.0 | 1,988.2 | tensor | 194.68 | 81.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 65 | 104,000 | 464.1 | 4,232.0 | 1,975.2 | tensor | 194.69 | 82.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 69 | 110,400 | 464.1 | 4,265.0 | 2,041.5 | tensor | 194.69 | 83.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 71 | 113,600 | 464.1 | 4,280.3 | 2,073.4 | tensor | 194.69 | 83.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 81 | 129,600 | 464.1 | 1,725.8 | 3,881.7 | hybrid | 196.93 | 76.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 82 | 131,200 | 464.1 | 1,726.7 | 3,891.0 | hybrid | 196.93 | 76.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 83 | 132,800 | 464.1 | 1,727.6 | 3,900.2 | hybrid | 196.93 | 76.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 87 | 139,200 | 464.1 | 1,731.0 | 3,935.1 | hybrid | 196.93 | 77.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 88 | 140,800 | 464.1 | 1,731.8 | 3,943.4 | hybrid | 196.93 | 77.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 94 | 150,400 | 464.1 | 1,736.3 | 3,990.2 | hybrid | 196.93 | 78.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 98 | 156,800 | 464.1 | 1,739.0 | 4,018.7 | hybrid | 196.93 | 79.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 110 | 176,000 | 464.1 | 1,745.9 | 4,093.9 | hybrid | 196.93 | 80.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 116 | 185,600 | 464.1 | 1,748.9 | 4,126.4 | hybrid | 196.93 | 81.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 126 | 201,600 | 464.1 | 1,753.2 | 4,174.8 | hybrid | 196.93 | 82.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 130 | 208,000 | 464.1 | 1,754.7 | 4,192.3 | hybrid | 196.93 | 82.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 144 | 230,400 | 464.1 | 1,759.4 | 4,246.9 | hybrid | 196.93 | 83.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 173 | 276,800 | 464.1 | 1,741.7 | 4,085.3 | hybrid | 199.16 | 81.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 186 | 297,600 | 464.1 | 1,744.2 | 4,127.2 | hybrid | 199.16 | 82.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 187 | 299,200 | 464.1 | 1,744.3 | 4,130.3 | hybrid | 199.16 | 82.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 188 | 300,800 | 464.1 | 1,744.5 | 4,133.2 | hybrid | 199.16 | 82.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 193 | 308,800 | 464.1 | 1,745.4 | 4,147.8 | hybrid | 199.16 | 82.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 194 | 310,400 | 464.1 | 1,745.6 | 4,150.6 | hybrid | 199.16 | 82.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 196 | 313,600 | 464.1 | 1,745.9 | 4,156.2 | hybrid | 199.16 | 82.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 231 | 369,600 | 464.1 | 1,738.3 | 4,049.2 | hybrid | 201.40 | 81.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 318 | 508,800 | 464.1 | 1,738.2 | 4,066.2 | hybrid | 203.63 | 82.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 347 | 555,200 | 464.1 | 1,739.8 | 4,111.2 | hybrid | 203.63 | 83.7% | link_latency |

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
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x185 | DeepSeek-V4.1-Flash-engram-hbm | 185 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x140 | DeepSeek-V4.1-Flash-engram-hbm | 140 | tensor | rom_package_ucie | rom_board_serdes | 160 | 91.39 us | 1,094.2 tok/s | 10,942.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 35 on rom_board_serdes (traversals 11.0) = 89.33 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x184 | DeepSeek-V4.1-Flash-engram-hbm | 184 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 6.18 us | 16,174.3 tok/s | 161,742.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x184 | DeepSeek-V4.1-Flash-engram-hbm | 184 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-pipeline-x4 | DeepSeek-V4.1-Flash-engram-hbm | 4 | pipeline | on_wafer_n5 | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-tensor-x135 | DeepSeek-V4.1-Flash-engram-hbm | 135 | tensor | nvlink5 | infiniband_ndr | 160 | 565.45 us | 176.9 tok/s | 1,768.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 371.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-tensor-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | tensor | on_wafer_n5 | rom_wafer_serdes | 160 | 171.87 us | 581.8 tok/s | 5,818.2 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 80 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 17.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hybrid-x173 | DeepSeek-V4.1-Flash-engram-hbm | 173 | hybrid | nvlink5 | infiniband_ndr | 101 | 241.32 us | 414.4 tok/s | 4,143.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-hybrid-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | hybrid | on_wafer_n5 | rom_wafer_serdes | 82 | 154.20 us | 648.5 tok/s | 6,484.9 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.20 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x113 | DeepSeek-V4.1-Flash-engram-hbm | 113 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x63 | DeepSeek-V4.1-Flash-engram-hbm | 63 | tensor | rom_package_ucie | rom_board_serdes | 160 | 56.14 us | 1,781.2 tok/s | 17,812.4 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 16 on rom_board_serdes (traversals 6.6) = 54.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x112 | DeepSeek-V4.1-Flash-engram-hbm | 112 | hybrid | rom_package_ucie | rom_board_serdes | 107 | 4.91 us | 20,348.4 tok/s | 203,483.6 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 27 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.85 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-pipeline-x113 | DeepSeek-V4.1-Flash-engram-hbm | 113 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5 | DeepSeek-V4.1-Flash-engram-hbm | 5 | pipeline | on_wafer_n5 | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-tensor-x60 | DeepSeek-V4.1-Flash-engram-hbm | 60 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x5 | DeepSeek-V4.1-Flash-engram-hbm | 5 | tensor | on_wafer_n5 | rom_wafer_serdes | 160 | 189.53 us | 527.6 tok/s | 5,276.3 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 80 x all_reduce span 5 on rom_wafer_serdes (traversals 4.4) = 35.53 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hybrid-x80 | DeepSeek-V4.1-Flash-engram-hbm | 80 | hybrid | nvlink5 | infiniband_ndr | 89 | 214.50 us | 466.2 tok/s | 4,661.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.11 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x5 | DeepSeek-V4.1-Flash-engram-hbm | 5 | hybrid | on_wafer_n5 | rom_wafer_serdes | 84 | 154.41 us | 647.6 tok/s | 6,476.4 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 4 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.41 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 20 | pipeline | nvlink5 | infiniband_ndr | 19 | 25.06 us | 3,989.9 tok/s | 39,899.4 tok/s | 17 x point_to_point span 2 on nvlink5 (traversals 1.0) = 20.59 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-tensor | DeepSeek-V4.1-Flash-engram-hbm | 20 | tensor | nvlink5 | infiniband_ndr | 160 | 551.96 us | 181.2 tok/s | 1,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 20 | hybrid | nvlink5 | infiniband_ndr | 82 | 198.86 us | 502.9 tok/s | 5,028.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 20 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.59 us | 513.9 tok/s | 5,138.9 tok/s | 80 x all_reduce span 20 on nvlink5_nvl72 (traversals 2.0) = 194.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-expert | DeepSeek-V4.1-Flash-engram-hbm | 20 | expert | nvlink5 | infiniband_ndr | 160 | 360.51 us | 277.4 tok/s | 2,773.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 193.19 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 167.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x20-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 20 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.87 us | 343.8 tok/s | 3,438.0 tok/s | 80 x all_reduce span 20 on nvlink5_nvl72 (traversals 2.0) = 194.59 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.27 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x22-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 27.49 us | 3,638.2 tok/s | 36,382.5 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 23.02 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x22-tensor | DeepSeek-V4.1-Flash-engram-hbm | 22 | tensor | nvlink5 | infiniband_ndr | 160 | 551.96 us | 181.2 tok/s | 1,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x22-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 22 | hybrid | nvlink5 | infiniband_ndr | 82 | 198.86 us | 502.9 tok/s | 5,028.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x22-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 22 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.61 us | 513.9 tok/s | 5,138.6 tok/s | 80 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 194.61 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x22-expert | DeepSeek-V4.1-Flash-engram-hbm | 22 | expert | nvlink5 | infiniband_ndr | 160 | 360.06 us | 277.7 tok/s | 2,777.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 193.19 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 166.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x22-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 22 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.85 us | 343.8 tok/s | 3,438.1 tok/s | 80 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 194.61 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.25 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x26-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 26 | pipeline | nvlink5 | infiniband_ndr | 25 | 33.35 us | 2,998.1 tok/s | 29,980.8 tok/s | 22 x point_to_point span 2 on nvlink5 (traversals 1.0) = 26.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x26-tensor | DeepSeek-V4.1-Flash-engram-hbm | 26 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x26-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 26 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x26-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 26 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.63 us | 513.8 tok/s | 5,138.1 tok/s | 80 x all_reduce span 26 on nvlink5_nvl72 (traversals 2.0) = 194.63 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x26-expert | DeepSeek-V4.1-Flash-engram-hbm | 26 | expert | nvlink5 | infiniband_ndr | 160 | 358.98 us | 278.6 tok/s | 2,785.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 166.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x26-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 26 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.84 us | 343.8 tok/s | 3,438.4 tok/s | 80 x all_reduce span 26 on nvlink5_nvl72 (traversals 2.0) = 194.63 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.21 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.99 us | 2,703.5 tok/s | 27,035.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.28 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-tensor | DeepSeek-V4.1-Flash-engram-hbm | 29 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 29 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.64 us | 513.8 tok/s | 5,137.8 tok/s | 80 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 194.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-expert | DeepSeek-V4.1-Flash-engram-hbm | 29 | expert | nvlink5 | infiniband_ndr | 160 | 358.59 us | 278.9 tok/s | 2,788.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x29-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.8 tok/s | 3,438.5 tok/s | 80 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 194.64 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 30 | pipeline | nvlink5 | infiniband_ndr | 29 | 38.20 us | 2,617.8 tok/s | 26,177.9 tok/s | 26 x point_to_point span 2 on nvlink5 (traversals 1.0) = 31.50 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-tensor | DeepSeek-V4.1-Flash-engram-hbm | 30 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 30 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 30 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.64 us | 513.8 tok/s | 5,137.7 tok/s | 80 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 194.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-expert | DeepSeek-V4.1-Flash-engram-hbm | 30 | expert | nvlink5 | infiniband_ndr | 160 | 358.47 us | 279.0 tok/s | 2,789.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x30-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 30 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.9 tok/s | 3,438.5 tok/s | 80 x all_reduce span 30 on nvlink5_nvl72 (traversals 2.0) = 194.64 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x31-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 31 | pipeline | nvlink5 | infiniband_ndr | 30 | 39.41 us | 2,537.3 tok/s | 25,373.2 tok/s | 27 x point_to_point span 2 on nvlink5 (traversals 1.0) = 32.71 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x31-tensor | DeepSeek-V4.1-Flash-engram-hbm | 31 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x31-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 31 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x31-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 31 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.64 us | 513.8 tok/s | 5,137.6 tok/s | 80 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 194.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x31-expert | DeepSeek-V4.1-Flash-engram-hbm | 31 | expert | nvlink5 | infiniband_ndr | 160 | 358.37 us | 279.0 tok/s | 2,790.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x31-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 31 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.9 tok/s | 3,438.6 tok/s | 80 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 194.64 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 32 | pipeline | nvlink5 | infiniband_ndr | 31 | 40.62 us | 2,461.7 tok/s | 24,616.6 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.92 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-tensor | DeepSeek-V4.1-Flash-engram-hbm | 32 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 32 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 32 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.65 us | 513.8 tok/s | 5,137.5 tok/s | 80 x all_reduce span 32 on nvlink5_nvl72 (traversals 2.0) = 194.65 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-expert | DeepSeek-V4.1-Flash-engram-hbm | 32 | expert | nvlink5 | infiniband_ndr | 160 | 358.07 us | 279.3 tok/s | 2,792.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x32-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 32 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.9 tok/s | 3,438.6 tok/s | 80 x all_reduce span 32 on nvlink5_nvl72 (traversals 2.0) = 194.65 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 35 | pipeline | nvlink5 | infiniband_ndr | 34 | 45.28 us | 2,208.5 tok/s | 22,084.5 tok/s | 30 x point_to_point span 2 on nvlink5 (traversals 1.0) = 36.34 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-tensor | DeepSeek-V4.1-Flash-engram-hbm | 35 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 35 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 35 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.65 us | 513.7 tok/s | 5,137.4 tok/s | 80 x all_reduce span 35 on nvlink5_nvl72 (traversals 2.0) = 194.65 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-expert | DeepSeek-V4.1-Flash-engram-hbm | 35 | expert | nvlink5 | infiniband_ndr | 160 | 357.81 us | 279.5 tok/s | 2,794.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.21 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x35-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 35 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.81 us | 343.9 tok/s | 3,438.7 tok/s | 80 x all_reduce span 35 on nvlink5_nvl72 (traversals 2.0) = 194.65 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.16 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x40-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 40 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x40-tensor | DeepSeek-V4.1-Flash-engram-hbm | 40 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x40-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 40 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x40-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 40 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.66 us | 513.7 tok/s | 5,137.1 tok/s | 80 x all_reduce span 40 on nvlink5_nvl72 (traversals 2.0) = 194.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x40-expert | DeepSeek-V4.1-Flash-engram-hbm | 40 | expert | nvlink5 | infiniband_ndr | 160 | 357.34 us | 279.8 tok/s | 2,798.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x40-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 40 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.80 us | 343.9 tok/s | 3,438.8 tok/s | 80 x all_reduce span 40 on nvlink5_nvl72 (traversals 2.0) = 194.66 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 41 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-tensor | DeepSeek-V4.1-Flash-engram-hbm | 41 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 41 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 41 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.66 us | 513.7 tok/s | 5,137.1 tok/s | 80 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 194.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-expert | DeepSeek-V4.1-Flash-engram-hbm | 41 | expert | nvlink5 | infiniband_ndr | 160 | 357.28 us | 279.9 tok/s | 2,799.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.80 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x41-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 41 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.80 us | 343.9 tok/s | 3,438.8 tok/s | 80 x all_reduce span 41 on nvlink5_nvl72 (traversals 2.0) = 194.66 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.13 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 46 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-tensor | DeepSeek-V4.1-Flash-engram-hbm | 46 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 46 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 46 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.9 tok/s | 80 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-expert | DeepSeek-V4.1-Flash-engram-hbm | 46 | expert | nvlink5 | infiniband_ndr | 160 | 357.01 us | 280.1 tok/s | 2,801.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.54 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x46-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 46 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 55 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-tensor | DeepSeek-V4.1-Flash-engram-hbm | 55 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 55 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 55 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.6 tok/s | 80 x all_reduce span 55 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-expert | DeepSeek-V4.1-Flash-engram-hbm | 55 | expert | nvlink5 | infiniband_ndr | 160 | 356.59 us | 280.4 tok/s | 2,804.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x55-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 55 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 55 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.10 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x57-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 57 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x57-tensor | DeepSeek-V4.1-Flash-engram-hbm | 57 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x57-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 57 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x57-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 57 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.6 tok/s | 80 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x57-expert | DeepSeek-V4.1-Flash-engram-hbm | 57 | expert | nvlink5 | infiniband_ndr | 160 | 356.47 us | 280.5 tok/s | 2,805.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.34 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x57-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 57 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.10 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 58 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-tensor | DeepSeek-V4.1-Flash-engram-hbm | 58 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 58 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.5 tok/s | 80 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-expert | DeepSeek-V4.1-Flash-engram-hbm | 58 | expert | nvlink5 | infiniband_ndr | 160 | 356.44 us | 280.6 tok/s | 2,805.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.34 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.09 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x58-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.09 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x65-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 65 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x65-tensor | DeepSeek-V4.1-Flash-engram-hbm | 65 | tensor | nvlink5 | infiniband_ndr | 160 | 562.88 us | 177.7 tok/s | 1,776.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 368.49 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x65-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 65 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.27 us | 471.1 tok/s | 4,711.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x65-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 65 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.4 tok/s | 80 x all_reduce span 65 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x65-expert | DeepSeek-V4.1-Flash-engram-hbm | 65 | expert | nvlink5 | infiniband_ndr | 160 | 356.21 us | 280.7 tok/s | 2,807.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.30 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x65-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 65 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 65 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x69-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 69 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x69-tensor | DeepSeek-V4.1-Flash-engram-hbm | 69 | tensor | nvlink5 | infiniband_ndr | 160 | 562.88 us | 177.7 tok/s | 1,776.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 368.49 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x69-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 69 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.27 us | 471.1 tok/s | 4,711.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x69-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 69 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.3 tok/s | 80 x all_reduce span 69 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x69-expert | DeepSeek-V4.1-Flash-engram-hbm | 69 | expert | nvlink5 | infiniband_ndr | 160 | 356.12 us | 280.8 tok/s | 2,808.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.30 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.82 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x69-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 69 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 69 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x71-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 71 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x71-tensor | DeepSeek-V4.1-Flash-engram-hbm | 71 | tensor | nvlink5 | infiniband_ndr | 160 | 562.88 us | 177.7 tok/s | 1,776.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 368.49 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x71-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 71 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.27 us | 471.1 tok/s | 4,711.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x71-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 71 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.3 tok/s | 80 x all_reduce span 71 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x71-expert | DeepSeek-V4.1-Flash-engram-hbm | 71 | expert | nvlink5 | infiniband_ndr | 160 | 356.08 us | 280.8 tok/s | 2,808.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.30 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.78 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x71-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 71 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.2 tok/s | 80 x all_reduce span 71 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x81-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 81 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x81-tensor | DeepSeek-V4.1-Flash-engram-hbm | 81 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x81-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 81 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x81-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 81 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x81-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 81 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x81-expert | DeepSeek-V4.1-Flash-engram-hbm | 81 | expert | nvlink5 | infiniband_ndr | 160 | 355.85 us | 281.0 tok/s | 2,810.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.61 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x81-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 81 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.31 us | 279.1 tok/s | 2,790.9 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.61 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 82 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-tensor | DeepSeek-V4.1-Flash-engram-hbm | 82 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 82 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 82 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 82 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-expert | DeepSeek-V4.1-Flash-engram-hbm | 82 | expert | nvlink5 | infiniband_ndr | 160 | 355.84 us | 281.0 tok/s | 2,810.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.60 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x82-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 82 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.29 us | 279.1 tok/s | 2,791.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.60 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 83 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-tensor | DeepSeek-V4.1-Flash-engram-hbm | 83 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 83 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 83 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 83 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-expert | DeepSeek-V4.1-Flash-engram-hbm | 83 | expert | nvlink5 | infiniband_ndr | 160 | 355.82 us | 281.0 tok/s | 2,810.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.58 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x83-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 83 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.28 us | 279.1 tok/s | 2,791.1 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.58 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 87 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-tensor | DeepSeek-V4.1-Flash-engram-hbm | 87 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 87 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-expert | DeepSeek-V4.1-Flash-engram-hbm | 87 | expert | nvlink5 | infiniband_ndr | 160 | 355.77 us | 281.1 tok/s | 2,810.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.53 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x87-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.22 us | 279.2 tok/s | 2,791.6 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.53 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x88-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 88 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x88-tensor | DeepSeek-V4.1-Flash-engram-hbm | 88 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x88-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 88 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x88-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 88 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x88-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 88 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x88-expert | DeepSeek-V4.1-Flash-engram-hbm | 88 | expert | nvlink5 | infiniband_ndr | 160 | 355.73 us | 281.1 tok/s | 2,811.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.22 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.52 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x88-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 88 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.21 us | 279.2 tok/s | 2,791.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.52 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x94-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 94 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x94-tensor | DeepSeek-V4.1-Flash-engram-hbm | 94 | tensor | nvlink5 | infiniband_ndr | 160 | 564.25 us | 177.2 tok/s | 1,772.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 369.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x94-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 94 | hybrid | nvlink5 | infiniband_ndr | 91 | 218.97 us | 456.7 tok/s | 4,566.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 24.58 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x94-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 94 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x94-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 94 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x94-expert | DeepSeek-V4.1-Flash-engram-hbm | 94 | expert | nvlink5 | infiniband_ndr | 160 | 355.66 us | 281.2 tok/s | 2,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.22 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.45 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x94-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 94 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.14 us | 279.2 tok/s | 2,792.2 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.45 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 98 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-tensor | DeepSeek-V4.1-Flash-engram-hbm | 98 | tensor | nvlink5 | infiniband_ndr | 160 | 564.56 us | 177.1 tok/s | 1,771.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 370.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 98 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.21 us | 452.1 tok/s | 4,520.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 26.82 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 98 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 98 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-expert | DeepSeek-V4.1-Flash-engram-hbm | 98 | expert | nvlink5 | infiniband_ndr | 160 | 355.60 us | 281.2 tok/s | 2,812.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.20 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x98-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 98 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.10 us | 279.3 tok/s | 2,792.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 110 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-tensor | DeepSeek-V4.1-Flash-engram-hbm | 110 | tensor | nvlink5 | infiniband_ndr | 160 | 564.83 us | 177.0 tok/s | 1,770.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 370.44 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 110 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.44 us | 447.5 tok/s | 4,475.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 29.05 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 110 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 110 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-expert | DeepSeek-V4.1-Flash-engram-hbm | 110 | expert | nvlink5 | infiniband_ndr | 160 | 355.48 us | 281.3 tok/s | 2,813.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.18 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.29 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x110-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 110 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.99 us | 279.3 tok/s | 2,793.4 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.29 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 116 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-tensor | DeepSeek-V4.1-Flash-engram-hbm | 116 | tensor | nvlink5 | infiniband_ndr | 160 | 565.06 us | 177.0 tok/s | 1,769.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 370.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 116 | hybrid | nvlink5 | infiniband_ndr | 94 | 225.68 us | 443.1 tok/s | 4,431.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 31.29 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-expert | DeepSeek-V4.1-Flash-engram-hbm | 116 | expert | nvlink5 | infiniband_ndr | 160 | 355.42 us | 281.4 tok/s | 2,813.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.17 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.25 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x116-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.94 us | 279.4 tok/s | 2,793.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.25 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 126 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-tensor | DeepSeek-V4.1-Flash-engram-hbm | 126 | tensor | nvlink5 | infiniband_ndr | 160 | 565.27 us | 176.9 tok/s | 1,769.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 370.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 126 | hybrid | nvlink5 | infiniband_ndr | 95 | 227.91 us | 438.8 tok/s | 4,387.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.52 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 126 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 126 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-expert | DeepSeek-V4.1-Flash-engram-hbm | 126 | expert | nvlink5 | infiniband_ndr | 160 | 355.34 us | 281.4 tok/s | 2,814.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.16 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x126-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 126 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.87 us | 279.4 tok/s | 2,794.3 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 130 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-tensor | DeepSeek-V4.1-Flash-engram-hbm | 130 | tensor | nvlink5 | infiniband_ndr | 160 | 565.45 us | 176.9 tok/s | 1,768.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 371.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 130 | hybrid | nvlink5 | infiniband_ndr | 96 | 230.15 us | 434.5 tok/s | 4,345.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 35.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 130 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 130 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-expert | DeepSeek-V4.1-Flash-engram-hbm | 130 | expert | nvlink5 | infiniband_ndr | 160 | 355.31 us | 281.4 tok/s | 2,814.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.15 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.16 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x130-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 130 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.85 us | 279.4 tok/s | 2,794.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.16 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x144-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 144 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x144-tensor | DeepSeek-V4.1-Flash-engram-hbm | 144 | tensor | nvlink5 | infiniband_ndr | 160 | 565.61 us | 176.8 tok/s | 1,768.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 18 on infiniband_ndr (traversals 2.0) = 371.22 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x144-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 144 | hybrid | nvlink5 | infiniband_ndr | 97 | 232.38 us | 430.3 tok/s | 4,303.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 37.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x144-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 144 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x144-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 144 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x144-expert | DeepSeek-V4.1-Flash-engram-hbm | 144 | expert | nvlink5 | infiniband_ndr | 160 | 355.22 us | 281.5 tok/s | 2,815.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.13 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x144-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 144 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.43 us | 280.6 tok/s | 2,805.6 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 173 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-tensor | DeepSeek-V4.1-Flash-engram-hbm | 173 | tensor | nvlink5 | infiniband_ndr | 160 | 566.11 us | 176.6 tok/s | 1,766.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 371.72 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 173 | hybrid | nvlink5 | infiniband_ndr | 101 | 241.32 us | 414.4 tok/s | 4,143.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-expert | DeepSeek-V4.1-Flash-engram-hbm | 173 | expert | nvlink5 | infiniband_ndr | 160 | 355.08 us | 281.6 tok/s | 2,816.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.11 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.97 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x173-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.31 us | 280.7 tok/s | 2,806.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.97 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x186-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 186 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x186-tensor | DeepSeek-V4.1-Flash-engram-hbm | 186 | tensor | nvlink5 | infiniband_ndr | 160 | 566.29 us | 176.6 tok/s | 1,765.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 371.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x186-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 186 | hybrid | nvlink5 | infiniband_ndr | 103 | 245.79 us | 406.9 tok/s | 4,068.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 51.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x186-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 186 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x186-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 186 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x186-expert | DeepSeek-V4.1-Flash-engram-hbm | 186 | expert | nvlink5 | infiniband_ndr | 160 | 355.03 us | 281.7 tok/s | 2,816.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x186-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 186 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.27 us | 280.7 tok/s | 2,806.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x187-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 187 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x187-tensor | DeepSeek-V4.1-Flash-engram-hbm | 187 | tensor | nvlink5 | infiniband_ndr | 160 | 566.29 us | 176.6 tok/s | 1,765.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 371.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x187-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 187 | hybrid | nvlink5 | infiniband_ndr | 103 | 245.79 us | 406.9 tok/s | 4,068.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 51.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x187-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 187 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x187-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 187 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x187-expert | DeepSeek-V4.1-Flash-engram-hbm | 187 | expert | nvlink5 | infiniband_ndr | 160 | 355.03 us | 281.7 tok/s | 2,816.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x187-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 187 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.27 us | 280.7 tok/s | 2,806.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 188 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-tensor | DeepSeek-V4.1-Flash-engram-hbm | 188 | tensor | nvlink5 | infiniband_ndr | 160 | 566.29 us | 176.6 tok/s | 1,765.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 371.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 188 | hybrid | nvlink5 | infiniband_ndr | 103 | 245.79 us | 406.9 tok/s | 4,068.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 51.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 188 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 188 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-expert | DeepSeek-V4.1-Flash-engram-hbm | 188 | expert | nvlink5 | infiniband_ndr | 160 | 355.03 us | 281.7 tok/s | 2,816.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.92 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x188-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 188 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.27 us | 280.7 tok/s | 2,806.9 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.92 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 193 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-tensor | DeepSeek-V4.1-Flash-engram-hbm | 193 | tensor | nvlink5 | infiniband_ndr | 160 | 566.38 us | 176.6 tok/s | 1,765.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 371.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 193 | hybrid | nvlink5 | infiniband_ndr | 104 | 248.02 us | 403.2 tok/s | 4,031.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 53.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 193 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 193 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-expert | DeepSeek-V4.1-Flash-engram-hbm | 193 | expert | nvlink5 | infiniband_ndr | 160 | 355.01 us | 281.7 tok/s | 2,816.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x193-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 193 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.26 us | 280.7 tok/s | 2,807.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 194 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-tensor | DeepSeek-V4.1-Flash-engram-hbm | 194 | tensor | nvlink5 | infiniband_ndr | 160 | 566.38 us | 176.6 tok/s | 1,765.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 371.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 194 | hybrid | nvlink5 | infiniband_ndr | 104 | 248.02 us | 403.2 tok/s | 4,031.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 53.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 194 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 194 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-expert | DeepSeek-V4.1-Flash-engram-hbm | 194 | expert | nvlink5 | infiniband_ndr | 160 | 355.01 us | 281.7 tok/s | 2,816.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x194-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 194 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.25 us | 280.7 tok/s | 2,807.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 196 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-tensor | DeepSeek-V4.1-Flash-engram-hbm | 196 | tensor | nvlink5 | infiniband_ndr | 160 | 566.38 us | 176.6 tok/s | 1,765.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 371.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 196 | hybrid | nvlink5 | infiniband_ndr | 104 | 248.02 us | 403.2 tok/s | 4,031.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 53.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 196 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 196 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-expert | DeepSeek-V4.1-Flash-engram-hbm | 196 | expert | nvlink5 | infiniband_ndr | 160 | 355.00 us | 281.7 tok/s | 2,816.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.10 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x196-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 196 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.25 us | 280.7 tok/s | 2,807.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 231 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-tensor | DeepSeek-V4.1-Flash-engram-hbm | 231 | tensor | nvlink5 | infiniband_ndr | 160 | 566.65 us | 176.5 tok/s | 1,764.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 372.26 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 231 | hybrid | nvlink5 | infiniband_ndr | 108 | 256.96 us | 389.2 tok/s | 3,891.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 62.57 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 556.36 us | 179.7 tok/s | 1,797.4 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 83 | 201.40 us | 496.5 tok/s | 4,965.3 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-expert | DeepSeek-V4.1-Flash-engram-hbm | 231 | expert | nvlink5 | infiniband_ndr | 160 | 354.91 us | 281.8 tok/s | 2,817.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.09 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.83 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x231-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.72 us | 281.1 tok/s | 2,811.2 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.90 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.83 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 318 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-tensor | DeepSeek-V4.1-Flash-engram-hbm | 318 | tensor | nvlink5 | infiniband_ndr | 160 | 567.11 us | 176.3 tok/s | 1,763.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 40 on infiniband_ndr (traversals 2.0) = 372.72 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 318 | hybrid | nvlink5 | infiniband_ndr | 119 | 281.55 us | 355.2 tok/s | 3,551.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 39 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 87.16 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 318 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 558.81 us | 179.0 tok/s | 1,789.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 318 | hybrid | nvlink5_nvl72 | infiniband_ndr | 84 | 203.63 us | 491.1 tok/s | 4,910.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-expert | DeepSeek-V4.1-Flash-engram-hbm | 318 | expert | nvlink5 | infiniband_ndr | 160 | 354.77 us | 281.9 tok/s | 2,818.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.06 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.71 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x318-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 318 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.38 us | 281.4 tok/s | 2,813.9 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.67 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.71 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 347 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-tensor | DeepSeek-V4.1-Flash-engram-hbm | 347 | tensor | nvlink5 | infiniband_ndr | 160 | 567.22 us | 176.3 tok/s | 1,763.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 372.83 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 347 | hybrid | nvlink5 | infiniband_ndr | 119 | 281.55 us | 355.2 tok/s | 3,551.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 39 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 87.16 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-tensor | DeepSeek-V4.1-Flash-engram-hbm | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 558.81 us | 179.0 tok/s | 1,789.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 84 | 203.63 us | 491.1 tok/s | 4,910.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-expert | DeepSeek-V4.1-Flash-engram-hbm | 347 | expert | nvlink5 | infiniband_ndr | 160 | 354.74 us | 281.9 tok/s | 2,819.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.06 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.68 us |
| DeepSeek-V4.1-Flash-engram-hbm/b200_sxm-x347-nvl72-expert | DeepSeek-V4.1-Flash-engram-hbm | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.36 us | 281.4 tok/s | 2,814.1 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.67 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.68 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4.1-Flash-engram-hbm | 1 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x108 | 88,020 | 15,405.4 | 0.175 | 15,405.4 (88,020) | 5,850.1 (138,675) | 0.38x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x108 | 88,020 | 15,405.4 | 0.175 | 15,405.4 (88,020) | 5,821.8 (231,125) | 0.38x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x108 | 88,020 | 15,405.4 | 0.175 | 15,405.4 (88,020) | 5,821.8 (231,125) | 0.38x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x108 | 88,020 | 15,405.4 | 0.175 | 15,405.4 (88,020) | 5,676.7 (231,125) | 0.37x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x108 | 88,020 | 15,405.4 | 0.175 | 15,405.4 (88,020) | 5,432.7 (277,350) | 0.35x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x112 | 91,280 | 14,214.5 | 0.156 | 14,214.5 (91,280) | 5,153.5 (369,800) | 0.36x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 13,034.9 | 0.047 | 13,034.9 (277,100) | 4,896.1 (554,700) | 0.38x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 5,005.8 | 0.018 | 5,005.8 (277,100) | 3,110.2 (554,700) | 0.62x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 1,593.3 | 0.009 | 1,593.3 (185,005) | 1,565.5 (554,700) | 0.98x | compute |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | array | array | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 566.8 | 0.002 | 566.8 (277,100) | 398.3 (554,700) | 0.70x | weight_read |

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
| DeepSeek-V4.1-Flash-engram-hbm | 384 | 752.0 MB | 128.3 mm2 | 23.09 mm2 (18.0%) | 49,261 mm2 | 8,867 mm2 | 52,460 mm2 = 64.4 reticles |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | sram | 607,862.2 | 26,077.4 | 26,077.4 | 23.31x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | sram | 607,862.2 | 26,077.4 | 26,077.4 | 23.31x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | sram | 607,862.2 | 26,077.4 | 31,757.3 | 23.31x | 1.22x | weight_read | weight_read | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | sram | 607,862.2 | 26,077.4 | 51,867.1 | 23.31x | 1.99x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | sram | 607,862.2 | 26,077.4 | 84,725.0 | 23.31x | 3.25x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | sram | 607,862.2 | 26,077.4 | 126,933.9 | 23.31x | 4.87x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | sram | 667,129.8 | 26,077.4 | 177,251.4 | 25.58x | 6.80x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | sram | 1,186,310.4 | 26,081.1 | 364,121.0 | 45.49x | 13.96x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | sram | 1,631,531.3 | 26,103.5 | 514,379.5 | 62.50x | 19.71x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | sram | 2,321,735.4 | 26,110.7 | 665,022.7 | 88.92x | 25.47x | weight_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | rom | 1,584,387.8 | 285,882.7 | 285,882.7 | 5.54x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | rom | 1,584,387.8 | 285,882.7 | 285,882.7 | 5.54x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | rom | 1,584,387.8 | 285,882.7 | 285,882.7 | 5.54x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | rom | 1,584,387.8 | 285,882.7 | 285,882.7 | 5.54x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | rom | 1,584,387.8 | 285,882.7 | 285,882.7 | 5.54x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | rom | 1,584,387.8 | 285,882.7 | 285,882.7 | 5.54x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | rom | 1,584,387.8 | 285,882.7 | 285,882.7 | 5.54x | 1.00x | kv_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | rom | 1,584,387.8 | 285,882.7 | 474,845.5 | 5.54x | 1.66x | kv_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | rom | 1,603,035.1 | 289,021.0 | 677,161.6 | 5.55x | 2.34x | kv_read | weight_read | kv_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | rom | 1,631,630.2 | 289,937.1 | 682,212.2 | 5.63x | 2.35x | kv_read | weight_read | kv_read |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 1,584,387.8 | 2.856 | kv_read | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 26,077.4 | 0.113 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perregion | 231,125 | 1.00 | 1.00 | 26,077.4 | 0.113 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 1,584,387.8 | 2.856 | kv_read | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 26,077.4 | 0.113 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perregion | 231,125 | 1.00 | 1.00 | 26,077.4 | 0.113 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 1,584,387.8 | 2.856 | kv_read | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 26,077.4 | 0.113 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x39-perregion | 31,785 | 1.00 | 1.43 | 31,757.3 | 0.999 | link_latency | 0.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 1,584,387.8 | 2.856 | kv_read | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 26,077.4 | 0.113 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x39-perregion | 31,785 | 1.00 | 1.99 | 51,867.1 | 1.632 | weight_read | 0.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 1,584,387.8 | 2.856 | kv_read | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 26,077.4 | 0.113 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x39-perregion | 31,785 | 1.00 | 2.54 | 84,725.0 | 2.666 | weight_read | 0.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 607,862.2 | 1.096 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 1,584,387.8 | 2.856 | kv_read | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 26,077.4 | 0.113 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x39-perregion | 31,785 | 1.00 | 3.49 | 126,933.9 | 3.994 | weight_read | 0.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x162 | 132,030 | 1.00 | 1.00 | 667,129.8 | 5.053 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 1,584,387.8 | 2.856 | kv_read | 2.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 26,077.4 | 0.113 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-tensor-x39-perregion | 31,785 | 1.00 | 4.92 | 177,251.4 | 5.577 | weight_read | 0.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x216 | 176,040 | 1.00 | 1.00 | 1,186,310.4 | 6.739 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 1,584,387.8 | 2.856 | kv_read | 1.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x39-perstream | 31,785 | 1.00 | 6.56 | 26,081.1 | 0.821 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 11.11 | 1.00 | 285,882.7 | 1.237 | weight_read | 0.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-tensor-x5-perregion | 231,125 | 1.00 | 10.96 | 364,121.0 | 1.575 | weight_read | 0.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x5-perregion-romfill | 231,125 | 11.11 | 4.40 | 474,845.5 | 2.054 | kv_read | 0.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 1.00 | 1.00 | 1,631,531.3 | 8.819 | compute | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 1,603,035.1 | 2.890 | kv_read | 0.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-pipeline-x39-perstream | 31,785 | 1.00 | 26.26 | 26,103.5 | 0.821 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 11.11 | 3.61 | 289,021.0 | 1.250 | weight_read | 0.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x5-perregion | 231,125 | 1.00 | 9.53 | 514,379.5 | 2.226 | weight_read | 0.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 11.11 | 1.36 | 677,161.6 | 2.930 | kv_read | 0.42x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 2,321,735.4 | 8.379 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.94 | 1.00 | 1,631,630.2 | 2.941 | kv_read | 0.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 14.42 | 26,110.7 | 0.113 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 11.11 | 14.42 | 289,937.1 | 1.254 | weight_read | 0.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-hybrid-x5-perregion | 231,125 | 1.00 | 24.46 | 665,022.7 | 2.877 | kv_read | 0.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 11.11 | 2.43 | 682,212.2 | 2.952 | kv_read | 0.29x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 127 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 127 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 39 | 6.56 | 1.044 | 1.840 | 1.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 39 | 26.26 | 1.211 | 3.207 | 2.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 39 | 105.03 | 2.029 | 6.434 | 3.17x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 20 | 9.14 | 5.21 | 1.75x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 20 | 13.99 | 6.79 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 20 | 18.06 | 8.50 | 2.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 20 | 19.75 | 10.19 | 1.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 20 | 19.99 | 11.71 | 1.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 20 | 20.00 | 12.89 | 1.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 20 | 20.00 | 13.90 | 1.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 20 | 20.00 | 13.93 | 1.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 22 | 9.36 | 5.37 | 1.74x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 22 | 14.61 | 7.06 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 22 | 19.34 | 8.91 | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 22 | 21.59 | 10.77 | 2.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 22 | 21.98 | 12.46 | 1.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 22 | 22.00 | 13.78 | 1.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 22 | 22.00 | 14.92 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 22 | 22.00 | 14.97 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 26 | 9.70 | 5.65 | 1.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 26 | 15.63 | 7.55 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 26 | 21.63 | 9.66 | 2.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 26 | 25.09 | 11.84 | 2.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 26 | 25.93 | 13.85 | 1.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 26 | 26.00 | 15.46 | 1.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 26 | 26.00 | 16.87 | 1.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 26 | 26.00 | 16.93 | 1.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 26 | 26.00 | 16.93 | 1.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 29 | 9.90 | 5.83 | 1.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 29 | 16.26 | 7.87 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 29 | 23.12 | 10.16 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 29 | 27.56 | 12.57 | 2.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 29 | 28.86 | 14.82 | 1.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 29 | 28.99 | 16.64 | 1.74x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 29 | 29.00 | 18.25 | 1.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 30 | 5.52 | 4.32 | 1.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 30 | 9.96 | 5.89 | 1.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 30 | 16.45 | 7.97 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 30 | 23.58 | 10.32 | 2.28x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 30 | 28.35 | 12.80 | 2.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 30 | 29.83 | 15.13 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 30 | 29.99 | 17.02 | 1.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 30 | 30.00 | 18.69 | 1.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 30 | 30.00 | 18.76 | 1.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 30 | 30.00 | 18.76 | 1.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 31 | 10.02 | 5.94 | 1.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 31 | 16.63 | 8.07 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 31 | 24.02 | 10.47 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 31 | 29.12 | 13.02 | 2.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 31 | 30.79 | 15.43 | 2.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 31 | 30.99 | 17.39 | 1.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 31 | 31.00 | 19.13 | 1.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 31 | 31.00 | 19.20 | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 31 | 31.00 | 19.20 | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 32 | 10.07 | 6.00 | 1.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 32 | 16.80 | 8.16 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 32 | 24.44 | 10.62 | 2.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 32 | 29.88 | 13.24 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 32 | 31.74 | 15.73 | 2.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 32 | 31.99 | 17.76 | 1.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 32 | 32.00 | 19.56 | 1.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 32 | 32.00 | 19.64 | 1.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 32 | 32.00 | 19.64 | 1.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 35 | 5.59 | 4.47 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 35 | 10.22 | 6.15 | 1.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 35 | 17.26 | 8.43 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 35 | 25.63 | 11.05 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 35 | 32.07 | 13.87 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 35 | 34.57 | 16.58 | 2.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 35 | 34.97 | 18.82 | 1.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 35 | 35.00 | 20.82 | 1.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 35 | 35.00 | 20.90 | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 35 | 35.00 | 20.90 | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 40 | 10.41 | 6.38 | 1.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 40 | 17.91 | 8.83 | 2.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 40 | 27.35 | 11.70 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 40 | 35.41 | 14.84 | 2.39x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 40 | 39.15 | 17.91 | 2.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 40 | 39.92 | 20.48 | 1.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 40 | 40.00 | 22.81 | 1.75x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 40 | 40.00 | 22.90 | 1.75x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 40 | 40.00 | 22.90 | 1.75x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 41 | 10.44 | 6.42 | 1.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 41 | 18.02 | 8.90 | 2.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 41 | 27.65 | 11.82 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 41 | 36.04 | 15.02 | 2.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 41 | 40.04 | 18.16 | 2.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 41 | 40.90 | 20.80 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 41 | 41.00 | 23.19 | 1.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 41 | 41.00 | 23.29 | 1.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 41 | 41.00 | 23.29 | 1.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 46 | 10.59 | 6.62 | 1.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 46 | 18.52 | 9.24 | 2.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 46 | 29.06 | 12.38 | 2.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 46 | 38.98 | 15.89 | 2.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 46 | 44.37 | 19.37 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 46 | 45.78 | 22.32 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 46 | 45.99 | 25.03 | 1.84x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 46 | 45.99 | 25.14 | 1.83x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 46 | 45.99 | 25.14 | 1.83x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 55 | 10.79 | 6.94 | 1.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 55 | 19.23 | 9.76 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 55 | 31.11 | 13.27 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 55 | 43.55 | 17.27 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 55 | 51.62 | 21.32 | 2.42x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 55 | 54.37 | 24.83 | 2.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 55 | 54.95 | 28.10 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 55 | 54.95 | 28.23 | 1.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 55 | 54.95 | 28.23 | 1.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 57 | 5.74 | 4.89 | 1.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 57 | 10.83 | 7.00 | 1.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 57 | 19.36 | 9.87 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 57 | 31.50 | 13.45 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 57 | 44.46 | 17.56 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 57 | 53.13 | 21.73 | 2.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 57 | 56.24 | 25.35 | 2.22x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 57 | 56.93 | 28.74 | 1.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 57 | 56.94 | 28.88 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 57 | 56.94 | 28.88 | 1.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 65 | 5.77 | 4.99 | 1.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 65 | 10.96 | 7.25 | 1.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 65 | 19.81 | 10.23 | 1.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 65 | 32.87 | 14.11 | 2.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 65 | 47.74 | 18.61 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 65 | 58.84 | 23.24 | 2.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 65 | 63.52 | 27.33 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 65 | 64.81 | 31.19 | 2.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 65 | 64.83 | 31.35 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 65 | 64.83 | 31.35 | 2.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 69 | 11.01 | 7.36 | 1.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 69 | 20.00 | 10.40 | 1.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 69 | 33.47 | 14.41 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 69 | 49.20 | 19.09 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 69 | 61.50 | 23.95 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 69 | 67.04 | 28.25 | 2.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 69 | 68.72 | 32.35 | 2.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 69 | 68.75 | 32.52 | 2.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 69 | 68.75 | 32.52 | 2.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 71 | 11.03 | 7.41 | 1.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 71 | 20.09 | 10.48 | 1.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 71 | 33.74 | 14.56 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 71 | 49.90 | 19.33 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 71 | 62.78 | 24.30 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 71 | 68.77 | 28.70 | 2.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 71 | 70.66 | 32.91 | 2.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 71 | 70.69 | 33.09 | 2.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 71 | 70.69 | 33.09 | 2.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 81 | 11.14 | 7.66 | 1.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 81 | 20.46 | 10.83 | 1.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 81 | 34.95 | 15.25 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 81 | 53.01 | 20.42 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 81 | 68.74 | 25.90 | 2.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 81 | 77.08 | 30.83 | 2.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 81 | 80.25 | 35.60 | 2.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 81 | 80.31 | 35.80 | 2.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 81 | 80.31 | 35.80 | 2.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 82 | 11.15 | 7.68 | 1.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 82 | 20.50 | 10.86 | 1.89x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 82 | 35.06 | 15.32 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 82 | 53.29 | 20.53 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 82 | 69.30 | 26.05 | 2.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 82 | 77.88 | 31.04 | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 82 | 81.20 | 35.85 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 82 | 81.26 | 36.05 | 2.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 82 | 81.26 | 36.05 | 2.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 83 | 11.15 | 7.71 | 1.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 83 | 20.53 | 10.90 | 1.88x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 83 | 35.16 | 15.38 | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 83 | 53.57 | 20.63 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 83 | 69.85 | 26.20 | 2.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 83 | 78.68 | 31.24 | 2.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 83 | 82.14 | 36.11 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 83 | 82.21 | 36.31 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 83 | 82.21 | 36.31 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 87 | 11.19 | 7.80 | 1.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 87 | 20.65 | 11.02 | 1.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 87 | 35.56 | 15.63 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 87 | 54.63 | 21.03 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 87 | 71.99 | 26.79 | 2.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 87 | 81.81 | 32.02 | 2.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 87 | 85.89 | 37.11 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 88 | 5.83 | 5.21 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 88 | 11.20 | 7.82 | 1.43x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 88 | 20.68 | 11.05 | 1.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 88 | 35.66 | 15.70 | 2.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 88 | 54.89 | 21.13 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 88 | 72.51 | 26.94 | 2.69x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 88 | 82.58 | 32.22 | 2.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 88 | 86.82 | 37.35 | 2.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 88 | 86.91 | 37.57 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 88 | 86.91 | 37.57 | 2.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 94 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 94 | 11.24 | 7.94 | 1.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 94 | 20.85 | 11.23 | 1.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 94 | 36.19 | 16.05 | 2.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 94 | 56.34 | 21.70 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 94 | 75.50 | 27.77 | 2.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 94 | 87.07 | 33.34 | 2.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 94 | 92.34 | 38.79 | 2.38x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 94 | 92.45 | 39.02 | 2.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 94 | 92.45 | 39.02 | 2.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 98 | 11.27 | 8.02 | 1.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 98 | 20.94 | 11.34 | 1.85x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 98 | 36.52 | 16.28 | 2.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 98 | 57.24 | 22.06 | 2.60x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 98 | 77.39 | 28.31 | 2.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 98 | 89.96 | 34.06 | 2.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 98 | 95.95 | 39.72 | 2.42x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 98 | 96.09 | 39.95 | 2.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 98 | 96.09 | 39.95 | 2.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 110 | 11.33 | 8.24 | 1.37x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 110 | 21.20 | 11.65 | 1.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 110 | 37.37 | 16.92 | 2.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 110 | 59.63 | 23.06 | 2.59x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 110 | 82.55 | 29.82 | 2.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 110 | 98.14 | 36.10 | 2.72x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 110 | 106.49 | 42.35 | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 110 | 106.70 | 42.61 | 2.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 110 | 106.70 | 42.61 | 2.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 116 | 11.36 | 8.35 | 1.36x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 116 | 21.31 | 11.79 | 1.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 116 | 37.74 | 17.21 | 2.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 116 | 60.68 | 23.52 | 2.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 116 | 84.89 | 30.52 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 116 | 101.95 | 37.06 | 2.75x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 116 | 111.57 | 43.59 | 2.56x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 126 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 126 | 11.40 | 8.50 | 1.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 126 | 21.47 | 12.02 | 1.79x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 126 | 38.29 | 17.66 | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 126 | 62.26 | 24.23 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 126 | 88.47 | 31.63 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 126 | 107.95 | 38.58 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 126 | 119.76 | 45.56 | 2.63x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 126 | 120.09 | 45.86 | 2.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 126 | 120.09 | 45.86 | 2.62x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 130 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 130 | 11.42 | 8.56 | 1.33x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 130 | 21.53 | 12.10 | 1.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 130 | 38.48 | 17.83 | 2.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 130 | 62.84 | 24.50 | 2.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 130 | 89.81 | 32.05 | 2.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 130 | 110.22 | 39.16 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 130 | 122.94 | 46.32 | 2.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 130 | 123.30 | 46.63 | 2.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 130 | 123.30 | 46.63 | 2.64x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 144 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 144 | 11.47 | 8.75 | 1.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 144 | 21.70 | 12.39 | 1.75x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 144 | 39.10 | 18.38 | 2.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 144 | 64.66 | 25.37 | 2.55x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 144 | 94.08 | 33.43 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 144 | 117.67 | 41.09 | 2.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 144 | 133.60 | 48.85 | 2.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 144 | 134.09 | 49.19 | 2.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 144 | 134.09 | 49.19 | 2.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 173 | 11.54 | 9.09 | 1.27x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 173 | 21.98 | 12.94 | 1.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 173 | 40.08 | 19.31 | 2.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 173 | 67.63 | 26.93 | 2.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 173 | 101.33 | 35.95 | 2.82x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 173 | 130.91 | 44.63 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 173 | 153.57 | 53.58 | 2.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 186 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 186 | 11.56 | 9.21 | 1.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 186 | 22.08 | 13.16 | 1.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 186 | 40.42 | 19.66 | 2.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 186 | 68.71 | 27.57 | 2.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 186 | 104.04 | 36.97 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 186 | 136.04 | 46.07 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 186 | 161.65 | 55.50 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 186 | 162.53 | 55.91 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 186 | 162.53 | 55.91 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 187 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 187 | 11.57 | 9.22 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 187 | 22.09 | 13.18 | 1.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 187 | 40.45 | 19.68 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 187 | 68.79 | 27.61 | 2.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 187 | 104.23 | 37.05 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 187 | 136.42 | 46.18 | 2.95x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 187 | 162.25 | 55.64 | 2.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 187 | 163.14 | 56.05 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 187 | 163.14 | 56.05 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 188 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 188 | 11.57 | 9.23 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 188 | 22.10 | 13.19 | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 188 | 40.47 | 19.71 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 188 | 68.86 | 27.66 | 2.49x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 188 | 104.43 | 37.13 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 188 | 136.79 | 46.29 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 188 | 162.85 | 55.79 | 2.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 188 | 163.75 | 56.20 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 188 | 163.75 | 56.20 | 2.91x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 193 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 193 | 11.58 | 9.28 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 193 | 22.13 | 13.28 | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 193 | 40.59 | 19.83 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 193 | 69.24 | 27.89 | 2.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 193 | 105.38 | 37.51 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 193 | 138.62 | 46.82 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 193 | 165.80 | 56.49 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 193 | 166.74 | 56.91 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 193 | 166.74 | 56.91 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 194 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 194 | 11.58 | 9.29 | 1.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 194 | 22.14 | 13.29 | 1.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 194 | 40.62 | 19.86 | 2.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 194 | 69.31 | 27.94 | 2.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 194 | 105.56 | 37.58 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 194 | 138.98 | 46.92 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 194 | 166.38 | 56.63 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 194 | 167.33 | 57.05 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 194 | 167.33 | 57.05 | 2.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 196 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 196 | 11.58 | 9.30 | 1.24x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 196 | 22.15 | 13.32 | 1.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 196 | 40.66 | 19.90 | 2.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 196 | 69.45 | 28.03 | 2.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 196 | 105.93 | 37.73 | 2.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 196 | 139.69 | 47.13 | 2.96x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 196 | 167.53 | 56.91 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 196 | 168.51 | 57.33 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 196 | 168.51 | 57.33 | 2.94x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 231 | 11.63 | 9.58 | 1.21x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 231 | 22.34 | 13.86 | 1.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 231 | 41.34 | 20.63 | 2.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 231 | 71.61 | 29.55 | 2.42x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 231 | 111.55 | 40.16 | 2.78x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 231 | 150.80 | 50.51 | 2.99x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 231 | 186.03 | 61.46 | 3.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 318 | 5.95 | 5.75 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 318 | 11.70 | 10.06 | 1.16x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 318 | 22.63 | 14.98 | 1.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 318 | 42.42 | 21.93 | 1.93x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 318 | 75.10 | 32.72 | 2.30x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 318 | 120.98 | 44.77 | 2.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 318 | 170.47 | 57.13 | 2.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 318 | 221.06 | 70.66 | 3.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 318 | 223.12 | 71.25 | 3.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 318 | 223.12 | 71.25 | 3.13x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 347 | 11.72 | 10.18 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 347 | 22.70 | 15.30 | 1.48x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 347 | 42.66 | 22.28 | 1.92x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 347 | 75.90 | 33.59 | 2.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 347 | 123.23 | 45.96 | 2.68x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 347 | 175.33 | 59.00 | 2.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 347 | 230.16 | 73.28 | 3.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 347 | 232.44 | 73.90 | 3.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 347 | 232.44 | 73.90 | 3.15x |

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
| gpu | DeepSeek-V4.1-Flash-engram-hbm | 1 | 10.05 | 4.3% |
| rom | DeepSeek-V4.1-Flash-engram-hbm | 1 | 10.05 | 15.9% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | sram | interleaved | 128 B | 1.85x |
| DeepSeek-V4.1-Flash-engram-hbm | hbm | interleaved | 32 B | 1.39x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 135 | 0.44% | 2.08 | 3.52 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 127 | 0.43% | 1.94 | 3.52 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 3 | 0.31% | 1.83 | 3.52 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 3 | 0.31% | 1.83 | 3.52 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 3 | 0.31% | 1.83 | 3.52 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 3 | 0.31% | 1.83 | 3.52 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 3 | 0.31% | 1.83 | 3.52 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 678.5 | 38,676.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 678.5 | 38,676.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 678.5 | 38,676.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 678.5 | 38,676.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 678.5 | 38,676.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 1.56% | 13.0 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 678.5 | 38,676.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 1.75% | 13.6 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 604.8 | 38,708.7 |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 6.83% | 28.2 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 152.0 | 38,907.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 1024 | 24.64% | 79.7 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 38.0 | 38,957.2 |
| DeepSeek-V4.1-Flash-engram-hbm | 4096 | 67.75% | 204.2 GB | 100.00% | 8,922.81 TB/s | 8,922.81 TB/s | 9.5 | 38,969.7 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 12 |
| gpu | link_latency | 1385 |
| gpu | thermal | 388 |
| gpu | weight_read | 775 |
| rom | compute | 947 |
| rom | infeasible | 2463 |
| rom | kv_read | 105 |
| rom | link_latency | 1190 |
| rom | thermal | 17 |
| rom | weight_read | 708 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 12 |
| rom | CAPACITY | 2463 |

## Mechanical consistency audit

**FAIL** over 169,404 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x135', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x140', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x160', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x173', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x184', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x185', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x192', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x256', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-pipeline-x384', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x135', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x140', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x160', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x173', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x184', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x185', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x192', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x256', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-tensor-x384', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x135', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x140', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x160', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x173', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x184', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x185', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x192', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x256', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-hw-hybrid-x384', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x135', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x140', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x160', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x173', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x184', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x185', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x192', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x256', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-array-pipeline-x384', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4.1-Flash-engram-hbm', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash-engram-hbm/ROM-N5-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4.1-Flash-engram-hbm', 1)

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

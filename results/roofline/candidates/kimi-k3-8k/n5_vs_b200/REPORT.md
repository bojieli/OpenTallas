# Area-constrained roofline: n5_vs_b200-kimi-k3-8k

> CANDIDATE MODEL under n5_vs_b200: Kimi-K3 at 8,192 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 219x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 128 devices. On the GPU side the correction reaches 101x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 65 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Kimi-K3 takes 256 x 815 mm2 (208,640 mm2, array, KV in SRAM) at 2,566 tok/s per user and 12 tok/s per 1,000 mm2, holding 1 session, against 130 copies of one unified HBM die at the same silicon: 2.1x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Kimi-K3 on 243,685 mm2 of ROM silicon at 2,625 tok/s per user against 243,200 mm2 of b200_sxm-x152-nvl72-hybrid at 1,101 tok/s: **2.4x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 53,808 resident sessions against the GPU cluster's 40,992. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 28.70x to it.** At 231,125 mm2 on Kimi-K3 the pipeline-only GPU delivers 44.61 tok/s and the same silicon running hybrid delivers 1,280 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.03x (Kimi-K3, ROM binding on `link_latency`) to 1.40x (Kimi-K3, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** Kimi-K3 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 108 to 30,739 tok/s, and its rate with every slot occupied from 30,644 to 30,739. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 284 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,366 us over NVLink, capping per-user decode at 732 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 441.0 us and cap it at 2,268 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 4 of 10 operating points and an array 6; on tokens per second per square millimetre the same points go 8 to the array and 2 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 135 of 3039 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 15.8x of aggregate throughput (Kimi-K3). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 14.25x, on Kimi-K3 at batch 4096, where the busiest region carries 3.35x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 258 of 3,039 feasible points (8.5%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `Kimi-K3/b200_sxm-x24-pipeline` at batch 4096 on 38,400 mm2, throttled 1.10x from 4 to 4 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 85% weight read against 84.9% weight read. The ROM sweep is not what melts it.


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

### Kimi-K3 at 8,192 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x256`** -- 256 x 815 mm2 reticle dies, 208,640 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **2,565.7 tok/s per user** (0.39 ms/token), binding on `link_latency`
- **12.3 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 2,566 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 12,943 W at 0.062 W/mm2, 5,044.7 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 130 copies of one unified HBM die -- `b200_sxm-x130-nvl72-hybrid`, 208,000 mm2, area ratio 1.0031 -- running the `hybrid` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 208,640 | 208,000 | 1.0031 |
| user tok/s | 2,565.7 | 1,230.2 | 2.09x |
| aggregate tok/s | 2,566 | 2,460 | 0.44x |
| resident sessions | 1 | 34,657 | -- |
| J/token | 5.0447 | 51.5916 | 10.2x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 34,657 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x72-nvl72-tensor` at 115,200 mm2 and 1,284.2 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-tensor-x256` | 208,640 | 2,565.7 | 12.3 | 1 | 2.09x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-array-hw-tensor-x299` | 243,685 | 2,625.5 | 10.8 | 53,808 | 2.38x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x256` | 208,640 | 2,565.7 | 12.3 | 1 | 2.09x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x256` | 208,640 | 2,565.7 | 12.3 | 1 | 2.09x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x256` | 208,640 | 2,565.7 | 12.3 | -- | 12.3 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x272` | 221,680 | 2,602.0 | 11.7 | 2.8 | 12.3 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x273` | 222,495 | 2,607.6 | 11.7 | 3.0 | 12.3 | stop |
| `ROM-N5-native-HBMKV-array-hw-tensor-x299` | 243,685 | 2,625.5 | 10.8 | 1.7 | 12.3 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x256` **<-- recommended** | 208,640 | 256 | 2,565.7 | 2,566 | 12.3 | 1 | `link_latency` | 12,943 | 5,044.7 | `b200_sxm-x130-nvl72-hybrid` | 2.09x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x272` | 221,680 | 272 | 2,602.0 | 2,602 | 11.7 | 1 | `link_latency` | 13,745 | 5,282.7 | `b200_sxm-x139-nvl72-hybrid` | 2.06x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x273` | 222,495 | 273 | 2,607.6 | 2,608 | 11.7 | 1 | `link_latency` | 13,796 | 5,290.7 | `b200_sxm-x139-nvl72-hybrid` | 2.06x |
| `ROM-N5-native-HBMKV-array-hw-tensor-x299` | 243,685 | 299 | 2,625.5 | 2,625 | 10.8 | 53,808 | `link_latency` | 19,046 | 7,254.3 | `b200_sxm-x152-nvl72-hybrid` | 2.38x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 168 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x256` | 208,640 | 2,565.7 | 12.3 | 1 |
| array | 168 | fastest | `ROM-N5-native-HBMKV-array-hw-tensor-x299` | 243,685 | 2,625.5 | 10.8 | 53,808 |
| array | 168 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x256` | 208,640 | 2,565.7 | 12.3 | 1 |
| wafer | 48 | densest | `ROM-N5-native-SRAMKV-wafer-hybrid-x5` | 231,125 | 2,088.3 | 9.0 | 1 |
| wafer | 48 | fastest | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 323,575 | 2,407.0 | 7.4 | 10,833 |
| wafer | 48 | smallest | `ROM-N5-native-SRAMKV-wafer-hybrid-x5` | 231,125 | 2,088.3 | 9.0 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-tensor-x299` | 243,685 | 2,625.5 | 2,625 | 53,808 | 19,046 | 7,254.3 | `link_latency` | `b200_sxm-x152-nvl72-hybrid` | 1,101.5 | 40,992 | 62,919.1 | 1.002 | 2.38x | 8.7x |
| 1 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 323,575 | 2,407.0 | 16,849 | 10,833 | 29,554 | 11,322.0 | `link_latency` | `b200_sxm-x202-nvl72-hybrid` | 1,244.1 | 55,389 | 71,461.7 | 1.001 | 1.93x | 6.3x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-tensor-x397` | 323,555 | 2,442.5 | 2,443 | 71,444 | 31,970 | 13,089.0 | `link_latency` | `b200_sxm-x202-nvl72-hybrid` | 1,244.1 | 55,389 | 71,461.7 | 1.001 | 1.96x | 5.5x |
| 1 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 323,575 | 2,407.0 | -- | 10,833 | -- | 11,322.0 | -- | -- | -- | -- | -- | 1.000 | 0.99x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-tensor-x299` | 243,685 | 2,481.7 | 4,963 | 53,808 | 19,333 | 3,895.1 | `link_latency` | `b200_sxm-x152-nvl72-hybrid` | 1,101.5 | 40,992 | 38,739.5 | 1.002 | 2.25x | 9.9x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 323,575 | 2,407.0 | 16,849 | 10,833 | 29,554 | 5,740.7 | `link_latency` | `b200_sxm-x202-nvl72-hybrid` | 1,244.1 | 55,389 | 43,010.8 | 1.001 | 1.93x | 7.5x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-tensor-x397` | 323,555 | 2,386.1 | 4,772 | 71,444 | 32,259 | 6,759.7 | `link_latency` | `b200_sxm-x202-nvl72-hybrid` | 1,244.1 | 55,389 | 43,010.8 | 1.001 | 1.92x | 6.4x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 323,575 | 2,407.0 | -- | 10,833 | -- | 5,740.7 | -- | -- | -- | -- | -- | 1.000 | 1.01x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 2,381.2 | 235,741 | 71,265 | 69,026 | 3,461.1 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 1,208.9 | 55,389 | 26,270.0 | 0.999 | 1.97x | 7.6x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 323,575 | 2,407.0 | 16,849 | 10,833 | 29,554 | 2,950.1 | `link_latency` | `b200_sxm-x202-nvl72-hybrid` | 1,208.9 | 55,389 | 26,270.0 | 1.001 | 1.99x | 8.9x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 2,381.2 | 235,741 | 71,265 | 69,026 | 3,461.1 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 1,208.9 | 55,389 | 26,270.0 | 0.999 | 1.97x | 7.6x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x7` | 323,575 | 2,407.0 | -- | 10,833 | -- | 2,950.1 | -- | -- | -- | -- | -- | 0.997 | 1.01x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 2,381.2 | 235,741 | 71,265 | 69,026 | 1,810.3 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 1,087.5 | 55,389 | 15,354.1 | 0.999 | 2.19x | 8.5x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 369,800 | 2,406.4 | 19,251 | 12,381 | 36,760 | 1,909.5 | `link_latency` | `b200_sxm-x231-nvl72-hybrid` | 1,065.3 | 63,739 | 18,192.8 | 1.001 | 2.26x | 9.5x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 2,381.2 | 235,741 | 71,265 | 69,026 | 984.8 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 910.0 | 55,389 | 9,825.5 | 0.999 | 2.62x | 10.0x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,349.3 | 37,588 | 18,572 | 54,866 | 1,459.6 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 1,054.2 | 97,140 | 13,683.4 | 0.999 | 2.23x | 9.4x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 2,381.2 | 235,741 | 71,265 | 69,026 | 572.1 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 695.9 | 55,389 | 6,927.4 | 0.999 | 3.42x | 12.1x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 2,153.1 | 68,900 | 18,572 | 70,474 | 1,022.8 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 863.9 | 97,140 | 8,972.9 | 0.999 | 2.49x | 8.8x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 2,381.2 | 235,741 | 71,265 | 69,026 | 365.8 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 490.3 | 55,389 | 5,239.0 | 0.999 | 4.86x | 14.3x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,845.0 | 118,083 | 18,572 | 76,464 | 647.5 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 646.2 | 97,140 | 6,460.7 | 0.999 | 2.86x | 10.0x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x397` | 323,555 | 986.4 | 252,521 | 71,444 | 66,502 | 263.4 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 230.9 | 55,389 | 2,894.1 | 1.001 | 4.27x | 9.5x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 992.7 | 254,143 | 18,572 | 92,817 | 365.2 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 304.0 | 97,140 | 3,741.0 | 0.999 | 3.27x | 7.9x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x397` | 323,555 | 256.3 | 262,466 | 71,444 | 67,851 | 258.5 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 124.7 | 55,389 | 1,194.0 | 1.001 | 2.06x | 4.2x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 397.0 | 406,571 | 18,572 | 109,300 | 268.8 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 157.3 | 97,140 | 1,696.6 | 0.999 | 2.52x | 4.8x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x397` | 323,555 | 64.5 | 264,026 | 71,444 | 65,283 | 247.3 | `compute` | `b200_sxm-x202-nvl72-hybrid` | 50.1 | 55,389 | 625.8 | 1.001 | 1.29x | 2.5x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12` | 554,700 | 100.4 | 411,375 | 18,572 | 114,595 | 278.6 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 71.9 | 97,140 | 773.7 | 0.999 | 1.40x | 2.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x256` | 208,640 | array | SRAM | 1 |
| 2-4 | `ROM-N5-native-HBMKV-array-hw-tensor-x299` | 243,685 | array | HBM | 53,808 |
| 8-16 | `ROM-N5-native-HBMKV-wafer-hybrid-x6` | 277,350 | wafer | HBM | 9,286 |
| 32-64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 322,740 | array | HBM | 71,265 |
| 256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x397` | 323,555 | array | HBM | 71,444 |
| 1024-4096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x397` | 323,555 | array | HBM | 71,444 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Kimi-K3 | HBM | rom | 284, 299, 338, 340, 383, 396, 397 |
| Kimi-K3 | HBM | sram | 284, 299, 338, 340, 383, 396, 397 |
| Kimi-K3 | SRAM | rom | 256, 259, 272, 273, 313, 340, 375 |
| Kimi-K3 | SRAM | sram | 256, 259, 272, 273, 313, 340, 375 |

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

- **258 of 3,039 feasible points (8.5%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 258.
- By area class: large array (5,000-40,000 mm2) 14, wafer (>=40,000 mm2) 244.
- By KV store: hbm 258.
- By batch: B=1 21, B=2 21, B=4 21, B=8 21, B=16 21, B=32 21, B=64 23, B=256 27, B=1024 41, B=4096 41.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 43% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 59 | 14 | 81.8% | 100.0% | 0.625 | 43% |
| gpu | wafer (>=40,000 mm2) | 1,360 | 244 | 53.3% | 100.0% | 0.625 | 66% |
| rom | wafer (>=40,000 mm2) | 1,620 | 0 | 22.9% | 95.4% | 0.477 | 75% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `Kimi-K3/b200_sxm-x24-pipeline` | Kimi-K3 | 4096 | 38,400 | hbm | 1.103x | 24,000.0 / 24,000.0 W | 35% | 3.5 | 3.9 |
| `Kimi-K3/b200_sxm-x29-pipeline` | Kimi-K3 | 4096 | 46,400 | hbm | 1.096x | 29,000.0 / 29,000.0 W | 35% | 3.7 | 4.1 |
| `Kimi-K3/b200_sxm-x29-hybrid` | Kimi-K3 | 4096 | 46,400 | hbm | 1.081x | 29,000.0 / 29,000.0 W | 35% | 14.3 | 15.5 |
| `Kimi-K3/b200_sxm-x58-pipeline` | Kimi-K3 | 4096 | 92,800 | hbm | 1.078x | 58,000.0 / 58,000.0 W | 35% | 4.9 | 5.3 |
| `Kimi-K3/b200_sxm-x65-pipeline` | Kimi-K3 | 4096 | 104,000 | hbm | 1.076x | 65,000.0 / 65,000.0 W | 35% | 5.2 | 5.6 |
| `Kimi-K3/b200_sxm-x24-hybrid` | Kimi-K3 | 4096 | 38,400 | hbm | 1.076x | 24,000.0 / 24,000.0 W | 35% | 13.6 | 14.6 |
| `Kimi-K3/b200_sxm-x72-pipeline` | Kimi-K3 | 4096 | 115,200 | hbm | 1.075x | 72,000.0 / 72,000.0 W | 35% | 5.5 | 5.9 |
| `Kimi-K3/b200_sxm-x24-pipeline` | Kimi-K3 | 1024 | 38,400 | hbm | 1.073x | 24,000.0 / 24,000.0 W | 35% | 6.5 | 7.0 |
| `Kimi-K3/b200_sxm-x87-pipeline` | Kimi-K3 | 4096 | 139,200 | hbm | 1.072x | 87,000.0 / 87,000.0 W | 35% | 6.1 | 6.6 |
| `Kimi-K3/b200_sxm-x29-pipeline` | Kimi-K3 | 1024 | 46,400 | hbm | 1.071x | 29,000.0 / 29,000.0 W | 35% | 7.3 | 7.8 |
| `Kimi-K3/b200_sxm-x116-pipeline` | Kimi-K3 | 4096 | 185,600 | hbm | 1.069x | 116,000.0 / 116,000.0 W | 35% | 7.3 | 7.8 |
| `Kimi-K3/b200_sxm-x130-pipeline` | Kimi-K3 | 4096 | 208,000 | hbm | 1.068x | 130,000.0 / 130,000.0 W | 35% | 7.9 | 8.4 |

The worst point's dynamic energy is weight read 84.9%, kv read 9.8%, arithmetic 5.1%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| Kimi-K3 | 1 | 208,640 | `Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x256` | 5.044733 | 12,943.4 | link_latency | `Kimi-K3/b200_sxm-x130-nvl72-hybrid` | 51.591580 | 81,381.2 | link_latency | 10.23x |
| Kimi-K3 | 2 | 243,685 | `Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x299` | 3.895076 | 19,332.6 | link_latency | `Kimi-K3/b200_sxm-x152-nvl72-hybrid` | 38.739504 | 101,379.6 | link_latency | 9.95x |
| Kimi-K3 | 4 | 277,350 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x6` | 2.248979 | 22,338.9 | link_latency | `Kimi-K3/b200_sxm-x173-nvl72-hybrid` | 25.023461 | 113,276.6 | link_latency | 11.13x |
| Kimi-K3 | 8 | 277,350 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x6` | 1.221181 | 22,868.4 | link_latency | `Kimi-K3/b200_sxm-x173-nvl72-hybrid` | 14.715003 | 118,982.2 | link_latency | 12.05x |
| Kimi-K3 | 16 | 322,740 | `Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 0.984829 | 69,026.0 | compute | `Kimi-K3/b200_sxm-x202-nvl72-hybrid` | 9.825456 | 143,059.8 | weight_read | 9.98x |
| Kimi-K3 | 32 | 322,740 | `Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 0.572116 | 69,026.0 | compute | `Kimi-K3/b200_sxm-x202-nvl72-hybrid` | 6.927408 | 154,265.3 | weight_read | 12.11x |
| Kimi-K3 | 64 | 322,740 | `Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 0.365759 | 69,026.0 | compute | `Kimi-K3/b200_sxm-x202-nvl72-hybrid` | 5.238990 | 164,389.0 | weight_read | 14.32x |
| Kimi-K3 | 256 | 322,740 | `Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396` | 0.263638 | 66,073.2 | compute | `Kimi-K3/b200_sxm-x202-nvl72-hybrid` | 2.894064 | 171,085.7 | weight_read | 9.51x |
| Kimi-K3 | 1024 | 554,700 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.268833 | 109,299.7 | kv_read | `Kimi-K3/b200_sxm-x347-nvl72-hybrid` | 1.696603 | 273,321.2 | weight_read | 4.83x |
| Kimi-K3 | 4096 | 554,700 | `Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12` | 0.278565 | 114,594.6 | kv_read | `Kimi-K3/b200_sxm-x347-nvl72-hybrid` | 0.773675 | 227,835.6 | link_latency | 2.61x |

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
| Kimi-K3 | 8,192 | 2,800 B | 1,560.9 GB | 4.46 | 0.563 GB | 0.563 GB | 243.5 |

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
| Kimi-K3 | 6 | 277,350 | 22,559.3 | wafer-pipeline | 2,398.2 | wafer-hybrid | 9.41x | 3,481.9 | pipeline | 1,167.1 | hybrid | 2.98x | 6.48x | 2.05x | 0.32x |
| Kimi-K3 | 8 | 369,800 | 23,338.7 | wafer-pipeline | 2,406.4 | wafer-hybrid | 9.70x | 3,923.1 | pipeline | 1,164.7 | hybrid | 3.37x | 5.95x | 2.07x | 0.35x |
| Kimi-K3 | 12 | 554,700 | 24,017.3 | wafer-pipeline | 2,404.0 | wafer-hybrid | 9.99x | 4,490.5 | pipeline | 1,251.5 | hybrid | 3.59x | 5.35x | 1.92x | 0.36x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.32x to 0.36x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Kimi-K3 | 1 | fastest | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x299 | 243,685 | 2,625.5 | 2,625.5 | link_latency | Kimi-K3/b200_sxm-x152-nvl72-hybrid | 243,200 | 1.00x | hybrid | 459.80 | 1,101.5 | 3,304.5 | link_latency | 2.38x | 0.39x | 58.85x | 2.38x |
| Kimi-K3 | 1 | smallest silicon | Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x256 | 208,640 | 2,565.7 | 2,565.7 | link_latency | Kimi-K3/b200_sxm-x130-nvl72-hybrid | 208,000 | 1.00x | hybrid | 457.48 | 1,230.2 | 2,460.4 | link_latency | 2.09x | 0.44x | 57.51x | 2.09x |
| Kimi-K3 | 2 | fastest | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x299 | 243,685 | 2,481.7 | 4,963.4 | link_latency | Kimi-K3/b200_sxm-x152-nvl72-hybrid | 243,200 | 1.00x | hybrid | 459.80 | 1,101.5 | 3,304.5 | link_latency | 2.25x | 0.73x | 55.63x | 2.25x |
| Kimi-K3 | 2 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x284 | 231,460 | 2,295.5 | 4,591.1 | link_latency | Kimi-K3/b200_sxm-x145-nvl72-hybrid | 232,000 | 1.00x | hybrid | 459.80 | 1,077.4 | 3,232.2 | link_latency | 2.13x | 0.71x | 51.45x | 2.13x |
| Kimi-K3 | 4 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x7 | 323,575 | 2,407.0 | 16,848.9 | link_latency | Kimi-K3/b200_sxm-x202-nvl72-hybrid | 323,200 | 1.00x | hybrid | 462.91 | 1,208.9 | 4,835.6 | link_latency | 1.99x | 1.87x | 53.95x | 1.99x |
| Kimi-K3 | 4 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x284 | 231,460 | 1,951.5 | 7,805.9 | link_latency | Kimi-K3/b200_sxm-x145-nvl72-hybrid | 232,000 | 1.00x | hybrid | 462.91 | 1,042.2 | 4,168.8 | link_latency | 1.87x | 1.21x | 43.74x | 1.87x |
| Kimi-K3 | 8 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 2,406.4 | 19,251.1 | link_latency | Kimi-K3/b200_sxm-x231-nvl72-hybrid | 369,600 | 1.00x | hybrid | 471.74 | 1,065.3 | 8,522.0 | link_latency | 2.26x | 1.87x | 53.94x | 2.26x |
| Kimi-K3 | 8 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x284 | 231,460 | 1,501.4 | 12,011.1 | link_latency | Kimi-K3/b200_sxm-x145-nvl72-hybrid | 232,000 | 1.00x | hybrid | 475.36 | 923.1 | 7,384.9 | weight_read | 1.63x | 1.63x | 33.65x | 1.63x |
| Kimi-K3 | 16 | fastest | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 2,381.2 | 235,740.6 | compute | Kimi-K3/b200_sxm-x202-nvl72-hybrid | 323,200 | 1.00x | hybrid | 500.26 | 910.0 | 14,560.1 | weight_read | 2.62x | 16.19x | 53.38x | 2.62x |
| Kimi-K3 | 16 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x284 | 231,460 | 1,027.4 | 16,439.2 | compute | Kimi-K3/b200_sxm-x145-nvl72-hybrid | 232,000 | 1.00x | hybrid | 500.26 | 755.7 | 12,090.9 | weight_read | 1.36x | 1.36x | 23.03x | 1.36x |
| Kimi-K3 | 32 | fastest | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 2,381.2 | 235,740.6 | compute | Kimi-K3/b200_sxm-x202-nvl72-hybrid | 323,200 | 1.00x | hybrid | 550.07 | 695.9 | 22,268.8 | weight_read | 3.42x | 10.59x | 53.38x | 3.42x |
| Kimi-K3 | 32 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x284 | 231,460 | 629.8 | 20,154.3 | compute | Kimi-K3/b200_sxm-x145-nvl72-hybrid | 232,000 | 1.00x | hybrid | 550.07 | 563.5 | 18,030.9 | weight_read | 1.12x | 1.12x | 14.12x | 1.12x |
| Kimi-K3 | 64 | fastest | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 2,381.2 | 235,740.6 | compute | Kimi-K3/b200_sxm-x202-nvl72-hybrid | 323,200 | 1.00x | hybrid | 649.68 | 490.3 | 31,378.0 | weight_read | 4.86x | 7.51x | 53.38x | 4.86x |
| Kimi-K3 | 64 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x284 | 231,460 | 425.6 | 30,217.5 | compute | Kimi-K3/b200_sxm-x145-nvl72-hybrid | 232,000 | 1.00x | hybrid | 649.68 | 388.3 | 24,853.0 | weight_read | 1.10x | 1.22x | 9.54x | 1.10x |
| Kimi-K3 | 256 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 992.7 | 254,143.1 | kv_read | Kimi-K3/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 962.00 | 304.0 | 77,811.4 | weight_read | 3.27x | 3.27x | 22.25x | 3.27x |
| Kimi-K3 | 256 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x284 | 231,460 | 119.5 | 30,579.2 | compute | Kimi-K3/b200_sxm-x145-nvl72-hybrid | 232,000 | 1.00x | hybrid | 1,247.33 | 180.8 | 46,280.0 | weight_read | 0.66x | 0.66x | 3.08x | 0.66x |
| Kimi-K3 | 1024 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 397.0 | 406,571.5 | kv_read | Kimi-K3/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 2,484.45 | 157.3 | 161,099.1 | weight_read | 2.52x | 2.52x | 12.24x | 2.52x |
| Kimi-K3 | 1024 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x284 | 231,460 | 30.0 | 30,718.0 | compute | Kimi-K3/b200_sxm-x145-nvl72-hybrid | 232,000 | 1.00x | hybrid | 3,637.94 | 102.8 | 105,220.3 | weight_read | 0.29x | 0.29x | 1.43x | 0.29x |
| Kimi-K3 | 4096 | fastest | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 100.4 | 411,375.0 | kv_read | Kimi-K3/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 8,574.23 | 71.9 | 294,485.0 | link_latency | 1.40x | 1.40x | 6.60x | 1.40x |
| Kimi-K3 | 4096 | smallest silicon | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x284 | 231,460 | 7.5 | 30,739.2 | compute | Kimi-K3/b200_sxm-x145-nvl72-hybrid | 232,000 | 1.00x | hybrid | 13,200.37 | 44.2 | 181,135.0 | link_latency | 0.17x | 0.17x | 0.89x | 0.17x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| Kimi-K3 | 24 | 38,400 | 454.92 | 454.92 | 729.9 | 729.9 |
| Kimi-K3 | 29 | 46,400 | 454.98 | 454.98 | 821.6 | 821.6 |
| Kimi-K3 | 58 | 92,800 | 455.14 | 455.14 | 1,176.4 | 1,176.4 |
| Kimi-K3 | 65 | 104,000 | 455.15 | 455.15 | 1,233.8 | 1,233.8 |
| Kimi-K3 | 72 | 115,200 | 455.16 | 455.16 | 1,284.2 | 1,284.2 |
| Kimi-K3 | 87 | 139,200 | 457.48 | 457.48 | 1,025.9 | 1,025.9 |
| Kimi-K3 | 116 | 185,600 | 457.48 | 457.48 | 1,173.2 | 1,173.2 |
| Kimi-K3 | 130 | 208,000 | 457.48 | 457.48 | 1,230.2 | 1,230.2 |
| Kimi-K3 | 132 | 211,200 | 457.48 | 457.48 | 1,237.8 | 1,237.8 |
| Kimi-K3 | 139 | 222,400 | 457.48 | 457.48 | 1,263.2 | 1,263.2 |
| Kimi-K3 | 144 | 230,400 | 457.48 | 457.48 | 1,280.4 | 1,280.4 |
| Kimi-K3 | 145 | 232,000 | 459.80 | 459.80 | 1,077.4 | 1,077.4 |
| Kimi-K3 | 152 | 243,200 | 459.80 | 459.80 | 1,101.5 | 1,101.5 |
| Kimi-K3 | 159 | 254,400 | 459.80 | 459.80 | 1,124.4 | 1,124.4 |
| Kimi-K3 | 172 | 275,200 | 459.80 | 459.80 | 1,164.2 | 1,164.2 |
| Kimi-K3 | 173 | 276,800 | 459.80 | 459.80 | 1,167.1 | 1,167.1 |
| Kimi-K3 | 191 | 305,600 | 459.80 | 459.80 | 1,216.5 | 1,216.5 |
| Kimi-K3 | 195 | 312,000 | 459.80 | 459.80 | 1,226.7 | 1,226.7 |
| Kimi-K3 | 202 | 323,200 | 459.80 | 459.80 | 1,244.1 | 1,244.1 |
| Kimi-K3 | 231 | 369,600 | 462.12 | 462.12 | 1,164.7 | 1,164.7 |
| Kimi-K3 | 347 | 555,200 | 464.43 | 464.43 | 1,251.5 | 1,251.5 |

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
| Kimi-K3 | 24 | 38,400 | 44.6 | 729.9 | 317.6 | tensor | 454.92 | 33.2% | weight_read |
| Kimi-K3 | 29 | 46,400 | 44.6 | 821.6 | 291.9 | tensor | 454.98 | 37.4% | weight_read |
| Kimi-K3 | 58 | 92,800 | 44.6 | 1,176.4 | 291.1 | tensor | 455.14 | 53.5% | link_latency |
| Kimi-K3 | 65 | 104,000 | 44.6 | 1,233.8 | 289.9 | tensor | 455.15 | 56.2% | link_latency |
| Kimi-K3 | 72 | 115,200 | 44.6 | 1,284.2 | 316.2 | tensor | 455.16 | 58.5% | link_latency |
| Kimi-K3 | 87 | 139,200 | 44.6 | 639.9 | 1,025.9 | hybrid | 457.48 | 46.9% | link_latency |
| Kimi-K3 | 116 | 185,600 | 44.6 | 665.9 | 1,173.2 | hybrid | 457.48 | 53.7% | link_latency |
| Kimi-K3 | 130 | 208,000 | 44.6 | 674.8 | 1,230.2 | hybrid | 457.48 | 56.3% | link_latency |
| Kimi-K3 | 132 | 211,200 | 44.6 | 676.0 | 1,237.8 | hybrid | 457.48 | 56.6% | link_latency |
| Kimi-K3 | 139 | 222,400 | 44.6 | 679.7 | 1,263.2 | hybrid | 457.48 | 57.8% | link_latency |
| Kimi-K3 | 144 | 230,400 | 44.6 | 682.2 | 1,280.4 | hybrid | 457.48 | 58.6% | link_latency |
| Kimi-K3 | 145 | 232,000 | 44.6 | 670.4 | 1,077.4 | hybrid | 459.80 | 49.5% | link_latency |
| Kimi-K3 | 152 | 243,200 | 44.6 | 673.5 | 1,101.5 | hybrid | 459.80 | 50.6% | link_latency |
| Kimi-K3 | 159 | 254,400 | 44.6 | 676.3 | 1,124.4 | hybrid | 459.80 | 51.7% | link_latency |
| Kimi-K3 | 172 | 275,200 | 44.6 | 680.9 | 1,164.2 | hybrid | 459.80 | 53.5% | link_latency |
| Kimi-K3 | 173 | 276,800 | 44.6 | 681.3 | 1,167.1 | hybrid | 459.80 | 53.7% | link_latency |
| Kimi-K3 | 191 | 305,600 | 44.6 | 686.7 | 1,216.5 | hybrid | 459.80 | 55.9% | link_latency |
| Kimi-K3 | 195 | 312,000 | 44.6 | 687.8 | 1,226.7 | hybrid | 459.80 | 56.4% | link_latency |
| Kimi-K3 | 202 | 323,200 | 44.6 | 689.6 | 1,244.1 | hybrid | 459.80 | 57.2% | link_latency |
| Kimi-K3 | 231 | 369,600 | 44.6 | 689.5 | 1,164.7 | hybrid | 462.12 | 53.8% | link_latency |
| Kimi-K3 | 347 | 555,200 | 44.6 | 700.6 | 1,251.5 | hybrid | 464.43 | 58.1% | link_latency |

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
| Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x273 | Kimi-K3 | 273 | pipeline | rom_package_ucie | rom_board_serdes | 92 | 3.42 us | 29,235.7 tok/s | 292,356.8 tok/s | 69 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.94 us; 23 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.48 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x256 | Kimi-K3 | 256 | tensor | rom_package_ucie | rom_board_serdes | 372 | 296.03 us | 337.8 tok/s | 3,378.0 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 186 x all_reduce span 64 on rom_board_serdes (traversals 15.4) = 290.81 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x273 | Kimi-K3 | 273 | hybrid | rom_package_ucie | rom_board_serdes | 254 | 12.56 us | 7,960.8 tok/s | 79,608.4 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 68 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 7.34 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x273 | Kimi-K3 | 273 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x5 | Kimi-K3 | 5 | pipeline | on_wafer_n5 | rom_wafer_serdes | 92 | 11.48 us | 8,712.7 tok/s | 87,127.5 tok/s | 91 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 11.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x259 | Kimi-K3 | 259 | tensor | nvlink5 | infiniband_ndr | 372 | 1,364.48 us | 73.3 tok/s | 732.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 33 on infiniband_ndr (traversals 2.0) = 910.30 us |
| Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x5 | Kimi-K3 | 5 | tensor | on_wafer_n5 | rom_wafer_serdes | 372 | 440.96 us | 226.8 tok/s | 2,267.8 tok/s | 186 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 358.05 us; 186 x all_reduce span 5 on rom_wafer_serdes (traversals 4.4) = 82.91 us |
| Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x272 | Kimi-K3 | 272 | hybrid | nvlink5 | infiniband_ndr | 219 | 530.63 us | 188.5 tok/s | 1,884.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 33 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 76.45 us |
| Kimi-K3/ROM-N5-native-SRAMKV-wafer-hybrid-x5 | Kimi-K3 | 5 | hybrid | on_wafer_n5 | rom_wafer_serdes | 190 | 358.46 us | 279.0 tok/s | 2,789.7 tok/s | 186 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 358.05 us; 4 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.41 us |
| Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x397 | Kimi-K3 | 397 | pipeline | rom_package_ucie | rom_board_serdes | 92 | 3.42 us | 29,235.7 tok/s | 292,356.8 tok/s | 69 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.94 us; 23 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.48 us |
| Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x299 | Kimi-K3 | 299 | tensor | rom_package_ucie | rom_board_serdes | 372 | 336.96 us | 296.8 tok/s | 2,967.7 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 186 x all_reduce span 75 on rom_board_serdes (traversals 17.6) = 331.74 us |
| Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396 | Kimi-K3 | 396 | hybrid | rom_package_ucie | rom_board_serdes | 278 | 15.15 us | 6,599.5 tok/s | 65,995.1 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 92 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 9.93 us |
| Kimi-K3/ROM-N5-native-HBMKV-array-pipeline-x396 | Kimi-K3 | 396 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x7 | Kimi-K3 | 7 | pipeline | on_wafer_n5 | rom_wafer_serdes | 92 | 11.48 us | 8,712.7 tok/s | 87,127.5 tok/s | 91 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 11.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| Kimi-K3/ROM-N5-native-HBMKV-array-tensor-x284 | Kimi-K3 | 284 | tensor | nvlink5 | infiniband_ndr | 372 | 1,364.88 us | 73.3 tok/s | 732.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 36 on infiniband_ndr (traversals 2.0) = 910.71 us |
| Kimi-K3/ROM-N5-native-HBMKV-wafer-tensor-x6 | Kimi-K3 | 6 | tensor | on_wafer_n5 | rom_wafer_serdes | 372 | 441.00 us | 226.8 tok/s | 2,267.6 tok/s | 186 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 358.05 us; 186 x all_reduce span 6 on rom_wafer_serdes (traversals 4.4) = 82.95 us |
| Kimi-K3/ROM-N5-native-HBMKV-array-hybrid-x383 | Kimi-K3 | 383 | hybrid | nvlink5 | infiniband_ndr | 233 | 563.06 us | 177.6 tok/s | 1,776.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 47 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 108.89 us |
| Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x6 | Kimi-K3 | 6 | hybrid | on_wafer_n5 | rom_wafer_serdes | 191 | 358.56 us | 278.9 tok/s | 2,788.9 tok/s | 186 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 358.05 us; 5 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.51 us |
| Kimi-K3/b200_sxm-x24-pipeline | Kimi-K3 | 24 | pipeline | nvlink5 | infiniband_ndr | 23 | 30.17 us | 3,314.8 tok/s | 33,147.8 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.53 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x24-tensor | Kimi-K3 | 24 | tensor | nvlink5 | infiniband_ndr | 372 | 1,316.00 us | 76.0 tok/s | 759.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x24-hybrid | Kimi-K3 | 24 | hybrid | nvlink5 | infiniband_ndr | 188 | 458.81 us | 218.0 tok/s | 2,179.5 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x24-nvl72-tensor | Kimi-K3 | 24 | tensor | nvlink5_nvl72 | infiniband_ndr | 186 | 454.92 us | 219.8 tok/s | 2,198.2 tok/s | 186 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 454.92 us |
| Kimi-K3/b200_sxm-x24-expert | Kimi-K3 | 24 | expert | nvlink5 | infiniband_ndr | 372 | 862.13 us | 116.0 tok/s | 1,159.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 448.99 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 413.13 us |
| Kimi-K3/b200_sxm-x24-nvl72-expert | Kimi-K3 | 24 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 680.09 us | 147.0 tok/s | 1,470.4 tok/s | 186 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 454.92 us; 186 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 225.18 us |
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
| Kimi-K3/b200_sxm-x65-pipeline | Kimi-K3 | 65 | pipeline | nvlink5 | infiniband_ndr | 64 | 86.63 us | 1,154.4 tok/s | 11,543.9 tok/s | 56 x point_to_point span 2 on nvlink5 (traversals 1.0) = 68.09 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.53 us |
| Kimi-K3/b200_sxm-x65-tensor | Kimi-K3 | 65 | tensor | nvlink5 | infiniband_ndr | 372 | 1,351.55 us | 74.0 tok/s | 739.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 897.37 us |
| Kimi-K3/b200_sxm-x65-hybrid | Kimi-K3 | 65 | hybrid | nvlink5 | infiniband_ndr | 194 | 472.71 us | 211.5 tok/s | 2,115.5 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.53 us |
| Kimi-K3/b200_sxm-x65-nvl72-tensor | Kimi-K3 | 65 | tensor | nvlink5_nvl72 | infiniband_ndr | 186 | 455.15 us | 219.7 tok/s | 2,197.1 tok/s | 186 x all_reduce span 65 on nvlink5_nvl72 (traversals 2.0) = 455.15 us |
| Kimi-K3/b200_sxm-x65-expert | Kimi-K3 | 65 | expert | nvlink5 | infiniband_ndr | 372 | 838.08 us | 119.3 tok/s | 1,193.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 447.37 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 390.71 us |
| Kimi-K3/b200_sxm-x65-nvl72-expert | Kimi-K3 | 65 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 679.08 us | 147.3 tok/s | 1,472.6 tok/s | 186 x all_reduce span 65 on nvlink5_nvl72 (traversals 2.0) = 455.15 us; 186 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 223.93 us |
| Kimi-K3/b200_sxm-x72-pipeline | Kimi-K3 | 72 | pipeline | nvlink5 | infiniband_ndr | 71 | 95.14 us | 1,051.1 tok/s | 10,511.1 tok/s | 63 x point_to_point span 2 on nvlink5 (traversals 1.0) = 76.60 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.53 us |
| Kimi-K3/b200_sxm-x72-tensor | Kimi-K3 | 72 | tensor | nvlink5 | infiniband_ndr | 372 | 1,351.55 us | 74.0 tok/s | 739.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 897.37 us |
| Kimi-K3/b200_sxm-x72-hybrid | Kimi-K3 | 72 | hybrid | nvlink5 | infiniband_ndr | 194 | 472.71 us | 211.5 tok/s | 2,115.5 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.53 us |
| Kimi-K3/b200_sxm-x72-nvl72-tensor | Kimi-K3 | 72 | tensor | nvlink5_nvl72 | infiniband_ndr | 186 | 455.16 us | 219.7 tok/s | 2,197.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us |
| Kimi-K3/b200_sxm-x72-expert | Kimi-K3 | 72 | expert | nvlink5 | infiniband_ndr | 372 | 836.70 us | 119.5 tok/s | 1,195.2 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 447.26 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 389.43 us |
| Kimi-K3/b200_sxm-x72-nvl72-expert | Kimi-K3 | 72 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 679.02 us | 147.3 tok/s | 1,472.7 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 223.86 us |
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
| Kimi-K3/b200_sxm-x130-pipeline | Kimi-K3 | 130 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x130-tensor | Kimi-K3 | 130 | tensor | nvlink5 | infiniband_ndr | 372 | 1,359.92 us | 73.5 tok/s | 735.3 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 905.74 us |
| Kimi-K3/b200_sxm-x130-hybrid | Kimi-K3 | 130 | hybrid | nvlink5 | infiniband_ndr | 202 | 491.24 us | 203.6 tok/s | 2,035.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 37.07 us |
| Kimi-K3/b200_sxm-x130-nvl72-tensor | Kimi-K3 | 130 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,290.32 us | 77.5 tok/s | 775.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 835.15 us |
| Kimi-K3/b200_sxm-x130-nvl72-hybrid | Kimi-K3 | 130 | hybrid | nvlink5_nvl72 | infiniband_ndr | 187 | 457.48 us | 218.6 tok/s | 2,185.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| Kimi-K3/b200_sxm-x130-expert | Kimi-K3 | 130 | expert | nvlink5 | infiniband_ndr | 372 | 831.03 us | 120.3 tok/s | 1,203.3 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.89 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 384.14 us |
| Kimi-K3/b200_sxm-x130-nvl72-expert | Kimi-K3 | 130 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 839.31 us | 119.1 tok/s | 1,191.5 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 384.14 us |
| Kimi-K3/b200_sxm-x132-pipeline | Kimi-K3 | 132 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x132-tensor | Kimi-K3 | 132 | tensor | nvlink5 | infiniband_ndr | 372 | 1,359.92 us | 73.5 tok/s | 735.3 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 905.74 us |
| Kimi-K3/b200_sxm-x132-hybrid | Kimi-K3 | 132 | hybrid | nvlink5 | infiniband_ndr | 202 | 491.24 us | 203.6 tok/s | 2,035.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 37.07 us |
| Kimi-K3/b200_sxm-x132-nvl72-tensor | Kimi-K3 | 132 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,290.32 us | 77.5 tok/s | 775.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 835.15 us |
| Kimi-K3/b200_sxm-x132-nvl72-hybrid | Kimi-K3 | 132 | hybrid | nvlink5_nvl72 | infiniband_ndr | 187 | 457.48 us | 218.6 tok/s | 2,185.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| Kimi-K3/b200_sxm-x132-expert | Kimi-K3 | 132 | expert | nvlink5 | infiniband_ndr | 372 | 830.93 us | 120.3 tok/s | 1,203.5 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.89 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 384.04 us |
| Kimi-K3/b200_sxm-x132-nvl72-expert | Kimi-K3 | 132 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 839.21 us | 119.2 tok/s | 1,191.6 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 384.04 us |
| Kimi-K3/b200_sxm-x139-pipeline | Kimi-K3 | 139 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x139-tensor | Kimi-K3 | 139 | tensor | nvlink5 | infiniband_ndr | 372 | 1,360.44 us | 73.5 tok/s | 735.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 18 on infiniband_ndr (traversals 2.0) = 906.26 us |
| Kimi-K3/b200_sxm-x139-hybrid | Kimi-K3 | 139 | hybrid | nvlink5 | infiniband_ndr | 203 | 493.56 us | 202.6 tok/s | 2,026.1 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 17 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 39.38 us |
| Kimi-K3/b200_sxm-x139-nvl72-tensor | Kimi-K3 | 139 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,290.32 us | 77.5 tok/s | 775.0 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 835.15 us |
| Kimi-K3/b200_sxm-x139-nvl72-hybrid | Kimi-K3 | 139 | hybrid | nvlink5_nvl72 | infiniband_ndr | 187 | 457.48 us | 218.6 tok/s | 2,185.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| Kimi-K3/b200_sxm-x139-expert | Kimi-K3 | 139 | expert | nvlink5 | infiniband_ndr | 372 | 830.58 us | 120.4 tok/s | 1,204.0 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.86 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 383.72 us |
| Kimi-K3/b200_sxm-x139-nvl72-expert | Kimi-K3 | 139 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 838.88 us | 119.2 tok/s | 1,192.1 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 383.72 us |
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
| Kimi-K3/b200_sxm-x191-pipeline | Kimi-K3 | 191 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x191-tensor | Kimi-K3 | 191 | tensor | nvlink5 | infiniband_ndr | 372 | 1,362.66 us | 73.4 tok/s | 733.9 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 24 on infiniband_ndr (traversals 2.0) = 908.48 us |
| Kimi-K3/b200_sxm-x191-hybrid | Kimi-K3 | 191 | hybrid | nvlink5 | infiniband_ndr | 209 | 507.46 us | 197.1 tok/s | 1,970.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 23 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 53.28 us |
| Kimi-K3/b200_sxm-x191-nvl72-tensor | Kimi-K3 | 191 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x191-nvl72-hybrid | Kimi-K3 | 191 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x191-expert | Kimi-K3 | 191 | expert | nvlink5 | infiniband_ndr | 372 | 828.79 us | 120.7 tok/s | 1,206.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.74 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.05 us |
| Kimi-K3/b200_sxm-x191-nvl72-expert | Kimi-K3 | 191 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 832.83 us | 120.1 tok/s | 1,200.7 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 382.05 us |
| Kimi-K3/b200_sxm-x195-pipeline | Kimi-K3 | 195 | pipeline | nvlink5 | infiniband_ndr | 92 | 123.97 us | 806.6 tok/s | 8,066.2 tok/s | 81 x point_to_point span 2 on nvlink5 (traversals 1.0) = 98.49 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| Kimi-K3/b200_sxm-x195-tensor | Kimi-K3 | 195 | tensor | nvlink5 | infiniband_ndr | 372 | 1,362.93 us | 73.4 tok/s | 733.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 186 x all_reduce span 25 on infiniband_ndr (traversals 2.0) = 908.75 us |
| Kimi-K3/b200_sxm-x195-hybrid | Kimi-K3 | 195 | hybrid | nvlink5 | infiniband_ndr | 210 | 509.78 us | 196.2 tok/s | 1,961.6 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 454.18 us; 24 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 55.60 us |
| Kimi-K3/b200_sxm-x195-nvl72-tensor | Kimi-K3 | 195 | tensor | nvlink5_nvl72 | infiniband_ndr | 372 | 1,316.98 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 186 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 861.82 us |
| Kimi-K3/b200_sxm-x195-nvl72-hybrid | Kimi-K3 | 195 | hybrid | nvlink5_nvl72 | infiniband_ndr | 188 | 459.80 us | 217.5 tok/s | 2,174.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 455.16 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.63 us |
| Kimi-K3/b200_sxm-x195-expert | Kimi-K3 | 195 | expert | nvlink5 | infiniband_ndr | 372 | 828.68 us | 120.7 tok/s | 1,206.7 tok/s | 186 x all_reduce span 8 on nvlink5 (traversals 2.0) = 446.72 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.96 us |
| Kimi-K3/b200_sxm-x195-nvl72-expert | Kimi-K3 | 195 | expert | nvlink5_nvl72 | infiniband_ndr | 372 | 832.74 us | 120.1 tok/s | 1,200.9 tok/s | 186 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 450.78 us; 186 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 381.96 us |
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

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Kimi-K3 | 1 | array | array | Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x256 | 208,640 | 2,565.7 | 0.012 | 2,565.7 (208,640) | 2,398.2 (277,350) | 0.93x | link_latency |
| Kimi-K3 | 2 | array | array | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x299 | 243,685 | 2,481.7 | 0.010 | 2,481.7 (243,685) | 2,398.2 (277,350) | 0.97x | link_latency |
| Kimi-K3 | 4 | wafer | array | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 2,398.2 | 0.009 | 2,271.2 (312,145) | 2,398.2 (277,350) | 1.06x | link_latency |
| Kimi-K3 | 8 | wafer | wafer | Kimi-K3/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 2,340.8 | 0.008 | 2,381.2 (322,740) | 2,340.8 (277,350) | 0.98x | link_latency |
| Kimi-K3 | 16 | array | wafer | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 2,381.2 | 0.007 | 2,381.2 (322,740) | 2,249.0 (369,800) | 0.94x | compute |
| Kimi-K3 | 32 | array | array | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 2,381.2 | 0.007 | 2,381.2 (322,740) | 2,153.1 (554,700) | 0.90x | compute |
| Kimi-K3 | 64 | array | array | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 2,381.2 | 0.007 | 2,381.2 (322,740) | 1,845.0 (554,700) | 0.77x | compute |
| Kimi-K3 | 256 | array | array | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 979.0 | 0.003 | 979.0 (322,740) | 992.7 (554,700) | 1.01x | compute |
| Kimi-K3 | 1024 | wafer | array | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 397.0 | 0.001 | 254.3 (322,740) | 397.0 (554,700) | 1.56x | kv_read |
| Kimi-K3 | 4096 | wafer | array | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 100.4 | 0.000 | 64.0 (322,740) | 100.4 (554,700) | 1.57x | kv_read |

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
| Kimi-K3 | 1 | sram | 292,520.0 | 25,964.4 | 25,964.4 | 11.27x | 1.00x | weight_read | weight_read | weight_read |
| Kimi-K3 | 2 | sram | 292,520.0 | 25,964.4 | 25,964.4 | 11.27x | 1.00x | weight_read | weight_read | weight_read |
| Kimi-K3 | 4 | sram | 292,520.0 | 25,964.4 | 25,964.4 | 11.27x | 1.00x | weight_read | weight_read | weight_read |
| Kimi-K3 | 8 | sram | 292,520.0 | 25,964.4 | 25,964.4 | 11.27x | 1.00x | weight_read | weight_read | weight_read |
| Kimi-K3 | 16 | sram | 292,520.0 | 25,964.4 | 35,887.5 | 11.27x | 1.38x | weight_read | weight_read | link_latency |
| Kimi-K3 | 32 | sram | 292,520.0 | 25,964.4 | 55,219.4 | 11.27x | 2.13x | weight_read | weight_read | link_latency |
| Kimi-K3 | 64 | sram | 292,520.0 | 25,964.4 | 91,033.1 | 11.27x | 3.51x | weight_read | weight_read | link_latency |
| Kimi-K3 | 256 | sram | 292,520.0 | 26,029.5 | 115,729.4 | 11.24x | 4.45x | weight_read | weight_read | link_latency |
| Kimi-K3 | 1024 | sram | 402,755.7 | 26,090.6 | 206,721.0 | 15.44x | 7.92x | weight_read | weight_read | weight_read |
| Kimi-K3 | 4096 | sram | 411,375.0 | 26,106.6 | 372,057.7 | 15.76x | 14.25x | kv_read | weight_read | weight_read |
| Kimi-K3 | 1 | rom | 403,408.0 | 34,043.2 | 34,043.2 | 11.85x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 2 | rom | 403,408.0 | 34,043.2 | 34,043.2 | 11.85x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 4 | rom | 403,408.0 | 34,043.2 | 34,043.2 | 11.85x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 8 | rom | 403,408.0 | 34,043.2 | 34,043.2 | 11.85x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 16 | rom | 403,408.0 | 34,043.2 | 35,944.0 | 11.85x | 1.06x | kv_read | weight_read | link_latency |
| Kimi-K3 | 32 | rom | 403,408.0 | 34,043.2 | 55,309.5 | 11.85x | 1.62x | kv_read | weight_read | link_latency |
| Kimi-K3 | 64 | rom | 403,408.0 | 34,043.2 | 77,417.4 | 11.85x | 2.27x | kv_read | weight_read | link_latency |
| Kimi-K3 | 256 | rom | 403,408.0 | 34,131.7 | 115,882.4 | 11.82x | 3.40x | kv_read | weight_read | link_latency |
| Kimi-K3 | 1024 | rom | 406,571.5 | 34,266.1 | 207,659.6 | 11.87x | 6.06x | kv_read | weight_read | weight_read |
| Kimi-K3 | 4096 | rom | 411,375.0 | 34,299.8 | 374,258.7 | 11.99x | 10.91x | kv_read | weight_read | weight_read |

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
| Kimi-K3 | 1 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 292,520.0 | 0.527 | weight_read | 1.00x |
| Kimi-K3 | 1 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.56 | 1.00 | 403,408.0 | 0.727 | kv_read | 1.38x |
| Kimi-K3 | 1 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perstream | 115,730 | 1.00 | 1.00 | 25,964.4 | 0.224 | weight_read | 0.09x |
| Kimi-K3 | 1 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.31 | 1.00 | 34,043.2 | 0.245 | weight_read | 0.12x |
| Kimi-K3 | 1 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perregion | 115,730 | 1.00 | 1.00 | 25,964.4 | 0.224 | weight_read | 0.09x |
| Kimi-K3 | 1 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 1.31 | 1.00 | 34,043.2 | 0.245 | weight_read | 0.12x |
| Kimi-K3 | 2 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 292,520.0 | 0.527 | weight_read | 1.00x |
| Kimi-K3 | 2 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.56 | 1.00 | 403,408.0 | 0.727 | kv_read | 1.38x |
| Kimi-K3 | 2 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perstream | 115,730 | 1.00 | 1.00 | 25,964.4 | 0.224 | weight_read | 0.09x |
| Kimi-K3 | 2 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.31 | 1.00 | 34,043.2 | 0.245 | weight_read | 0.12x |
| Kimi-K3 | 2 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perregion | 115,730 | 1.00 | 1.00 | 25,964.4 | 0.224 | weight_read | 0.09x |
| Kimi-K3 | 2 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 1.31 | 1.00 | 34,043.2 | 0.245 | weight_read | 0.12x |
| Kimi-K3 | 4 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 292,520.0 | 0.527 | weight_read | 1.00x |
| Kimi-K3 | 4 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.56 | 1.00 | 403,408.0 | 0.727 | kv_read | 1.38x |
| Kimi-K3 | 4 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perstream | 115,730 | 1.00 | 1.00 | 25,964.4 | 0.224 | weight_read | 0.09x |
| Kimi-K3 | 4 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.31 | 1.00 | 34,043.2 | 0.245 | weight_read | 0.12x |
| Kimi-K3 | 4 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perregion | 115,730 | 1.00 | 1.00 | 25,964.4 | 0.224 | weight_read | 0.09x |
| Kimi-K3 | 4 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 1.31 | 1.00 | 34,043.2 | 0.245 | weight_read | 0.12x |
| Kimi-K3 | 8 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 292,520.0 | 0.527 | weight_read | 1.00x |
| Kimi-K3 | 8 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.56 | 1.00 | 403,408.0 | 0.727 | kv_read | 1.38x |
| Kimi-K3 | 8 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perstream | 115,730 | 1.00 | 1.00 | 25,964.4 | 0.224 | weight_read | 0.09x |
| Kimi-K3 | 8 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.31 | 1.00 | 34,043.2 | 0.245 | weight_read | 0.12x |
| Kimi-K3 | 8 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perregion | 115,730 | 1.00 | 1.00 | 25,964.4 | 0.224 | weight_read | 0.09x |
| Kimi-K3 | 8 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 1.31 | 1.00 | 34,043.2 | 0.245 | weight_read | 0.12x |
| Kimi-K3 | 16 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 292,520.0 | 0.527 | weight_read | 1.00x |
| Kimi-K3 | 16 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.56 | 1.00 | 403,408.0 | 0.727 | kv_read | 1.38x |
| Kimi-K3 | 16 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perstream | 115,730 | 1.00 | 1.00 | 25,964.4 | 0.224 | weight_read | 0.09x |
| Kimi-K3 | 16 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.31 | 1.00 | 34,043.2 | 0.245 | weight_read | 0.12x |
| Kimi-K3 | 16 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x142-perregion | 115,730 | 1.00 | 3.05 | 35,887.5 | 0.310 | link_latency | 0.12x |
| Kimi-K3 | 16 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x142-perregion-romfill | 115,730 | 1.01 | 3.05 | 35,944.0 | 0.311 | link_latency | 0.12x |
| Kimi-K3 | 32 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 292,520.0 | 0.527 | weight_read | 1.00x |
| Kimi-K3 | 32 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.56 | 1.00 | 403,408.0 | 0.727 | kv_read | 1.38x |
| Kimi-K3 | 32 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perstream | 115,730 | 1.00 | 1.00 | 25,964.4 | 0.224 | weight_read | 0.09x |
| Kimi-K3 | 32 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.31 | 1.00 | 34,043.2 | 0.245 | weight_read | 0.12x |
| Kimi-K3 | 32 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x142-perregion | 115,730 | 1.00 | 4.10 | 55,219.4 | 0.477 | link_latency | 0.19x |
| Kimi-K3 | 32 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x142-perregion-romfill | 115,730 | 1.01 | 4.10 | 55,309.5 | 0.478 | link_latency | 0.19x |
| Kimi-K3 | 64 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 292,520.0 | 0.527 | weight_read | 1.00x |
| Kimi-K3 | 64 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.56 | 1.00 | 403,408.0 | 0.727 | kv_read | 1.38x |
| Kimi-K3 | 64 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perstream | 115,730 | 1.00 | 1.00 | 25,964.4 | 0.224 | weight_read | 0.09x |
| Kimi-K3 | 64 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.31 | 1.00 | 34,043.2 | 0.245 | weight_read | 0.12x |
| Kimi-K3 | 64 | per_region | sram | Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x3-perregion | 138,675 | 1.00 | 5.73 | 91,033.1 | 0.656 | link_latency | 0.31x |
| Kimi-K3 | 64 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x142-perregion-romfill | 115,730 | 1.01 | 5.73 | 77,417.4 | 0.669 | link_latency | 0.26x |
| Kimi-K3 | 256 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 292,520.0 | 0.527 | weight_read | 1.00x |
| Kimi-K3 | 256 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.56 | 1.00 | 403,408.0 | 0.727 | kv_read | 1.38x |
| Kimi-K3 | 256 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perstream | 115,730 | 1.00 | 1.80 | 26,029.5 | 0.225 | weight_read | 0.09x |
| Kimi-K3 | 256 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.31 | 1.50 | 34,131.7 | 0.246 | weight_read | 0.12x |
| Kimi-K3 | 256 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x142-perregion | 115,730 | 1.00 | 12.69 | 115,729.4 | 1.000 | link_latency | 0.40x |
| Kimi-K3 | 256 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-array-hw-tensor-x142-perregion-romfill | 115,730 | 1.01 | 12.69 | 115,882.4 | 1.001 | link_latency | 0.40x |
| Kimi-K3 | 1024 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 402,755.7 | 0.726 | weight_read | 1.00x |
| Kimi-K3 | 1024 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.56 | 1.00 | 406,571.5 | 0.733 | kv_read | 1.01x |
| Kimi-K3 | 1024 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-pipeline-x142-perstream | 115,730 | 1.00 | 7.21 | 26,090.6 | 0.225 | weight_read | 0.06x |
| Kimi-K3 | 1024 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.31 | 5.99 | 34,266.1 | 0.247 | weight_read | 0.09x |
| Kimi-K3 | 1024 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hybrid-x142-perregion | 115,730 | 1.00 | 5.40 | 206,721.0 | 1.786 | weight_read | 0.51x |
| Kimi-K3 | 1024 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-array-hybrid-x142-perregion-romfill | 115,730 | 1.01 | 5.40 | 207,659.6 | 1.794 | weight_read | 0.52x |
| Kimi-K3 | 4096 | batched | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 411,375.0 | 0.742 | kv_read | 1.00x |
| Kimi-K3 | 4096 | batched | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.56 | 1.00 | 411,375.0 | 0.742 | kv_read | 1.00x |
| Kimi-K3 | 4096 | per_stream | sram | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 23.95 | 26,106.6 | 0.188 | weight_read | 0.06x |
| Kimi-K3 | 4096 | per_stream | rom | Kimi-K3/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.31 | 23.95 | 34,299.8 | 0.247 | weight_read | 0.08x |
| Kimi-K3 | 4096 | per_region | sram | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x142-perregion | 115,730 | 1.00 | 7.81 | 372,057.7 | 3.215 | weight_read | 0.90x |
| Kimi-K3 | 4096 | per_region | rom | Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x142-perregion-romfill | 115,730 | 1.01 | 7.81 | 374,258.7 | 3.234 | weight_read | 0.91x |

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
| Kimi-K3 | 1 | 128 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 2 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 4 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 8 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 16 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 32 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 64 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
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
| Kimi-K3 | 1 | 24 | 11.85 | 6.28 | 1.89x |
| Kimi-K3 | 2 | 24 | 17.78 | 8.20 | 2.17x |
| Kimi-K3 | 4 | 24 | 22.31 | 10.30 | 2.17x |
| Kimi-K3 | 8 | 24 | 23.86 | 12.42 | 1.92x |
| Kimi-K3 | 16 | 24 | 24.00 | 14.39 | 1.67x |
| Kimi-K3 | 32 | 24 | 24.00 | 16.03 | 1.50x |
| Kimi-K3 | 64 | 24 | 24.00 | 17.21 | 1.39x |
| Kimi-K3 | 256 | 24 | 24.00 | 18.11 | 1.33x |
| Kimi-K3 | 1024 | 24 | 24.00 | 18.13 | 1.32x |
| Kimi-K3 | 4096 | 24 | 24.00 | 18.13 | 1.32x |
| Kimi-K3 | 1 | 29 | 12.46 | 6.68 | 1.87x |
| Kimi-K3 | 2 | 29 | 19.47 | 8.87 | 2.19x |
| Kimi-K3 | 4 | 29 | 25.74 | 11.34 | 2.27x |
| Kimi-K3 | 8 | 29 | 28.57 | 13.90 | 2.06x |
| Kimi-K3 | 16 | 29 | 28.99 | 16.33 | 1.78x |
| Kimi-K3 | 32 | 29 | 29.00 | 18.39 | 1.58x |
| Kimi-K3 | 64 | 29 | 29.00 | 19.91 | 1.46x |
| Kimi-K3 | 256 | 29 | 29.00 | 21.07 | 1.38x |
| Kimi-K3 | 1024 | 29 | 29.00 | 21.10 | 1.37x |
| Kimi-K3 | 4096 | 29 | 29.00 | 21.10 | 1.37x |
| Kimi-K3 | 1 | 58 | 14.09 | 8.11 | 1.74x |
| Kimi-K3 | 2 | 58 | 24.59 | 11.50 | 2.14x |
| Kimi-K3 | 4 | 58 | 38.37 | 15.54 | 2.47x |
| Kimi-K3 | 8 | 58 | 50.84 | 20.16 | 2.52x |
| Kimi-K3 | 16 | 58 | 56.83 | 24.95 | 2.28x |
| Kimi-K3 | 32 | 58 | 57.94 | 29.37 | 1.97x |
| Kimi-K3 | 64 | 58 | 58.00 | 32.85 | 1.77x |
| Kimi-K3 | 256 | 58 | 58.00 | 35.61 | 1.63x |
| Kimi-K3 | 1024 | 58 | 58.00 | 35.69 | 1.63x |
| Kimi-K3 | 4096 | 58 | 58.00 | 35.69 | 1.63x |
| Kimi-K3 | 1 | 65 | 14.28 | 8.35 | 1.71x |
| Kimi-K3 | 2 | 65 | 25.25 | 11.95 | 2.11x |
| Kimi-K3 | 4 | 65 | 40.26 | 16.28 | 2.47x |
| Kimi-K3 | 8 | 65 | 54.93 | 21.30 | 2.58x |
| Kimi-K3 | 16 | 65 | 63.00 | 26.60 | 2.37x |
| Kimi-K3 | 32 | 65 | 64.85 | 31.55 | 2.06x |
| Kimi-K3 | 64 | 65 | 65.00 | 35.48 | 1.83x |
| Kimi-K3 | 256 | 65 | 65.00 | 38.63 | 1.68x |
| Kimi-K3 | 1024 | 65 | 65.00 | 38.72 | 1.68x |
| Kimi-K3 | 4096 | 65 | 65.00 | 38.72 | 1.68x |
| Kimi-K3 | 1 | 72 | 14.44 | 8.57 | 1.68x |
| Kimi-K3 | 2 | 72 | 25.79 | 12.35 | 2.09x |
| Kimi-K3 | 4 | 72 | 41.88 | 16.95 | 2.47x |
| Kimi-K3 | 8 | 72 | 58.61 | 22.35 | 2.62x |
| Kimi-K3 | 16 | 72 | 68.88 | 28.13 | 2.45x |
| Kimi-K3 | 32 | 72 | 71.70 | 33.59 | 2.13x |
| Kimi-K3 | 64 | 72 | 71.99 | 37.96 | 1.90x |
| Kimi-K3 | 256 | 72 | 72.00 | 41.51 | 1.73x |
| Kimi-K3 | 1024 | 72 | 72.00 | 41.60 | 1.73x |
| Kimi-K3 | 4096 | 72 | 72.00 | 41.60 | 1.73x |
| Kimi-K3 | 1 | 87 | 14.69 | 8.99 | 1.63x |
| Kimi-K3 | 2 | 87 | 26.70 | 13.07 | 2.04x |
| Kimi-K3 | 4 | 87 | 44.67 | 18.18 | 2.46x |
| Kimi-K3 | 8 | 87 | 65.34 | 24.36 | 2.68x |
| Kimi-K3 | 16 | 87 | 80.50 | 31.08 | 2.59x |
| Kimi-K3 | 32 | 87 | 86.07 | 37.58 | 2.29x |
| Kimi-K3 | 64 | 87 | 86.93 | 42.89 | 2.03x |
| Kimi-K3 | 256 | 87 | 87.00 | 47.26 | 1.84x |
| Kimi-K3 | 1024 | 87 | 87.00 | 47.37 | 1.84x |
| Kimi-K3 | 4096 | 87 | 87.00 | 47.37 | 1.84x |
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
| Kimi-K3 | 1 | 130 | 15.11 | 9.95 | 1.52x |
| Kimi-K3 | 2 | 130 | 28.24 | 14.48 | 1.95x |
| Kimi-K3 | 4 | 130 | 49.65 | 20.86 | 2.38x |
| Kimi-K3 | 8 | 130 | 78.65 | 28.80 | 2.73x |
| Kimi-K3 | 16 | 130 | 107.02 | 37.86 | 2.83x |
| Kimi-K3 | 32 | 130 | 123.73 | 47.01 | 2.63x |
| Kimi-K3 | 64 | 130 | 128.86 | 54.77 | 2.35x |
| Kimi-K3 | 256 | 130 | 129.86 | 61.35 | 2.12x |
| Kimi-K3 | 1024 | 130 | 129.87 | 61.53 | 2.11x |
| Kimi-K3 | 4096 | 130 | 129.87 | 61.53 | 2.11x |
| Kimi-K3 | 1 | 132 | 15.12 | 9.98 | 1.51x |
| Kimi-K3 | 2 | 132 | 28.29 | 14.53 | 1.95x |
| Kimi-K3 | 4 | 132 | 49.81 | 20.97 | 2.38x |
| Kimi-K3 | 8 | 132 | 79.11 | 28.97 | 2.73x |
| Kimi-K3 | 16 | 132 | 108.04 | 38.12 | 2.83x |
| Kimi-K3 | 32 | 132 | 125.33 | 47.39 | 2.64x |
| Kimi-K3 | 64 | 132 | 130.75 | 55.26 | 2.37x |
| Kimi-K3 | 256 | 132 | 131.84 | 61.94 | 2.13x |
| Kimi-K3 | 1024 | 132 | 131.85 | 62.12 | 2.12x |
| Kimi-K3 | 4096 | 132 | 131.85 | 62.12 | 2.12x |
| Kimi-K3 | 1 | 139 | 15.17 | 10.11 | 1.50x |
| Kimi-K3 | 2 | 139 | 28.45 | 14.70 | 1.94x |
| Kimi-K3 | 4 | 139 | 50.36 | 21.33 | 2.36x |
| Kimi-K3 | 8 | 139 | 80.68 | 29.57 | 2.73x |
| Kimi-K3 | 16 | 139 | 111.50 | 39.04 | 2.86x |
| Kimi-K3 | 32 | 139 | 130.84 | 48.69 | 2.69x |
| Kimi-K3 | 64 | 139 | 137.34 | 56.94 | 2.41x |
| Kimi-K3 | 256 | 139 | 138.77 | 63.95 | 2.17x |
| Kimi-K3 | 1024 | 139 | 138.78 | 64.14 | 2.16x |
| Kimi-K3 | 4096 | 139 | 138.78 | 64.14 | 2.16x |
| Kimi-K3 | 1 | 144 | 15.19 | 10.20 | 1.49x |
| Kimi-K3 | 2 | 144 | 28.55 | 14.81 | 1.93x |
| Kimi-K3 | 4 | 144 | 50.72 | 21.59 | 2.35x |
| Kimi-K3 | 8 | 144 | 81.72 | 29.99 | 2.73x |
| Kimi-K3 | 16 | 144 | 113.86 | 39.67 | 2.87x |
| Kimi-K3 | 32 | 144 | 134.66 | 49.60 | 2.72x |
| Kimi-K3 | 64 | 144 | 141.99 | 58.10 | 2.44x |
| Kimi-K3 | 256 | 144 | 143.70 | 65.36 | 2.20x |
| Kimi-K3 | 1024 | 144 | 143.72 | 65.56 | 2.19x |
| Kimi-K3 | 4096 | 144 | 143.72 | 65.56 | 2.19x |
| Kimi-K3 | 1 | 145 | 15.20 | 10.22 | 1.49x |
| Kimi-K3 | 2 | 145 | 28.57 | 14.83 | 1.93x |
| Kimi-K3 | 4 | 145 | 50.79 | 21.64 | 2.35x |
| Kimi-K3 | 8 | 145 | 81.92 | 30.07 | 2.72x |
| Kimi-K3 | 16 | 145 | 114.32 | 39.80 | 2.87x |
| Kimi-K3 | 32 | 145 | 135.42 | 49.78 | 2.72x |
| Kimi-K3 | 64 | 145 | 142.92 | 58.33 | 2.45x |
| Kimi-K3 | 256 | 145 | 144.69 | 65.64 | 2.20x |
| Kimi-K3 | 1024 | 145 | 144.71 | 65.84 | 2.20x |
| Kimi-K3 | 4096 | 145 | 144.71 | 65.84 | 2.20x |
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
| Kimi-K3 | 1 | 191 | 15.39 | 10.92 | 1.41x |
| Kimi-K3 | 2 | 191 | 29.29 | 15.72 | 1.86x |
| Kimi-K3 | 4 | 191 | 53.28 | 23.67 | 2.25x |
| Kimi-K3 | 8 | 191 | 89.42 | 33.34 | 2.68x |
| Kimi-K3 | 16 | 191 | 132.19 | 44.91 | 2.94x |
| Kimi-K3 | 32 | 191 | 166.68 | 57.14 | 2.92x |
| Kimi-K3 | 64 | 191 | 183.36 | 67.92 | 2.70x |
| Kimi-K3 | 256 | 191 | 189.19 | 77.33 | 2.45x |
| Kimi-K3 | 1024 | 191 | 189.27 | 77.59 | 2.44x |
| Kimi-K3 | 4096 | 191 | 189.27 | 77.59 | 2.44x |
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
| gpu | Kimi-K3 | 1 | 27.74 | 3.6% |
| rom | Kimi-K3 | 1 | 27.74 | 9.9% |

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
| Kimi-K3 | 1 | 128 | 72.67% | 1,551.55 | 16.68 |
| Kimi-K3 | 2 | 3 | 0.66% | 18.69 | 16.68 |
| Kimi-K3 | 4 | 3 | 0.66% | 18.69 | 16.68 |
| Kimi-K3 | 8 | 3 | 0.66% | 18.69 | 16.68 |
| Kimi-K3 | 16 | 3 | 0.66% | 18.69 | 16.68 |
| Kimi-K3 | 32 | 3 | 0.66% | 18.69 | 16.68 |
| Kimi-K3 | 64 | 3 | 0.66% | 18.69 | 16.68 |

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
| Kimi-K3 | 1 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 107.9 | 30,644.4 |
| Kimi-K3 | 2 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 107.9 | 30,644.4 |
| Kimi-K3 | 4 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 107.9 | 30,644.4 |
| Kimi-K3 | 8 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 107.9 | 30,644.4 |
| Kimi-K3 | 16 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 107.9 | 30,644.4 |
| Kimi-K3 | 32 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 107.9 | 30,644.4 |
| Kimi-K3 | 64 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 107.9 | 30,644.4 |
| Kimi-K3 | 256 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 107.9 | 30,644.4 |
| Kimi-K3 | 1024 | 6.29% | 202.1 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 30.0 | 30,718.0 |
| Kimi-K3 | 4096 | 22.89% | 442.2 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 7.5 | 30,739.2 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 1 |
| gpu | link_latency | 619 |
| gpu | thermal | 258 |
| gpu | weight_read | 542 |
| rom | compute | 580 |
| rom | infeasible | 1260 |
| rom | kv_read | 135 |
| rom | link_latency | 622 |
| rom | weight_read | 283 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 1 |
| rom | CAPACITY | 1260 |

## Mechanical consistency audit

**FAIL** over 93,047 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x256', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x259', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x272', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x273', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x313', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-pipeline-x375', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x256', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x259', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x272', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x273', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x313', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-tensor-x375', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x256', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x259', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x272', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x273', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x313', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x375', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x256', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x259', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x272', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x273', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x313', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-pipeline-x375', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x5', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x6', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x8', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-pipeline-x12', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x256', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x259', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x272', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x273', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x313', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-tensor-x375', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x5', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x6', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x8', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-wafer-tensor-x12', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x256', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x259', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x272', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x273', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x313', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N5-native-SRAMKV-array-hybrid-x375', 'Kimi-K3', 1)

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

# Area-constrained roofline: n5_vs_b200-flash-1m

> CONTEXT-LADDER RUNG of n5_vs_b200: DeepSeek-V4-Flash-0731 at 1,000,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 202x (ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream, 1,872 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 84 devices. On the GPU side the correction reaches 3x (b200_sxm-x953-pipeline, 953 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 16 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Flash-0731 takes 35 x 815 mm2 (28,525 mm2, array, KV in SRAM) at 2,227 tok/s per user and 78 tok/s per 1,000 mm2, holding 1 session, against 18 copies of one unified HBM die at the same silicon: 4.1x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Flash-0731 on 92,095 mm2 of ROM silicon at 2,960 tok/s per user against 92,800 mm2 of b200_sxm-x58-nvl72-tensor at 559 tok/s: **5.3x**, ROM binding on `layer_fixed_latency` and the GPU on `layer_fixed_latency`. It holds 1 resident session against the GPU cluster's 1,340. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 1.57x to it.** At 97,800 mm2 on DeepSeek-V4-Flash-0731 the pipeline-only GPU delivers 356.04 tok/s and the same silicon running tensor delivers 559 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.00x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 2.48x (DeepSeek-V4-Flash-0731, ROM binding on `thermal`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 1,049 to 475,451 tok/s, and its rate with every slot occupied from 292,799 to 475,451. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 279 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 949 us over NVLink, capping per-user decode at 1,054 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 260.5 us and cap it at 3,839 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 10 operating points and an array 8; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 57 of 2533 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 27.5x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 13.67x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.04x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 10 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 24 of 2,533 feasible points (0.9%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x349` at batch 4096 on 284,435 mm2, throttled 1.24x from 178 to 144 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 96% kv read against 0.2% weight read. The ROM sweep is not what melts it.


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

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x35`** -- 35 x 815 mm2 reticle dies, 28,525 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **2,227.1 tok/s per user** (0.45 ms/token), binding on `layer_fixed_latency`
- **78.1 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 2,227 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 1,779 W at 0.062 W/mm2, 798.9 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 18 copies of one unified HBM die -- `b200_sxm-x18-nvl72-tensor`, 28,800 mm2, area ratio 0.9905 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 28,525 | 28,800 | 0.9905 |
| user tok/s | 2,227.1 | 543.1 | 4.10x |
| aggregate tok/s | 2,227 | 543 | 0.34x |
| resident sessions | 1 | 399 | -- |
| J/token | 0.7989 | 12.9598 | 16.2x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 399 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x61-nvl72-tensor` at 97,600 mm2 and 559.5 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-hybrid-x84` | 68,460 | 2,923.9 | 42.7 | 1 | 5.25x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 92,095 | 2,959.9 | 32.1 | 1 | 5.29x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x31` | 25,265 | 1,861.8 | 73.7 | 1 | 3.44x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | 28,525 | 2,227.1 | 78.1 | 1 | 4.10x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | 28,525 | 2,227.1 | 78.1 | -- | 78.1 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x38` | 30,970 | 2,341.6 | 75.6 | 46.8 | 78.1 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x44-romfill` | 35,860 | 2,508.8 | 70.0 | 38.4 | 78.1 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 36,675 | 2,533.3 | 69.1 | 37.6 | 78.1 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x47` | 38,305 | 2,574.9 | 67.2 | 35.6 | 78.1 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x49-romfill` | 39,935 | 2,584.2 | 64.7 | 31.3 | 78.1 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x57` | 46,455 | 2,717.2 | 58.5 | 27.3 | 78.1 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x60` | 48,900 | 2,777.7 | 56.8 | 27.0 | 78.1 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x84` | 68,460 | 2,923.9 | 42.7 | 17.4 | 78.1 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x90` | 73,350 | 2,927.3 | 39.9 | 15.6 | 78.1 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x101` | 82,315 | 2,943.6 | 35.8 | 13.3 | 78.1 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x102` | 83,130 | 2,950.0 | 35.5 | 13.2 | 78.1 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 92,095 | 2,959.9 | 32.1 | 11.5 | 78.1 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x35` **<-- recommended** | 28,525 | 35 | 2,227.1 | 2,227 | 78.1 | 1 | `layer_fixed_latency` | 1,779 | 798.9 | `b200_sxm-x18-nvl72-tensor` | 4.10x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x38` | 30,970 | 38 | 2,341.6 | 2,342 | 75.6 | 1 | `layer_fixed_latency` | 2,061 | 880.2 | `b200_sxm-x19-nvl72-tensor` | 4.30x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x44-romfill` | 35,860 | 44 | 2,508.8 | 2,509 | 70.0 | 1 | `layer_fixed_latency` | 2,772 | 1,105.1 | `b200_sxm-x22-nvl72-tensor` | 4.58x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | 36,675 | 45 | 2,533.3 | 2,533 | 69.1 | 1 | `layer_fixed_latency` | 2,891 | 1,141.2 | `b200_sxm-x23-nvl72-tensor` | 4.62x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x47` | 38,305 | 47 | 2,574.9 | 2,575 | 67.2 | 1 | `layer_fixed_latency` | 3,128 | 1,214.7 | `b200_sxm-x24-nvl72-tensor` | 4.69x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x49-romfill` | 39,935 | 49 | 2,584.2 | 2,584 | 64.7 | 1 | `layer_fixed_latency` | 3,348 | 1,295.5 | `b200_sxm-x25-nvl72-tensor` | 4.70x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x57` | 46,455 | 57 | 2,717.2 | 2,717 | 58.5 | 1 | `layer_fixed_latency` | 4,311 | 1,586.7 | `b200_sxm-x29-nvl72-tensor` | 4.92x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x60` | 48,900 | 60 | 2,777.7 | 2,778 | 56.8 | 1 | `layer_fixed_latency` | 4,667 | 1,680.1 | `b200_sxm-x31-nvl72-tensor` | 5.02x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x84` | 68,460 | 84 | 2,923.9 | 2,924 | 42.7 | 1 | `layer_fixed_latency` | 7,505 | 2,566.7 | `b200_sxm-x43-nvl72-tensor` | 5.25x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x90` | 73,350 | 90 | 2,927.3 | 2,927 | 39.9 | 1 | `layer_fixed_latency` | 8,214 | 2,806.0 | `b200_sxm-x46-nvl72-tensor` | 5.25x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x101` | 82,315 | 101 | 2,943.6 | 2,944 | 35.8 | 1 | `layer_fixed_latency` | 9,514 | 3,232.1 | `b200_sxm-x51-nvl72-tensor` | 5.27x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x102` | 83,130 | 102 | 2,950.0 | 2,950 | 35.5 | 1 | `layer_fixed_latency` | 9,632 | 3,265.2 | `b200_sxm-x52-nvl72-tensor` | 5.28x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 92,095 | 113 | 2,959.9 | 2,960 | 32.1 | 1 | `layer_fixed_latency` | 10,932 | 3,693.5 | `b200_sxm-x58-nvl72-tensor` | 5.29x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 222 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | 28,525 | 2,227.1 | 78.1 | 1 |
| array | 222 | fastest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 92,095 | 2,959.9 | 32.1 | 1 |
| array | 222 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x31` | 25,265 | 1,861.8 | 73.7 | 1 |
| wafer | 46 | densest | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 46,225 | 1,563.3 | 33.8 | 1 |
| wafer | 46 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 2,778.1 | 30.0 | 1 |
| wafer | 46 | smallest | `ROM-N5-native-SRAMKV-wafer-pipeline-x1` | 46,225 | 1,563.3 | 33.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 92,095 | 2,959.9 | 2,960 | 1 | 10,932 | 3,693.5 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 559.2 | 1,340 | 37,695.3 | 0.992 | 5.29x | 10.2x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 2,778.1 | 2,778 | 1 | 10,981 | 3,952.8 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 559.2 | 1,340 | 37,695.3 | 0.996 | 4.97x | 9.5x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-hybrid-x113` | 92,095 | 2,959.9 | 2,960 | 1 | 10,932 | 3,693.5 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 559.2 | 1,340 | 37,695.3 | 0.992 | 5.29x | 10.2x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 2,778.1 | -- | 1 | -- | 3,952.8 | -- | -- | -- | -- | -- | 0.996 | 0.94x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 227,385 | 2,513.2 | 87,961 | 4,102 | 49,479 | 7,061.0 | `layer_fixed_latency` | `b200_sxm-x142-nvl72-hybrid` | 558.7 | 3,316 | 45,878.0 | 1.001 | 4.50x | 6.5x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 1,809.5 | 211,714 | 4,173 | 171,004 | 37,553.2 | `layer_fixed_latency` | `b200_sxm-x953-nvl72-hybrid` | 548.5 | 22,397 | 305,771.5 | 1.000 | 3.30x | 8.1x |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 227,385 | 2,513.2 | 87,961 | 4,102 | 49,479 | 3,614.8 | `layer_fixed_latency` | `b200_sxm-x142-nvl72-hybrid` | 548.5 | 3,316 | 24,026.6 | 1.001 | 4.58x | 6.6x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 1,809.5 | 211,714 | 4,173 | 171,004 | 18,860.9 | `layer_fixed_latency` | `b200_sxm-x953-nvl72-hybrid` | 548.5 | 22,397 | 153,558.1 | 1.000 | 3.30x | 8.1x |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 227,385 | 2,513.2 | 87,961 | 4,102 | 49,479 | 1,891.7 | `layer_fixed_latency` | `b200_sxm-x142-nvl72-hybrid` | 535.4 | 3,316 | 12,962.4 | 1.001 | 4.69x | 6.9x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 1,809.5 | 211,714 | 4,173 | 171,004 | 9,514.8 | `layer_fixed_latency` | `b200_sxm-x953-nvl72-hybrid` | 548.5 | 22,397 | 77,451.4 | 1.000 | 3.30x | 8.1x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 227,385 | 2,513.2 | 87,961 | 4,102 | 49,479 | 1,030.2 | `layer_fixed_latency` | `b200_sxm-x142-nvl72-hybrid` | 535.2 | 3,316 | 7,155.5 | 1.001 | 4.70x | 6.9x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 1,809.5 | 211,714 | 4,173 | 171,004 | 4,841.7 | `layer_fixed_latency` | `b200_sxm-x953-nvl72-hybrid` | 543.1 | 22,397 | 39,725.8 | 1.000 | 3.33x | 8.2x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 227,385 | 2,513.2 | 87,961 | 4,102 | 49,479 | 599.4 | `layer_fixed_latency` | `b200_sxm-x142-nvl72-hybrid` | 482.5 | 3,316 | 4,207.2 | 1.001 | 5.21x | 7.0x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 1,809.5 | 211,714 | 4,173 | 171,004 | 2,505.2 | `layer_fixed_latency` | `b200_sxm-x953-nvl72-hybrid` | 531.8 | 22,397 | 20,918.1 | 1.000 | 3.40x | 8.3x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 227,385 | 2,479.0 | 173,532 | 4,102 | 63,911 | 387.0 | `layer_fixed_latency` | `b200_sxm-x142-nvl72-hybrid` | 428.3 | 3,316 | 2,799.7 | 1.001 | 5.79x | 7.2x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 1,809.5 | 211,714 | 4,173 | 171,004 | 1,336.9 | `layer_fixed_latency` | `b200_sxm-x953-nvl72-hybrid` | 525.7 | 22,397 | 11,270.6 | 1.000 | 3.44x | 8.4x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 284,435 | 1,582.7 | 405,180 | 5,131 | 111,584 | 275.4 | `weight_read` | `b200_sxm-x178-pipeline` | 320.0 | 4,163 | 1,855.4 | 0.999 | 4.95x | 5.8x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 1,463.1 | 374,562 | 4,173 | 198,393 | 529.7 | `kv_read` | `b200_sxm-x953-nvl72-hybrid` | 473.6 | 22,397 | 4,044.5 | 1.000 | 3.09x | 7.6x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 284,435 | 576.3 | 590,148 | 5,131 | 142,218 | 241.0 | `thermal` | `b200_sxm-x178-pipeline` | 160.8 | 4,163 | 1,029.3 | 0.999 | 3.58x | 4.0x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 1,525,425 | 610.6 | 625,269 | 4,173 | 240,625 | 384.8 | `kv_read` | `b200_sxm-x953-pipeline` | 349.3 | 22,397 | 2,221.4 | 1.000 | 1.75x | 4.9x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x349` | 284,435 | 144.5 | 591,884 | 5,131 | 142,218 | 240.3 | `thermal` | `b200_sxm-x178-pipeline` | 58.3 | 4,163 | 744.9 | 0.999 | 2.48x | 2.9x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x33` | 1,525,425 | 175.2 | 717,447 | 4,173 | 342,569 | 477.5 | `kv_read` | `b200_sxm-x953-pipeline` | 192.5 | 22,397 | 1,128.0 | 1.000 | 0.91x | 2.2x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | 28,525 | array | SRAM | 1 |
| 2-4096 | `ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 227,385 | array | HBM | 4,102 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 279, 340, 349 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 279, 340, 349 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 31, 35, 38, 44, 45, 47, 49, 57, 60, 90, 113, 120, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 31, 35, 38, 45, 47, 57, 60, 84, 90, 101, 102, 113, 120, 170, 227, 340 |

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
| DeepSeek-V4-Flash-0731 | `ROM-N5-native-SRAMKV-array-hw-tensor-x35` | 1 | 35 | 6.51 | hierarchical | 249.72 | 173.08 | 38.00 | 53.39 | 2,227.1 |
| DeepSeek-V4-Flash-0731 | `b200_sxm-x18-nvl72-tensor` | 1 | 18 | 6.51 | measured_floor | 890.50 | 857.36 | 109.21 | 221.01 | 543.1 |
| DeepSeek-V4-Flash-0731 | `b200_sxm-x18-nvl72-tensor` | 64 | 18 | 6.51 | measured_floor | 886.60 | 12,852.51 | 1,886.20 | 360.74 | 64.7 |

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

- **24 of 2,533 feasible points (0.9%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 10, rom 14.
- By area class: large array (5,000-40,000 mm2) 2, wafer (>=40,000 mm2) 22.
- By KV store: hbm 24.
- By batch: B=256 2, B=1024 10, B=4096 12.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 45% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 256 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 372 | 2 | 42.3% | 100.0% | 0.625 | 83% |
| gpu | wafer (>=40,000 mm2) | 1,063 | 8 | 37.3% | 100.0% | 0.625 | 94% |
| rom | large array (5,000-40,000 mm2) | 144 | 0 | 13.1% | 16.8% | 0.084 | 99% |
| rom | wafer (>=40,000 mm2) | 954 | 14 | 25.5% | 100.0% | 0.500 | 93% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x349` | DeepSeek-V4-Flash-0731 | 4096 | 284,435 | hbm | 1.235x | 142,217.5 / 142,217.5 W | 31% | 144.3 | 178.3 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340` | DeepSeek-V4-Flash-0731 | 4096 | 277,100 | hbm | 1.235x | 138,550.0 / 138,550.0 W | 31% | 140.7 | 173.8 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279` | DeepSeek-V4-Flash-0731 | 4096 | 227,385 | hbm | 1.233x | 113,692.5 / 113,692.5 W | 30% | 116.1 | 143.1 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x340` | DeepSeek-V4-Flash-0731 | 4096 | 277,100 | hbm | 1.214x | 138,550.0 / 138,550.0 W | 31% | 140.7 | 170.8 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x349` | DeepSeek-V4-Flash-0731 | 4096 | 284,435 | hbm | 1.214x | 142,217.5 / 142,217.5 W | 31% | 144.3 | 175.2 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x279` | DeepSeek-V4-Flash-0731 | 4096 | 227,385 | hbm | 1.214x | 113,692.5 / 113,692.5 W | 30% | 116.1 | 140.9 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279` | DeepSeek-V4-Flash-0731 | 1024 | 227,385 | hbm | 1.163x | 113,692.5 / 113,692.5 W | 30% | 462.6 | 538.0 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x349` | DeepSeek-V4-Flash-0731 | 4096 | 284,435 | hbm | 1.136x | 142,217.5 / 142,217.5 W | 31% | 144.5 | 164.1 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340` | DeepSeek-V4-Flash-0731 | 4096 | 277,100 | hbm | 1.134x | 138,550.0 / 138,550.0 W | 31% | 140.9 | 159.8 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279` | DeepSeek-V4-Flash-0731 | 4096 | 227,385 | hbm | 1.130x | 113,692.5 / 113,692.5 W | 30% | 116.2 | 131.3 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x279` | DeepSeek-V4-Flash-0731 | 1024 | 227,385 | hbm | 1.122x | 113,692.5 / 113,692.5 W | 30% | 462.6 | 518.8 |
| `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279` | DeepSeek-V4-Flash-0731 | 1024 | 227,385 | hbm | 1.068x | 113,692.5 / 113,692.5 W | 30% | 463.6 | 495.2 |

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
| DeepSeek-V4-Flash-0731 | 1 | 68,460 | `DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x84` | 2.566736 | 7,504.8 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x43-nvl72-tensor` | 28.406859 | 15,817.7 | layer_fixed_latency | 11.07x |
| DeepSeek-V4-Flash-0731 | 2 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 7.060978 | 49,478.7 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x142-nvl72-hybrid` | 45.877997 | 51,265.1 | layer_fixed_latency | 6.50x |
| DeepSeek-V4-Flash-0731 | 4 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 3.614820 | 49,478.7 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x142-nvl72-hybrid` | 24.026555 | 53,450.2 | layer_fixed_latency | 6.65x |
| DeepSeek-V4-Flash-0731 | 8 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 1.891741 | 49,478.7 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x142-nvl72-hybrid` | 12.962402 | 56,242.2 | layer_fixed_latency | 6.85x |
| DeepSeek-V4-Flash-0731 | 16 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 1.030201 | 49,478.7 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x142-nvl72-hybrid` | 7.155486 | 62,717.7 | layer_fixed_latency | 6.95x |
| DeepSeek-V4-Flash-0731 | 32 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 0.599431 | 49,478.7 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x142-nvl72-hybrid` | 4.207193 | 64,957.5 | layer_fixed_latency | 7.02x |
| DeepSeek-V4-Flash-0731 | 64 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 0.387012 | 63,911.2 | layer_fixed_latency | `DSV4-Flash/b200_sxm-x142-nvl72-hybrid` | 2.799723 | 76,737.0 | layer_fixed_latency | 7.23x |
| DeepSeek-V4-Flash-0731 | 256 | 227,385 | `DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279` | 0.256455 | 99,182.3 | kv_read | `DSV4-Flash/b200_sxm-x142-pipeline` | 1.635932 | 123,671.5 | weight_read | 5.63x |
| DeepSeek-V4-Flash-0731 | 1024 | 1,525,425 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill` | 0.384834 | 240,624.9 | kv_read | `DSV4-Flash/b200_sxm-x953-pipeline` | 2.221350 | 794,636.9 | weight_read | 4.87x |
| DeepSeek-V4-Flash-0731 | 4096 | 1,525,425 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33` | 0.477484 | 342,569.0 | kv_read | `DSV4-Flash/b200_sxm-x953-pipeline` | 1.127997 | 889,300.7 | weight_read | 2.21x |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 2,864.9 | wafer-pipeline | 1,563.3 | wafer-pipeline | 1.83x | 977.4 | pipeline | 552.1 | tensor | 1.77x | 2.93x | 2.83x | 0.97x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 2,879.5 | wafer-hybrid | 2,778.1 | wafer-hybrid | 1.04x | 988.3 | pipeline | 559.2 | tensor | 1.77x | 2.91x | 4.97x | 1.71x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 2,866.2 | wafer-pipeline | 2,674.3 | wafer-hybrid | 1.07x | 998.7 | pipeline | 554.4 | hybrid | 1.80x | 2.87x | 4.82x | 1.68x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 2,866.2 | wafer-pipeline | 2,577.4 | wafer-hybrid | 1.11x | 1,003.9 | pipeline | 557.4 | hybrid | 1.80x | 2.85x | 4.62x | 1.62x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 2,866.2 | wafer-pipeline | 2,366.9 | wafer-hybrid | 1.21x | 1,009.2 | pipeline | 556.5 | hybrid | 1.81x | 2.84x | 4.25x | 1.50x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 2,866.2 | wafer-pipeline | 2,216.7 | wafer-hybrid | 1.29x | 1,011.9 | pipeline | 555.7 | hybrid | 1.82x | 2.83x | 3.99x | 1.41x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 2,866.2 | wafer-pipeline | 2,049.8 | wafer-hybrid | 1.40x | 1,014.6 | pipeline | 556.0 | hybrid | 1.82x | 2.82x | 3.69x | 1.30x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.97x to 1.71x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x113 | 92,095 | 2,959.9 | 2,959.9 | layer_fixed_latency | DSV4-Flash/b200_sxm-x58-nvl72-tensor | 92,800 | 0.99x | tensor | 868.90 | 559.2 | 559.2 | layer_fixed_latency | 5.29x | 0.14x | 8.31x | 5.29x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x31 | 25,265 | 1,861.8 | 1,861.8 | layer_fixed_latency | DSV4-Flash/b200_sxm-x16-hybrid | 25,600 | 0.99x | hybrid | 736.61 | 541.9 | 1,083.7 | layer_fixed_latency | 3.44x | 0.32x | 5.16x | 3.44x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 2,513.2 | 87,960.8 | layer_fixed_latency | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 875.63 | 558.7 | 1,117.4 | layer_fixed_latency | 4.50x | 1.74x | 7.06x | 4.50x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 2,513.2 | 87,960.8 | layer_fixed_latency | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 873.45 | 548.5 | 2,742.4 | layer_fixed_latency | 4.58x | 1.74x | 7.06x | 4.58x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 2,513.2 | 87,960.8 | layer_fixed_latency | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 870.54 | 535.4 | 4,818.7 | layer_fixed_latency | 4.69x | 1.74x | 7.06x | 4.69x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 2,513.2 | 87,960.8 | layer_fixed_latency | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 756.40 | 535.2 | 9,634.3 | layer_fixed_latency | 4.70x | 1.74x | 7.06x | 4.70x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 2,513.2 | 87,960.8 | layer_fixed_latency | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 893.55 | 482.5 | 15,439.6 | layer_fixed_latency | 5.21x | 1.74x | 7.06x | 5.21x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 2,479.0 | 173,531.9 | layer_fixed_latency | DSV4-Flash/b200_sxm-x142-nvl72-hybrid | 227,200 | 1.00x | hybrid | 871.33 | 428.3 | 27,408.8 | layer_fixed_latency | 5.79x | 3.43x | 6.96x | 5.79x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x349 | 284,435 | 1,582.7 | 405,180.2 | weight_read | DSV4-Flash/b200_sxm-x178-pipeline | 284,800 | 1.00x | pipeline | 63.23 | 320.0 | 81,930.3 | weight_read | 4.95x | 4.95x | 4.95x | 5.23x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 1,510.7 | 386,742.9 | kv_read | DSV4-Flash/b200_sxm-x142-pipeline | 227,200 | 1.00x | pipeline | 64.92 | 295.3 | 75,597.0 | weight_read | 5.12x | 5.12x | 5.12x | 5.32x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill | 1,525,425 | 610.6 | 625,268.8 | kv_read | DSV4-Flash/b200_sxm-x953-pipeline | 1,524,800 | 1.00x | pipeline | 61.55 | 349.3 | 357,727.0 | weight_read | 1.75x | 1.75x | 1.75x | 2.49x |
| DeepSeek-V4-Flash-0731 | 1024 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 463.6 | 474,752.4 | thermal | DSV4-Flash/b200_sxm-x142-pipeline | 227,200 | 1.00x | pipeline | 89.94 | 138.5 | 141,834.2 | weight_read | 3.35x | 3.35x | 3.35x | 3.42x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33 | 1,525,425 | 175.2 | 717,446.6 | kv_read | DSV4-Flash/b200_sxm-x953-pipeline | 1,524,800 | 1.00x | pipeline | 76.46 | 192.5 | 788,389.5 | weight_read | 0.91x | 0.91x | 0.91x | 1.14x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 116.2 | 476,067.7 | thermal | DSV4-Flash/b200_sxm-x142-pipeline | 227,200 | 1.00x | pipeline | 190.03 | infeasible | — | capacity_or_format | — | — | — | — |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 9 | 14,400 | 838.16 | 208.49 | 520.0 | 773.1 |
| DeepSeek-V4-Flash-0731 | 10 | 16,000 | 840.47 | 208.51 | 524.5 | 784.6 |
| DeepSeek-V4-Flash-0731 | 16 | 25,600 | 736.61 | 208.60 | 541.9 | 759.0 |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 857.36 | 208.62 | 543.1 | 838.5 |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 858.04 | 208.62 | 544.3 | 842.0 |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 859.76 | 208.64 | 547.4 | 850.6 |
| DeepSeek-V4-Flash-0731 | 23 | 36,800 | 860.25 | 208.65 | 548.3 | 853.0 |
| DeepSeek-V4-Flash-0731 | 24 | 38,400 | 860.70 | 208.65 | 549.1 | 855.2 |
| DeepSeek-V4-Flash-0731 | 25 | 40,000 | 861.16 | 208.65 | 549.8 | 857.3 |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 862.65 | 208.67 | 552.1 | 864.2 |
| DeepSeek-V4-Flash-0731 | 31 | 49,600 | 863.28 | 208.67 | 553.1 | 867.0 |
| DeepSeek-V4-Flash-0731 | 43 | 68,800 | 866.25 | 208.69 | 556.8 | 878.5 |
| DeepSeek-V4-Flash-0731 | 46 | 73,600 | 866.84 | 208.70 | 557.4 | 880.5 |
| DeepSeek-V4-Flash-0731 | 51 | 81,600 | 867.76 | 208.70 | 558.3 | 883.2 |
| DeepSeek-V4-Flash-0731 | 52 | 83,200 | 867.93 | 208.70 | 558.4 | 883.7 |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 868.90 | 208.71 | 559.2 | 886.3 |
| DeepSeek-V4-Flash-0731 | 61 | 97,600 | 869.36 | 208.71 | 559.5 | 887.5 |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 874.52 | 210.91 | 554.4 | 877.1 |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 874.52 | 210.91 | 557.4 | 884.6 |
| DeepSeek-V4-Flash-0731 | 142 | 227,200 | 875.63 | 210.91 | 558.7 | 888.8 |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 877.20 | 213.10 | 556.5 | 882.8 |
| DeepSeek-V4-Flash-0731 | 176 | 281,600 | 877.20 | 213.10 | 556.7 | 883.2 |
| DeepSeek-V4-Flash-0731 | 178 | 284,800 | 877.20 | 213.10 | 556.8 | 883.4 |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 879.89 | 215.30 | 555.7 | 881.1 |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 883.69 | 217.49 | 556.0 | 883.2 |
| DeepSeek-V4-Flash-0731 | 953 | 1,524,800 | 907.86 | 237.24 | 548.5 | 867.7 |

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
| DeepSeek-V4-Flash-0731 | 9 | 14,400 | 362.2 | 520.0 | 496.9 | tensor | 838.16 | 43.6% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 10 | 16,000 | 362.1 | 524.5 | 506.5 | tensor | 840.47 | 44.1% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 16 | 25,600 | 361.1 | 540.1 | 541.9 | hybrid | 736.61 | 39.9% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 18 | 28,800 | 360.6 | 543.1 | 520.9 | tensor | 857.36 | 46.6% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 360.4 | 544.3 | 525.0 | tensor | 858.04 | 46.7% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 22 | 35,200 | 359.9 | 547.4 | 535.4 | tensor | 859.76 | 47.1% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 23 | 36,800 | 359.8 | 548.3 | 538.3 | tensor | 860.25 | 47.2% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 24 | 38,400 | 359.6 | 549.1 | 541.1 | tensor | 860.70 | 47.3% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 25 | 40,000 | 359.3 | 549.8 | 523.3 | tensor | 861.16 | 47.3% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 358.6 | 552.1 | 533.9 | tensor | 862.65 | 47.6% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 31 | 49,600 | 358.3 | 553.1 | 538.3 | tensor | 863.28 | 47.7% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 43 | 68,800 | 356.0 | 556.8 | 531.6 | tensor | 866.25 | 48.2% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 46 | 73,600 | 356.0 | 557.4 | 536.0 | tensor | 866.84 | 48.3% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 51 | 81,600 | 356.0 | 558.3 | 531.9 | tensor | 867.76 | 48.4% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 52 | 83,200 | 356.0 | 558.4 | 533.2 | tensor | 867.93 | 48.5% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 356.0 | 559.2 | 530.8 | tensor | 868.90 | 48.6% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 61 | 97,600 | 356.0 | 559.5 | 534.1 | tensor | 869.36 | 48.6% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 356.0 | 207.4 | 554.4 | hybrid | 874.52 | 48.5% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 356.0 | 206.4 | 557.4 | hybrid | 874.52 | 48.7% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 142 | 227,200 | 356.0 | 205.4 | 558.7 | hybrid | 875.63 | 48.9% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 356.0 | 180.4 | 556.5 | hybrid | 877.20 | 48.8% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 176 | 281,600 | 356.0 | 180.3 | 556.7 | hybrid | 877.20 | 48.8% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 178 | 284,800 | 356.0 | 180.2 | 556.8 | hybrid | 877.20 | 48.8% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 356.0 | 168.2 | 555.7 | hybrid | 879.89 | 48.9% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 356.0 | 158.4 | 556.0 | hybrid | 883.69 | 49.1% | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 953 | 1,524,800 | 356.0 | 122.6 | 548.5 | hybrid | 907.86 | 49.8% | link_latency |

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
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x102 | DeepSeek-V4-Flash-0731 | 102 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x35 | DeepSeek-V4-Flash-0731 | 35 | tensor | rom_package_ucie | rom_board_serdes | 172 | 41.00 us | 2,439.0 tok/s | 24,390.2 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 9 on rom_board_serdes (traversals 4.4) = 38.88 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x84 | DeepSeek-V4-Flash-0731 | 84 | hybrid | rom_package_ucie | rom_board_serdes | 106 | 4.21 us | 23,768.2 tok/s | 237,681.5 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 20 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.09 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x101 | DeepSeek-V4-Flash-0731 | 101 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4-Flash-0731 | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x31 | DeepSeek-V4-Flash-0731 | 31 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x47 | DeepSeek-V4-Flash-0731 | 47 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | DeepSeek-V4-Flash-0731 | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 87 | 165.65 us | 603.7 tok/s | 6,036.8 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
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
| DSV4-Flash/b200_sxm-x10-pipeline | DeepSeek-V4-Flash-0731 | 10 | pipeline | nvlink5 | infiniband_ndr | 9 | 11.87 us | 8,427.0 tok/s | 84,269.7 tok/s | 8 x point_to_point span 2 on nvlink5 (traversals 1.0) = 9.67 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x10-tensor | DeepSeek-V4-Flash-0731 | 10 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x10-hybrid | DeepSeek-V4-Flash-0731 | 10 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x10-nvl72-tensor | DeepSeek-V4-Flash-0731 | 10 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.51 us | 479.6 tok/s | 4,795.9 tok/s | 86 x all_reduce span 10 on nvlink5_nvl72 (traversals 2.0) = 208.51 us |
| DSV4-Flash/b200_sxm-x10-expert | DeepSeek-V4-Flash-0731 | 10 | expert | nvlink5 | infiniband_ndr | 172 | 391.49 us | 255.4 tok/s | 2,554.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 183.03 us |
| DSV4-Flash/b200_sxm-x10-nvl72-expert | DeepSeek-V4-Flash-0731 | 10 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.18 us | 320.3 tok/s | 3,203.2 tok/s | 86 x all_reduce span 10 on nvlink5_nvl72 (traversals 2.0) = 208.51 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.67 us |
| DSV4-Flash/b200_sxm-x16-pipeline | DeepSeek-V4-Flash-0731 | 16 | pipeline | nvlink5 | infiniband_ndr | 15 | 19.12 us | 5,229.8 tok/s | 52,297.8 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x16-tensor | DeepSeek-V4-Flash-0731 | 16 | tensor | nvlink5 | infiniband_ndr | 172 | 578.75 us | 172.8 tok/s | 1,727.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 370.30 us |
| DSV4-Flash/b200_sxm-x16-hybrid | DeepSeek-V4-Flash-0731 | 16 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.65 us | 474.7 tok/s | 4,747.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| DSV4-Flash/b200_sxm-x16-nvl72-tensor | DeepSeek-V4-Flash-0731 | 16 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.60 us | 479.4 tok/s | 4,793.8 tok/s | 86 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 208.60 us |
| DSV4-Flash/b200_sxm-x16-expert | DeepSeek-V4-Flash-0731 | 16 | expert | nvlink5 | infiniband_ndr | 172 | 387.29 us | 258.2 tok/s | 2,582.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.43 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 179.86 us |
| DSV4-Flash/b200_sxm-x16-nvl72-expert | DeepSeek-V4-Flash-0731 | 16 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.10 us | 320.4 tok/s | 3,204.2 tok/s | 86 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 208.60 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.49 us |
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
| DSV4-Flash/b200_sxm-x25-pipeline | DeepSeek-V4-Flash-0731 | 25 | pipeline | nvlink5 | infiniband_ndr | 24 | 31.97 us | 3,127.7 tok/s | 31,276.7 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x25-tensor | DeepSeek-V4-Flash-0731 | 25 | tensor | nvlink5 | infiniband_ndr | 172 | 589.32 us | 169.7 tok/s | 1,696.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 380.86 us |
| DSV4-Flash/b200_sxm-x25-hybrid | DeepSeek-V4-Flash-0731 | 25 | hybrid | nvlink5 | infiniband_ndr | 89 | 215.04 us | 465.0 tok/s | 4,650.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| DSV4-Flash/b200_sxm-x25-nvl72-tensor | DeepSeek-V4-Flash-0731 | 25 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.65 us | 479.3 tok/s | 4,792.6 tok/s | 86 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 208.65 us |
| DSV4-Flash/b200_sxm-x25-expert | DeepSeek-V4-Flash-0731 | 25 | expert | nvlink5 | infiniband_ndr | 172 | 385.05 us | 259.7 tok/s | 2,597.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 207.08 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 177.96 us |
| DSV4-Flash/b200_sxm-x25-nvl72-expert | DeepSeek-V4-Flash-0731 | 25 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.04 us | 320.5 tok/s | 3,204.7 tok/s | 86 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 208.65 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.39 us |
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
| DSV4-Flash/b200_sxm-x43-pipeline | DeepSeek-V4-Flash-0731 | 43 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x43-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x43-hybrid | DeepSeek-V4-Flash-0731 | 43 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x43-nvl72-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.69 us | 479.2 tok/s | 4,791.7 tok/s | 86 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 208.69 us |
| DSV4-Flash/b200_sxm-x43-expert | DeepSeek-V4-Flash-0731 | 43 | expert | nvlink5 | infiniband_ndr | 172 | 383.36 us | 260.9 tok/s | 2,608.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.81 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.55 us |
| DSV4-Flash/b200_sxm-x43-nvl72-expert | DeepSeek-V4-Flash-0731 | 43 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.00 us | 320.5 tok/s | 3,205.1 tok/s | 86 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 208.69 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.31 us |
| DSV4-Flash/b200_sxm-x46-pipeline | DeepSeek-V4-Flash-0731 | 46 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x46-tensor | DeepSeek-V4-Flash-0731 | 46 | tensor | nvlink5 | infiniband_ndr | 172 | 592.84 us | 168.7 tok/s | 1,686.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 384.39 us |
| DSV4-Flash/b200_sxm-x46-hybrid | DeepSeek-V4-Flash-0731 | 46 | hybrid | nvlink5 | infiniband_ndr | 91 | 219.42 us | 455.7 tok/s | 4,557.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x46-nvl72-tensor | DeepSeek-V4-Flash-0731 | 46 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.70 us | 479.2 tok/s | 4,791.6 tok/s | 86 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 208.70 us |
| DSV4-Flash/b200_sxm-x46-expert | DeepSeek-V4-Flash-0731 | 46 | expert | nvlink5 | infiniband_ndr | 172 | 383.23 us | 260.9 tok/s | 2,609.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.81 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.42 us |
| DSV4-Flash/b200_sxm-x46-nvl72-expert | DeepSeek-V4-Flash-0731 | 46 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 312.00 us | 320.5 tok/s | 3,205.1 tok/s | 86 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 208.70 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.30 us |
| DSV4-Flash/b200_sxm-x51-pipeline | DeepSeek-V4-Flash-0731 | 51 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x51-tensor | DeepSeek-V4-Flash-0731 | 51 | tensor | nvlink5 | infiniband_ndr | 172 | 593.85 us | 168.4 tok/s | 1,683.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 385.39 us |
| DSV4-Flash/b200_sxm-x51-hybrid | DeepSeek-V4-Flash-0731 | 51 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.62 us | 451.2 tok/s | 4,512.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| DSV4-Flash/b200_sxm-x51-nvl72-tensor | DeepSeek-V4-Flash-0731 | 51 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.70 us | 479.2 tok/s | 4,791.5 tok/s | 86 x all_reduce span 51 on nvlink5_nvl72 (traversals 2.0) = 208.70 us |
| DSV4-Flash/b200_sxm-x51-expert | DeepSeek-V4-Flash-0731 | 51 | expert | nvlink5 | infiniband_ndr | 172 | 382.98 us | 261.1 tok/s | 2,611.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.74 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.24 us |
| DSV4-Flash/b200_sxm-x51-nvl72-expert | DeepSeek-V4-Flash-0731 | 51 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.2 tok/s | 86 x all_reduce span 51 on nvlink5_nvl72 (traversals 2.0) = 208.70 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.29 us |
| DSV4-Flash/b200_sxm-x52-pipeline | DeepSeek-V4-Flash-0731 | 52 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| DSV4-Flash/b200_sxm-x52-tensor | DeepSeek-V4-Flash-0731 | 52 | tensor | nvlink5 | infiniband_ndr | 172 | 593.85 us | 168.4 tok/s | 1,683.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 385.39 us |
| DSV4-Flash/b200_sxm-x52-hybrid | DeepSeek-V4-Flash-0731 | 52 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.62 us | 451.2 tok/s | 4,512.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| DSV4-Flash/b200_sxm-x52-nvl72-tensor | DeepSeek-V4-Flash-0731 | 52 | tensor | nvlink5_nvl72 | infiniband_ndr | 86 | 208.70 us | 479.1 tok/s | 4,791.5 tok/s | 86 x all_reduce span 52 on nvlink5_nvl72 (traversals 2.0) = 208.70 us |
| DSV4-Flash/b200_sxm-x52-expert | DeepSeek-V4-Flash-0731 | 52 | expert | nvlink5 | infiniband_ndr | 172 | 382.95 us | 261.1 tok/s | 2,611.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 206.74 us; 86 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 176.21 us |
| DSV4-Flash/b200_sxm-x52-nvl72-expert | DeepSeek-V4-Flash-0731 | 52 | expert | nvlink5_nvl72 | infiniband_ndr | 172 | 311.99 us | 320.5 tok/s | 3,205.2 tok/s | 86 x all_reduce span 52 on nvlink5_nvl72 (traversals 2.0) = 208.70 us; 86 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 103.29 us |
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
| DeepSeek-V4-Flash-0731 | 1 | array | array | DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x84 | 68,460 | 2,923.9 | 0.043 | 2,923.9 (68,460) | 2,778.1 (92,450) | 0.95x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 2 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 2,513.2 | 0.011 | 2,513.2 (227,385) | 1,809.5 (1,525,425) | 0.72x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 4 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 2,513.2 | 0.011 | 2,513.2 (227,385) | 1,809.5 (1,525,425) | 0.72x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 8 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 2,513.2 | 0.011 | 2,513.2 (227,385) | 1,809.5 (1,525,425) | 0.72x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 16 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 2,513.2 | 0.011 | 2,513.2 (227,385) | 1,809.5 (1,525,425) | 0.72x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 2,513.2 | 0.011 | 2,513.2 (227,385) | 1,809.5 (1,525,425) | 0.72x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 64 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 2,479.0 | 0.011 | 2,479.0 (227,385) | 1,809.5 (1,525,425) | 0.73x | layer_fixed_latency |
| DeepSeek-V4-Flash-0731 | 256 | array | array | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279 | 227,385 | 1,510.7 | 0.007 | 1,510.7 (227,385) | 1,463.1 (1,525,425) | 0.97x | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33-romfill | 1,525,425 | 610.6 | 0.000 | 561.8 (277,100) | 610.6 (1,525,425) | 1.09x | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33 | 1,525,425 | 175.2 | 0.000 | 140.9 (277,100) | 175.2 (1,525,425) | 1.24x | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | sram | 377,339.6 | 26,113.2 | 26,113.2 | 14.45x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 377,339.6 | 26,113.2 | 26,113.2 | 14.45x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 377,339.6 | 26,113.2 | 26,113.2 | 14.45x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 377,339.6 | 26,113.2 | 26,113.2 | 14.45x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 377,339.6 | 26,113.2 | 26,113.2 | 14.45x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 377,339.6 | 26,113.2 | 29,431.2 | 14.45x | 1.13x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 377,339.6 | 26,113.2 | 42,472.9 | 14.45x | 1.63x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 405,180.2 | 26,113.2 | 95,587.5 | 15.52x | 3.66x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 621,536.4 | 26,113.2 | 193,404.5 | 23.80x | 7.41x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 717,446.6 | 26,113.2 | 356,877.4 | 27.47x | 13.67x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 683,602.7 | 692,317.7 | 692,317.7 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 683,602.7 | 692,317.7 | 692,317.7 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 683,602.7 | 692,317.7 | 692,317.7 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 683,602.7 | 692,317.7 | 692,317.7 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 683,602.7 | 692,317.7 | 692,317.7 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 683,602.7 | 692,317.7 | 692,317.7 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 683,602.7 | 692,317.7 | 692,317.7 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 683,602.7 | 692,317.7 | 692,317.7 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 683,602.7 | 692,317.7 | 692,317.7 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 711,019.8 | 715,351.2 | 713,822.9 | 0.99x | 1.00x | kv_read | kv_read | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 377,339.6 | 0.247 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 683,602.7 | 0.448 | kv_read | 1.81x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perstream | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perregion | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 377,339.6 | 0.247 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 683,602.7 | 0.448 | kv_read | 1.81x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perstream | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perregion | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 377,339.6 | 0.247 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 683,602.7 | 0.448 | kv_read | 1.81x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perstream | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perregion | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 377,339.6 | 0.247 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 683,602.7 | 0.448 | kv_read | 1.81x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perstream | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perregion | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 377,339.6 | 0.247 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 683,602.7 | 0.448 | kv_read | 1.81x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perstream | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perregion | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 377,339.6 | 0.247 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 683,602.7 | 0.448 | kv_read | 1.81x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perstream | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-perregion | 227,385 | 1.00 | 1.10 | 29,431.2 | 0.129 | weight_read | 0.08x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33 | 1,525,425 | 1.00 | 1.00 | 377,339.6 | 0.247 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 683,602.7 | 0.448 | kv_read | 1.81x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perstream | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x279-perregion | 227,385 | 1.00 | 1.47 | 42,472.9 | 0.187 | weight_read | 0.11x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.83x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x349 | 284,435 | 1.00 | 1.00 | 405,180.2 | 1.425 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 683,602.7 | 0.448 | kv_read | 1.69x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perstream | 227,385 | 1.00 | 1.00 | 26,113.2 | 0.115 | weight_read | 0.06x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.71x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33-perregion | 1,525,425 | 1.00 | 2.80 | 95,587.5 | 0.063 | weight_read | 0.24x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.71x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33 | 1,525,425 | 1.00 | 1.00 | 621,536.4 | 0.407 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 683,602.7 | 0.448 | kv_read | 1.10x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perstream | 227,385 | 1.00 | 3.67 | 26,113.2 | 0.115 | weight_read | 0.04x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33-perregion | 1,525,425 | 1.00 | 5.64 | 193,404.5 | 0.127 | weight_read | 0.31x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.00 | 692,317.7 | 0.454 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33 | 1,525,425 | 1.00 | 1.00 | 717,446.6 | 0.470 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-romfill | 1,525,425 | 40.23 | 1.00 | 711,019.8 | 0.466 | kv_read | 0.99x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x279-perstream | 227,385 | 1.00 | 14.68 | 26,113.2 | 0.115 | weight_read | 0.04x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perstream-romfill | 1,525,425 | 135.19 | 2.19 | 715,351.2 | 0.469 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x33-perregion | 1,525,425 | 1.00 | 8.63 | 356,877.4 | 0.234 | weight_read | 0.50x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x33-perregion-romfill | 1,525,425 | 135.19 | 1.17 | 713,822.9 | 0.468 | kv_read | 0.99x |

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
| DeepSeek-V4-Flash-0731 | 1 | 10 | 4.69 | 3.22 | 1.45x |
| DeepSeek-V4-Flash-0731 | 2 | 10 | 7.13 | 4.05 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 10 | 9.13 | 4.92 | 1.86x |
| DeepSeek-V4-Flash-0731 | 8 | 10 | 9.91 | 5.76 | 1.72x |
| DeepSeek-V4-Flash-0731 | 16 | 10 | 10.00 | 6.50 | 1.54x |
| DeepSeek-V4-Flash-0731 | 32 | 10 | 10.00 | 7.09 | 1.41x |
| DeepSeek-V4-Flash-0731 | 64 | 10 | 10.00 | 7.48 | 1.34x |
| DeepSeek-V4-Flash-0731 | 1 | 16 | 5.14 | 3.70 | 1.39x |
| DeepSeek-V4-Flash-0731 | 2 | 16 | 8.56 | 4.83 | 1.77x |
| DeepSeek-V4-Flash-0731 | 4 | 16 | 12.41 | 6.15 | 2.02x |
| DeepSeek-V4-Flash-0731 | 8 | 16 | 15.08 | 7.51 | 2.01x |
| DeepSeek-V4-Flash-0731 | 16 | 16 | 15.91 | 8.79 | 1.81x |
| DeepSeek-V4-Flash-0731 | 32 | 16 | 16.00 | 9.86 | 1.62x |
| DeepSeek-V4-Flash-0731 | 64 | 16 | 16.00 | 10.60 | 1.51x |
| DeepSeek-V4-Flash-0731 | 256 | 16 | 16.00 | 11.05 | 1.45x |
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
| DeepSeek-V4-Flash-0731 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 22 | 9.33 | 5.36 | 1.74x |
| DeepSeek-V4-Flash-0731 | 4 | 22 | 14.51 | 7.03 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 22 | 19.19 | 8.83 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 22 | 21.49 | 10.61 | 2.03x |
| DeepSeek-V4-Flash-0731 | 32 | 22 | 21.96 | 12.14 | 1.81x |
| DeepSeek-V4-Flash-0731 | 64 | 22 | 22.00 | 13.24 | 1.66x |
| DeepSeek-V4-Flash-0731 | 256 | 22 | 22.00 | 13.91 | 1.58x |
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
| DeepSeek-V4-Flash-0731 | 1 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 43 | 10.47 | 6.49 | 1.61x |
| DeepSeek-V4-Flash-0731 | 4 | 43 | 18.07 | 9.00 | 2.01x |
| DeepSeek-V4-Flash-0731 | 8 | 43 | 27.82 | 11.92 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 43 | 36.58 | 15.07 | 2.43x |
| DeepSeek-V4-Flash-0731 | 32 | 43 | 41.25 | 18.02 | 2.29x |
| DeepSeek-V4-Flash-0731 | 64 | 43 | 42.61 | 20.26 | 2.10x |
| DeepSeek-V4-Flash-0731 | 256 | 43 | 42.89 | 21.69 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 46 | 10.55 | 6.61 | 1.60x |
| DeepSeek-V4-Flash-0731 | 4 | 46 | 18.36 | 9.19 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 46 | 28.60 | 12.24 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 46 | 38.22 | 15.56 | 2.46x |
| DeepSeek-V4-Flash-0731 | 32 | 46 | 43.69 | 18.69 | 2.34x |
| DeepSeek-V4-Flash-0731 | 64 | 46 | 45.43 | 21.07 | 2.16x |
| DeepSeek-V4-Flash-0731 | 256 | 46 | 45.83 | 22.61 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1024 | 46 | 45.83 | 22.63 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1 | 51 | 5.71 | 4.80 | 1.19x |
| DeepSeek-V4-Flash-0731 | 2 | 51 | 10.67 | 6.79 | 1.57x |
| DeepSeek-V4-Flash-0731 | 4 | 51 | 18.77 | 9.49 | 1.98x |
| DeepSeek-V4-Flash-0731 | 8 | 51 | 29.76 | 12.74 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 51 | 40.71 | 16.32 | 2.49x |
| DeepSeek-V4-Flash-0731 | 32 | 51 | 47.56 | 19.74 | 2.41x |
| DeepSeek-V4-Flash-0731 | 64 | 51 | 50.03 | 22.37 | 2.24x |
| DeepSeek-V4-Flash-0731 | 256 | 51 | 50.68 | 24.07 | 2.11x |
| DeepSeek-V4-Flash-0731 | 1024 | 51 | 50.68 | 24.09 | 2.10x |
| DeepSeek-V4-Flash-0731 | 1 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 2 | 52 | 10.70 | 6.83 | 1.57x |
| DeepSeek-V4-Flash-0731 | 4 | 52 | 18.84 | 9.55 | 1.97x |
| DeepSeek-V4-Flash-0731 | 8 | 52 | 29.98 | 12.84 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 52 | 41.18 | 16.47 | 2.50x |
| DeepSeek-V4-Flash-0731 | 32 | 52 | 48.30 | 19.94 | 2.42x |
| DeepSeek-V4-Flash-0731 | 64 | 52 | 50.93 | 22.62 | 2.25x |
| DeepSeek-V4-Flash-0731 | 256 | 52 | 51.64 | 24.35 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1024 | 52 | 51.64 | 24.37 | 2.12x |
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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 890.50 | 49.8% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 268.49 | 79.5% |

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
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,049.5 | 292,798.7 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,049.5 | 292,798.7 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,049.5 | 292,798.7 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,049.5 | 292,798.7 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,049.5 | 292,798.7 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,049.5 | 292,798.7 |
| DeepSeek-V4-Flash-0731 | 64 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,049.5 | 292,798.7 |
| DeepSeek-V4-Flash-0731 | 256 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,049.5 | 292,798.7 |
| DeepSeek-V4-Flash-0731 | 1024 | 8.34% | 20.0 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 462.6 | 473,700.3 |
| DeepSeek-V4-Flash-0731 | 4096 | 29.40% | 51.0 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 116.1 | 475,451.5 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 215 |
| gpu | layer_fixed_latency | 210 |
| gpu | link_latency | 900 |
| gpu | thermal | 10 |
| gpu | weight_read | 315 |
| rom | compute | 132 |
| rom | infeasible | 2742 |
| rom | kv_read | 57 |
| rom | layer_fixed_latency | 141 |
| rom | link_latency | 499 |
| rom | thermal | 14 |
| rom | weight_read | 255 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 215 |
| rom | CAPACITY | 2742 |

## Mechanical consistency audit

**FAIL** over 84,873 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x31', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x35', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x47', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x60', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x84', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x90', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x101', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x102', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x120', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x31', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x35', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x47', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x60', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x84', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x90', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x101', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x102', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x120', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x31', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x35', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x47', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x60', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x84', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x90', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x101', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x102', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x120', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x31', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x35', 'DeepSeek-V4-Flash-0731', 1)

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

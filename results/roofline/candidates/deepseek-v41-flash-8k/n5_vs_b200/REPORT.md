# Area-constrained roofline: n5_vs_b200-deepseek-v41-flash-8k

> CANDIDATE MODEL under n5_vs_b200: DeepSeek-V4.1-Flash at 8,192 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 368x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 170 devices. On the GPU side the correction reaches 31x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 48 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash takes 86 x 815 mm2 (70,090 mm2, array, KV in SRAM) at 9,766 tok/s per user and 139 tok/s per 1,000 mm2, holding 1 session, against 44 copies of one unified HBM die at the same silicon: 2.4x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash on 145,885 mm2 of ROM silicon at 16,180 tok/s per user against 145,600 mm2 of b200_sxm-x91-nvl72-hybrid at 3,980 tok/s: **4.1x**, ROM binding on `compute` and the GPU on `link_latency`. It holds 1,813,419 resident sessions against the GPU cluster's 1,423,991. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 9.01x to it.** At 107,580 mm2 on DeepSeek-V4.1-Flash the pipeline-only GPU delivers 472.85 tok/s and the same silicon running tensor delivers 4,259 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4.1-Flash, ROM binding on `link_latency`) to 3.34x (DeepSeek-V4.1-Flash, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 793 to 76,038 tok/s, and its rate with every slot occupied from 75,374 to 76,038. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 95 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 567 us over NVLink, capping per-user decode at 1,763 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 171.8 us and cap it at 5,821 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 10 operating points and an array 8; on tokens per second per square millimetre the same points go 9 to the array and 1 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 90 of 5062 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 185.3x of aggregate throughput (DeepSeek-V4.1-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 43.84x, on DeepSeek-V4.1-Flash at batch 4096, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 314 of 5,062 feasible points (6.2%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `DeepSeek-V4.1-Flash/b200_sxm-x4-pipeline` at batch 4096 on 6,400 mm2, throttled 1.12x from 21 to 19 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 89% weight read against 89.3% weight read. The ROM sweep is not what melts it.


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

### DeepSeek-V4.1-Flash at 8,192 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-tensor-x86`** -- 86 x 815 mm2 reticle dies, 70,090 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **9,766.0 tok/s per user** (0.10 ms/token), binding on `link_latency`
- **139.3 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 9,766 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 4,360 W at 0.062 W/mm2, 446.4 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 44 copies of one unified HBM die -- `b200_sxm-x44-nvl72-tensor`, 70,400 mm2, area ratio 0.9956 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 70,090 | 70,400 | 0.9956 |
| user tok/s | 9,766.0 | 3,992.2 | 2.45x |
| aggregate tok/s | 9,766 | 3,992 | 0.47x |
| resident sessions | 1 | 662,152 | -- |
| J/token | 0.4464 | 5.2360 | 11.7x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 662,152 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x67-nvl72-tensor` at 107,200 mm2 and 4,259.0 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 138,550 | 15,490.3 | 111.8 | 1,722,242 | 3.92x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-array-hw-hybrid-x179` | 145,885 | 16,180.4 | 110.9 | 1,813,419 | 4.07x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x85` | 69,275 | 9,296.0 | 134.2 | 1 | 2.34x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-tensor-x86` | 70,090 | 9,766.0 | 139.3 | 1 | 2.45x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x86` | 70,090 | 9,766.0 | 139.3 | -- | 139.3 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x87` | 70,905 | 9,865.6 | 139.1 | 122.1 | 139.3 | stop |
| `ROM-N5-native-HBMKV-array-hw-tensor-x98` | 79,870 | 10,749.2 | 134.6 | 100.5 | 139.3 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x151-romfill` | 123,065 | 13,965.9 | 113.5 | 79.3 | 139.3 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 143,440 | 16,049.0 | 111.9 | 85.7 | 139.3 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x179` | 145,885 | 16,180.4 | 110.9 | 84.6 | 139.3 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x86` **<-- recommended** | 70,090 | 86 | 9,766.0 | 9,766 | 139.3 | 1 | `link_latency` | 4,360 | 446.4 | `b200_sxm-x44-nvl72-tensor` | 2.45x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x87` | 70,905 | 87 | 9,865.6 | 9,866 | 139.1 | 1 | `link_latency` | 4,410 | 447.0 | `b200_sxm-x44-nvl72-tensor` | 2.47x |
| `ROM-N5-native-HBMKV-array-hw-tensor-x98` | 79,870 | 98 | 10,749.2 | 10,749 | 134.6 | 992,821 | `link_latency` | 6,203 | 577.1 | `b200_sxm-x50-nvl72-tensor` | 2.63x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x151-romfill` | 123,065 | 151 | 13,965.9 | 530,704 | 113.5 | 1,529,756 | `compute` | 17,095 | 947.5 | `b200_sxm-x77-nvl72-hybrid` | 3.62x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 143,440 | 176 | 16,049.0 | 706,155 | 111.9 | 1,783,027 | `compute` | 21,711 | 1,031.4 | `b200_sxm-x90-nvl72-hybrid` | 4.04x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x179` | 145,885 | 179 | 16,180.4 | 728,118 | 110.9 | 1,813,419 | `compute` | 22,271 | 1,047.6 | `b200_sxm-x91-nvl72-hybrid` | 4.07x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 312 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x86` | 70,090 | 9,766.0 | 139.3 | 1 |
| array | 312 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x179` | 145,885 | 16,180.4 | 110.9 | 1,813,419 |
| array | 312 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x85` | 69,275 | 9,296.0 | 134.2 | 1 |
| wafer | 72 | densest | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 5,892.7 | 63.7 | 174,250 |
| wafer | 72 | fastest | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 5,980.8 | 43.1 | 261,375 |
| wafer | 72 | smallest | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 5,892.7 | 63.7 | 174,250 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x179` | 145,885 | 16,180.4 | 728,118 | 1,813,419 | 22,271 | 1,047.6 | `compute` | `b200_sxm-x91-nvl72-hybrid` | 3,980.3 | 1,423,991 | 9,385.6 | 1.002 | 4.07x | 9.0x |
| 1 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 5,980.8 | 17,942 | 261,375 | 13,773 | 2,287.9 | `link_latency` | `b200_sxm-x87-nvl72-hybrid` | 3,948.4 | 1,359,154 | 9,095.5 | 0.996 | 1.51x | 4.0x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 143,440 | 16,049.0 | 706,155 | 1,783,027 | 21,711 | 1,031.4 | `compute` | `b200_sxm-x90-nvl72-hybrid` | 3,972.6 | 1,407,782 | 9,313.1 | 0.996 | 4.04x | 9.0x |
| 1 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 5,980.8 | -- | 261,375 | -- | 2,287.9 | -- | -- | -- | -- | -- | 1.034 | 0.37x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x179` | 145,885 | 16,180.4 | 728,118 | 1,813,419 | 22,271 | 527.5 | `compute` | `b200_sxm-x91-nvl72-hybrid` | 3,980.3 | 1,423,991 | 5,379.7 | 1.002 | 4.07x | 10.2x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 5,980.8 | 17,942 | 261,375 | 13,773 | 1,147.7 | `link_latency` | `b200_sxm-x87-nvl72-hybrid` | 3,948.4 | 1,359,154 | 5,234.6 | 0.996 | 1.51x | 4.6x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | 143,440 | 16,049.0 | 706,155 | 1,783,027 | 21,711 | 519.4 | `compute` | `b200_sxm-x90-nvl72-hybrid` | 3,972.6 | 1,407,782 | 5,343.4 | 0.996 | 4.04x | 10.3x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 5,980.8 | -- | 261,375 | -- | 1,147.7 | -- | -- | -- | -- | -- | 1.034 | 0.37x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x179` | 145,885 | 16,180.4 | 728,118 | 1,813,419 | 22,271 | 267.5 | `compute` | `b200_sxm-x91-nvl72-hybrid` | 3,714.1 | 1,423,991 | 3,068.6 | 1.002 | 4.36x | 11.5x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 5,953.6 | 23,814 | 348,500 | 16,578 | 696.1 | `link_latency` | `b200_sxm-x116-nvl72-hybrid` | 3,899.4 | 1,829,225 | 3,528.3 | 0.996 | 1.53x | 5.1x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 14,050.0 | 800,852 | 2,299,699 | 25,791 | 359.9 | `compute` | `b200_sxm-x116-nvl72-hybrid` | 3,899.4 | 1,829,225 | 3,528.3 | 0.997 | 3.60x | 9.8x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 5,953.6 | -- | 348,500 | -- | 696.1 | -- | -- | -- | -- | -- | 1.001 | 0.42x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x179` | 145,885 | 16,180.4 | 728,118 | 1,813,419 | 22,271 | 137.5 | `compute` | `b200_sxm-x91-nvl72-hybrid` | 3,283.5 | 1,423,991 | 1,904.9 | 1.002 | 4.93x | 13.9x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,939.2 | 47,513 | 697,001 | 33,154 | 697.8 | `link_latency` | `b200_sxm-x231-nvl72-hybrid` | 3,823.7 | 3,693,298 | 3,568.5 | 1.001 | 1.55x | 5.1x |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x179` | 145,885 | 16,180.4 | 728,118 | 1,813,419 | 22,271 | 72.5 | `compute` | `b200_sxm-x91-nvl72-hybrid` | 2,684.8 | 1,423,991 | 1,307.1 | 1.002 | 6.03x | 18.0x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,882.7 | 94,123 | 1,045,502 | 49,840 | 529.5 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 3,676.3 | 5,573,581 | 2,817.1 | 0.999 | 1.60x | 5.3x |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x179` | 145,885 | 16,180.4 | 728,118 | 1,813,419 | 22,271 | 40.0 | `compute` | `b200_sxm-x91-nvl72-hybrid` | 2,007.1 | 1,423,991 | 978.6 | 1.002 | 8.06x | 24.5x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,719.9 | 183,036 | 1,045,502 | 50,261 | 274.6 | `link_latency` | `b200_sxm-x347-nvl72-hybrid` | 3,191.2 | 5,573,581 | 1,789.1 | 0.999 | 1.79x | 6.5x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill` | 215,160 | 14,097.8 | 930,452 | 2,674,540 | 29,988 | 33.0 | `compute` | `b200_sxm-x134-nvl72-hybrid` | 1,722.0 | 2,120,993 | 833.2 | 1.004 | 8.19x | 25.2x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x3` | 138,675 | 5,468.3 | 935,083 | 261,375 | 20,628 | 46.4 | `compute` | `b200_sxm-x87-nvl72-hybrid` | 1,362.2 | 1,359,154 | 756.8 | 0.996 | 4.01x | 16.3x |
| 64 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x178` | 145,070 | 12,187.5 | 779,998 | 1,803,288 | 21,911 | 28.1 | `compute` | `b200_sxm-x91-nvl72-hybrid` | 1,398.8 | 1,423,991 | 763.3 | 0.996 | 8.71x | 27.2x |
| 64 | wafer reference | `ROM-N5-native-HBMKV-wafer-pipeline-x3` | 138,675 | 5,468.3 | -- | 261,375 | -- | 46.4 | -- | -- | -- | -- | -- | 1.046 | 0.45x wafer/array | -- |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 215,160 | 6,568.4 | 1,681,521 | 2,674,540 | 37,283 | 22.2 | `compute` | `b200_sxm-x134-nvl72-hybrid` | 851.0 | 2,120,993 | 431.7 | 1.004 | 7.72x | 19.5x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x8-romfill` | 369,800 | 4,549.8 | 2,065,592 | 697,001 | 48,239 | 35.6 | `compute` | `b200_sxm-x231-nvl72-hybrid` | 1,069.6 | 3,693,298 | 614.4 | 1.001 | 4.25x | 15.6x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | 2,511.0 | 2,571,231 | 3,444,484 | 50,804 | 19.8 | `compute` | `b200_sxm-x173-expert` | 485.3 | 2,736,101 | 156.1 | 1.001 | 5.17x | 7.9x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 3,096.2 | 3,170,512 | 1,045,502 | 70,074 | 22.1 | `compute` | `b200_sxm-x347-expert` | 674.0 | 5,537,764 | 210.3 | 0.999 | 4.59x | 9.5x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | 286,880 | 677.0 | 2,772,907 | 3,566,054 | 52,145 | 18.8 | `compute` | `b200_sxm-x179-expert` | 245.1 | 2,832,504 | 73.7 | 1.002 | 2.76x | 3.9x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,312.3 | 5,375,012 | 1,045,502 | 94,947 | 17.7 | `compute` | `b200_sxm-x347-expert` | 393.2 | 5,537,764 | 86.7 | 0.999 | 3.34x | 4.9x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x86` | 70,090 | array | SRAM | 1 |
| 2 | `ROM-N5-native-HBMKV-array-hw-tensor-x98` | 79,870 | array | HBM | 992,821 |
| 4-32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x151-romfill` | 123,065 | array | HBM | 1,529,756 |
| 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x179` | 145,885 | array | HBM | 1,813,419 |
| 256 | `ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 215,160 | array | HBM | 2,674,540 |
| 1024 | `ROM-N5-native-HBMKV-array-hw-hybrid-x340` | 277,100 | array | HBM | 3,444,484 |
| 4096 | `ROM-N5-native-HBMKV-wafer-hybrid-x8` | 369,800 | wafer | HBM | 697,001 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash | HBM | rom | 95, 98, 110, 113, 126, 132, 150, 151, 170, 176, 227, 264, 340, 352 |
| DeepSeek-V4.1-Flash | HBM | sram | 95, 98, 110, 113, 126, 132, 170, 176, 178, 179, 227, 264, 340, 352 |
| DeepSeek-V4.1-Flash | SRAM | rom | 85, 86, 87, 103, 113, 123, 164, 170, 227, 246, 328, 340 |
| DeepSeek-V4.1-Flash | SRAM | sram | 85, 86, 87, 103, 113, 123, 164, 170, 227, 246, 328, 340 |

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

- **314 of 5,062 feasible points (6.2%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 314.
- By area class: large array (5,000-40,000 mm2) 44, wafer (>=40,000 mm2) 270.
- By KV store: hbm 314.
- By batch: B=1 31, B=2 31, B=4 31, B=8 31, B=16 31, B=32 31, B=64 33, B=256 33, B=1024 31, B=4096 31.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 39% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 230 | 44 | 74.3% | 100.0% | 0.625 | 47% |
| gpu | wafer (>=40,000 mm2) | 1,760 | 270 | 48.9% | 100.0% | 0.625 | 72% |
| rom | large array (5,000-40,000 mm2) | 480 | 0 | 18.8% | 30.4% | 0.152 | 95% |
| rom | wafer (>=40,000 mm2) | 2,592 | 0 | 21.5% | 39.2% | 0.196 | 94% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `DeepSeek-V4.1-Flash/b200_sxm-x4-pipeline` | DeepSeek-V4.1-Flash | 4096 | 6,400 | hbm | 1.119x | 4,000.0 / 4,000.0 W | 35% | 18.6 | 20.8 |
| `DeepSeek-V4.1-Flash/b200_sxm-x4-pipeline` | DeepSeek-V4.1-Flash | 1024 | 6,400 | hbm | 1.067x | 4,000.0 / 4,000.0 W | 35% | 20.5 | 21.9 |
| `DeepSeek-V4.1-Flash/b200_sxm-x21-pipeline` | DeepSeek-V4.1-Flash | 4096 | 33,600 | hbm | 1.060x | 21,000.0 / 21,000.0 W | 35% | 21.3 | 22.5 |
| `DeepSeek-V4.1-Flash/b200_sxm-x22-pipeline` | DeepSeek-V4.1-Flash | 4096 | 35,200 | hbm | 1.059x | 22,000.0 / 22,000.0 W | 35% | 21.4 | 22.7 |
| `DeepSeek-V4.1-Flash/b200_sxm-x24-pipeline` | DeepSeek-V4.1-Flash | 4096 | 38,400 | hbm | 1.058x | 24,000.0 / 24,000.0 W | 35% | 21.8 | 23.1 |
| `DeepSeek-V4.1-Flash/b200_sxm-x29-pipeline` | DeepSeek-V4.1-Flash | 4096 | 46,400 | hbm | 1.056x | 29,000.0 / 29,000.0 W | 35% | 22.8 | 24.1 |
| `DeepSeek-V4.1-Flash/b200_sxm-x4-pipeline` | DeepSeek-V4.1-Flash | 256 | 6,400 | hbm | 1.055x | 4,000.0 / 4,000.0 W | 35% | 31.8 | 33.6 |
| `DeepSeek-V4.1-Flash/b200_sxm-x31-pipeline` | DeepSeek-V4.1-Flash | 4096 | 49,600 | hbm | 1.055x | 31,000.0 / 31,000.0 W | 35% | 23.3 | 24.5 |
| `DeepSeek-V4.1-Flash/b200_sxm-x38-pipeline` | DeepSeek-V4.1-Flash | 4096 | 60,800 | hbm | 1.053x | 38,000.0 / 38,000.0 W | 35% | 24.9 | 26.2 |
| `DeepSeek-V4.1-Flash/b200_sxm-x21-pipeline` | DeepSeek-V4.1-Flash | 1024 | 33,600 | hbm | 1.052x | 21,000.0 / 21,000.0 W | 35% | 37.5 | 39.4 |
| `DeepSeek-V4.1-Flash/b200_sxm-x43-pipeline` | DeepSeek-V4.1-Flash | 4096 | 68,800 | hbm | 1.052x | 43,000.0 / 43,000.0 W | 35% | 26.2 | 27.5 |
| `DeepSeek-V4.1-Flash/b200_sxm-x44-pipeline` | DeepSeek-V4.1-Flash | 4096 | 70,400 | hbm | 1.052x | 44,000.0 / 44,000.0 W | 35% | 26.4 | 27.8 |

The worst point's dynamic energy is weight read 89.3%, arithmetic 6.4%, kv read 4.1%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| DeepSeek-V4.1-Flash | 1 | 138,550 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 1.017091 | 20,618.0 | compute | `DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-hybrid` | 9.095478 | 41,336.0 | link_latency | 8.94x |
| DeepSeek-V4.1-Flash | 2 | 138,550 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 0.512283 | 20,618.0 | compute | `DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-hybrid` | 5.234590 | 41,336.0 | link_latency | 10.22x |
| DeepSeek-V4.1-Flash | 4 | 138,550 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 0.259879 | 20,618.0 | compute | `DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-hybrid` | 2.995070 | 44,049.6 | link_latency | 11.52x |
| DeepSeek-V4.1-Flash | 8 | 138,550 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 0.133677 | 20,618.0 | compute | `DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-hybrid` | 1.867067 | 48,394.2 | link_latency | 13.97x |
| DeepSeek-V4.1-Flash | 16 | 138,550 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 0.070576 | 20,618.0 | compute | `DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-hybrid` | 1.287173 | 54,318.3 | link_latency | 18.24x |
| DeepSeek-V4.1-Flash | 32 | 138,550 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170` | 0.039025 | 20,618.0 | compute | `DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-hybrid` | 0.967675 | 60,761.3 | link_latency | 24.80x |
| DeepSeek-V4.1-Flash | 64 | 185,005 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x227` | 0.034133 | 29,351.1 | weight_read | `DeepSeek-V4.1-Flash/b200_sxm-x116-nvl72-hybrid` | 0.803916 | 82,349.5 | weight_read | 23.55x |
| DeepSeek-V4.1-Flash | 256 | 215,160 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x264` | 0.022172 | 37,282.7 | compute | `DeepSeek-V4.1-Flash/b200_sxm-x134-nvl72-hybrid` | 0.431682 | 94,043.9 | link_latency | 19.47x |
| DeepSeek-V4.1-Flash | 1024 | 554,700 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 0.022102 | 70,073.6 | compute | `DeepSeek-V4.1-Flash/b200_sxm-x347-expert` | 0.210281 | 145,140.7 | link_latency | 9.51x |
| DeepSeek-V4.1-Flash | 4096 | 554,700 | `DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12` | 0.017665 | 94,947.0 | compute | `DeepSeek-V4.1-Flash/b200_sxm-x347-expert` | 0.086709 | 139,666.1 | link_latency | 4.91x |

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
| DeepSeek-V4.1-Flash | 8,192 | 552 B | 510.3 GB | 7.40 | 0.012 GB | 0.010 GB | 1,092.9 |

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
| DeepSeek-V4.1-Flash | 2 | 92,450 | 56,496.1 | wafer-pipeline | 5,892.7 | wafer-hybrid | 9.59x | 10,209.4 | pipeline | 4,176.2 | tensor | 2.44x | 5.53x | 1.41x | 0.25x |
| DeepSeek-V4.1-Flash | 3 | 138,675 | 62,858.0 | wafer-pipeline | 5,980.8 | wafer-hybrid | 10.51x | 11,607.0 | pipeline | 3,948.4 | hybrid | 2.94x | 5.42x | 1.51x | 0.28x |
| DeepSeek-V4.1-Flash | 4 | 184,900 | 63,174.2 | wafer-pipeline | 5,953.6 | wafer-hybrid | 10.61x | 12,459.9 | pipeline | 4,137.4 | hybrid | 3.01x | 5.07x | 1.44x | 0.28x |
| DeepSeek-V4.1-Flash | 6 | 277,350 | 64,398.1 | wafer-pipeline | 5,946.4 | wafer-hybrid | 10.83x | 13,435.7 | pipeline | 4,096.1 | hybrid | 3.28x | 4.79x | 1.45x | 0.30x |
| DeepSeek-V4.1-Flash | 8 | 369,800 | 65,028.0 | wafer-pipeline | 5,939.2 | wafer-hybrid | 10.95x | 13,995.8 | pipeline | 4,059.8 | hybrid | 3.45x | 4.65x | 1.46x | 0.31x |
| DeepSeek-V4.1-Flash | 12 | 554,700 | 65,670.3 | wafer-pipeline | 5,924.9 | wafer-hybrid | 11.08x | 14,602.8 | pipeline | 4,120.3 | hybrid | 3.54x | 4.50x | 1.44x | 0.32x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.25x to 0.32x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash | 1 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x179 | 145,885 | 16,180.4 | 728,118.5 | compute | DeepSeek-V4.1-Flash/b200_sxm-x91-nvl72-hybrid | 145,600 | 1.00x | hybrid | 196.93 | 3,980.3 | 7,960.7 | link_latency | 4.07x | 16.92x | 34.22x | 4.07x |
| DeepSeek-V4.1-Flash | 1 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x85 | 69,275 | 9,296.0 | 9,296.0 | link_latency | DeepSeek-V4.1-Flash/b200_sxm-x43-nvl72-tensor | 68,800 | 1.01x | tensor | 194.67 | 3,975.4 | 3,975.4 | link_latency | 2.34x | 0.46x | 19.66x | 2.34x |
| DeepSeek-V4.1-Flash | 2 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x179 | 145,885 | 16,180.4 | 728,118.5 | compute | DeepSeek-V4.1-Flash/b200_sxm-x91-nvl72-hybrid | 145,600 | 1.00x | hybrid | 196.93 | 3,980.3 | 7,960.7 | link_latency | 4.07x | 16.92x | 34.22x | 4.07x |
| DeepSeek-V4.1-Flash | 2 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x95 | 77,425 | 8,937.8 | 17,875.5 | link_latency | DeepSeek-V4.1-Flash/b200_sxm-x48-nvl72-tensor | 76,800 | 1.01x | tensor | 197.35 | 3,792.6 | 7,585.1 | link_latency | 2.36x | 0.79x | 18.90x | 2.36x |
| DeepSeek-V4.1-Flash | 4 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x179 | 145,885 | 16,180.4 | 728,118.5 | compute | DeepSeek-V4.1-Flash/b200_sxm-x91-nvl72-hybrid | 145,600 | 1.00x | hybrid | 199.83 | 3,714.1 | 14,856.5 | link_latency | 4.36x | 16.92x | 34.22x | 4.36x |
| DeepSeek-V4.1-Flash | 4 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x95 | 77,425 | 7,056.3 | 28,225.1 | link_latency | DeepSeek-V4.1-Flash/b200_sxm-x48-nvl72-tensor | 76,800 | 1.01x | tensor | 202.70 | 3,367.0 | 13,467.9 | link_latency | 2.10x | 1.24x | 14.92x | 2.10x |
| DeepSeek-V4.1-Flash | 8 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x179 | 145,885 | 16,180.4 | 728,118.5 | compute | DeepSeek-V4.1-Flash/b200_sxm-x91-nvl72-hybrid | 145,600 | 1.00x | hybrid | 205.62 | 3,283.5 | 26,267.7 | link_latency | 4.93x | 16.92x | 34.22x | 4.93x |
| DeepSeek-V4.1-Flash | 8 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x95 | 77,425 | 4,965.6 | 39,725.1 | compute | DeepSeek-V4.1-Flash/b200_sxm-x48-nvl72-tensor | 76,800 | 1.01x | tensor | 213.39 | 2,769.4 | 22,155.1 | link_latency | 1.79x | 1.75x | 10.50x | 1.79x |
| DeepSeek-V4.1-Flash | 16 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x179 | 145,885 | 16,180.4 | 728,118.5 | compute | DeepSeek-V4.1-Flash/b200_sxm-x91-nvl72-hybrid | 145,600 | 1.00x | hybrid | 217.21 | 2,684.8 | 42,956.1 | link_latency | 6.03x | 16.92x | 34.22x | 6.03x |
| DeepSeek-V4.1-Flash | 16 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x95 | 77,425 | 3,118.0 | 49,888.3 | compute | DeepSeek-V4.1-Flash/b200_sxm-x48-nvl72-tensor | 76,800 | 1.01x | tensor | 234.78 | 2,084.6 | 33,352.9 | link_latency | 1.50x | 1.50x | 6.59x | 1.50x |
| DeepSeek-V4.1-Flash | 32 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x179 | 145,885 | 16,180.4 | 728,118.5 | compute | DeepSeek-V4.1-Flash/b200_sxm-x91-nvl72-hybrid | 145,600 | 1.00x | hybrid | 240.39 | 2,007.1 | 64,226.9 | link_latency | 8.06x | 11.34x | 34.22x | 8.06x |
| DeepSeek-V4.1-Flash | 32 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x95 | 77,425 | 2,296.5 | 73,486.4 | compute | DeepSeek-V4.1-Flash/b200_sxm-x48-nvl72-tensor | 76,800 | 1.01x | tensor | 277.56 | 1,462.2 | 46,788.9 | weight_read | 1.57x | 1.57x | 4.86x | 1.57x |
| DeepSeek-V4.1-Flash | 64 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x264-romfill | 215,160 | 14,097.8 | 930,451.9 | compute | DeepSeek-V4.1-Flash/b200_sxm-x134-nvl72-hybrid | 214,400 | 1.00x | hybrid | 286.75 | 1,722.0 | 110,206.8 | link_latency | 8.19x | 8.44x | 29.81x | 8.19x |
| DeepSeek-V4.1-Flash | 64 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x95 | 77,425 | 1,166.9 | 74,682.8 | compute | DeepSeek-V4.1-Flash/b200_sxm-x48-nvl72-tensor | 76,800 | 1.01x | tensor | 363.12 | 1,007.1 | 64,457.4 | weight_read | 1.16x | 1.16x | 2.75x | 1.16x |
| DeepSeek-V4.1-Flash | 256 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x264 | 215,160 | 6,568.4 | 1,681,520.9 | compute | DeepSeek-V4.1-Flash/b200_sxm-x134-nvl72-hybrid | 214,400 | 1.00x | hybrid | 564.92 | 851.0 | 217,854.7 | link_latency | 7.72x | 7.72x | 18.23x | 7.72x |
| DeepSeek-V4.1-Flash | 256 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x95 | 77,425 | 296.1 | 75,800.0 | compute | DeepSeek-V4.1-Flash/b200_sxm-x48-nvl72-tensor | 76,800 | 1.01x | tensor | 876.49 | 544.4 | 139,361.2 | link_latency | 0.54x | 0.54x | 1.53x | 0.54x |
| DeepSeek-V4.1-Flash | 1024 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3,096.2 | 3,170,512.0 | compute | DeepSeek-V4.1-Flash/b200_sxm-x347-expert | 555,200 | 1.00x | expert | 701.40 | 674.0 | 690,222.4 | link_latency | 4.59x | 4.59x | 10.89x | 4.59x |
| DeepSeek-V4.1-Flash | 1024 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x95 | 77,425 | 74.2 | 75,989.9 | compute | DeepSeek-V4.1-Flash/b200_sxm-x48-nvl72-tensor | 76,800 | 1.01x | tensor | 2,929.95 | 253.8 | 259,893.4 | link_latency | 0.29x | 0.29x | 1.10x | 0.29x |
| DeepSeek-V4.1-Flash | 4096 | fastest | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,312.3 | 5,375,012.0 | compute | DeepSeek-V4.1-Flash/b200_sxm-x347-expert | 555,200 | 1.00x | expert | 1,742.38 | 393.2 | 1,610,741.2 | link_latency | 3.34x | 3.34x | 12.30x | 3.34x |
| DeepSeek-V4.1-Flash | 4096 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x95 | 77,425 | 18.6 | 76,037.5 | compute | DeepSeek-V4.1-Flash/b200_sxm-x48-hybrid | 76,800 | 1.01x | hybrid | 2,532.32 | 118.3 | 484,492.1 | weight_read | 0.16x | 0.16x | 0.68x | 0.16x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash | 4 | 6,400 | 194.05 | 194.05 | 1,413.4 | 1,413.4 |
| DeepSeek-V4.1-Flash | 21 | 33,600 | 194.60 | 194.60 | 3,327.3 | 3,327.3 |
| DeepSeek-V4.1-Flash | 22 | 35,200 | 194.61 | 194.61 | 3,376.2 | 3,376.2 |
| DeepSeek-V4.1-Flash | 24 | 38,400 | 194.62 | 194.62 | 3,465.4 | 3,465.4 |
| DeepSeek-V4.1-Flash | 29 | 46,400 | 194.64 | 194.64 | 3,648.0 | 3,648.0 |
| DeepSeek-V4.1-Flash | 31 | 49,600 | 194.64 | 194.64 | 3,708.5 | 3,708.5 |
| DeepSeek-V4.1-Flash | 38 | 60,800 | 194.66 | 194.66 | 3,880.5 | 3,880.5 |
| DeepSeek-V4.1-Flash | 43 | 68,800 | 194.67 | 194.67 | 3,975.4 | 3,975.4 |
| DeepSeek-V4.1-Flash | 44 | 70,400 | 194.67 | 194.67 | 3,992.2 | 3,992.2 |
| DeepSeek-V4.1-Flash | 48 | 76,800 | 194.67 | 194.67 | 4,053.9 | 4,053.9 |
| DeepSeek-V4.1-Flash | 50 | 80,000 | 194.68 | 194.68 | 4,081.6 | 4,081.6 |
| DeepSeek-V4.1-Flash | 52 | 83,200 | 194.68 | 194.68 | 4,107.6 | 4,107.6 |
| DeepSeek-V4.1-Flash | 56 | 89,600 | 194.68 | 194.68 | 4,154.7 | 4,154.7 |
| DeepSeek-V4.1-Flash | 58 | 92,800 | 194.68 | 194.68 | 4,176.2 | 4,176.2 |
| DeepSeek-V4.1-Flash | 63 | 100,800 | 194.69 | 194.69 | 4,224.7 | 4,224.7 |
| DeepSeek-V4.1-Flash | 64 | 102,400 | 194.69 | 194.69 | 4,233.6 | 4,233.6 |
| DeepSeek-V4.1-Flash | 67 | 107,200 | 194.69 | 194.69 | 4,259.0 | 4,259.0 |
| DeepSeek-V4.1-Flash | 76 | 121,600 | 196.93 | 196.93 | 3,846.6 | 3,846.6 |
| DeepSeek-V4.1-Flash | 77 | 123,200 | 196.93 | 196.93 | 3,856.8 | 3,856.8 |
| DeepSeek-V4.1-Flash | 84 | 134,400 | 196.93 | 196.93 | 3,922.7 | 3,922.7 |
| DeepSeek-V4.1-Flash | 87 | 139,200 | 196.93 | 196.93 | 3,948.4 | 3,948.4 |
| DeepSeek-V4.1-Flash | 90 | 144,000 | 196.93 | 196.93 | 3,972.6 | 3,972.6 |
| DeepSeek-V4.1-Flash | 91 | 145,600 | 196.93 | 196.93 | 3,980.3 | 3,980.3 |
| DeepSeek-V4.1-Flash | 116 | 185,600 | 196.93 | 196.93 | 4,137.4 | 4,137.4 |
| DeepSeek-V4.1-Flash | 125 | 200,000 | 196.93 | 196.93 | 4,180.6 | 4,180.6 |
| DeepSeek-V4.1-Flash | 134 | 214,400 | 196.93 | 196.93 | 4,218.8 | 4,218.8 |
| DeepSeek-V4.1-Flash | 167 | 267,200 | 199.16 | 199.16 | 4,075.2 | 4,075.2 |
| DeepSeek-V4.1-Flash | 173 | 276,800 | 199.16 | 199.16 | 4,096.1 | 4,096.1 |
| DeepSeek-V4.1-Flash | 179 | 286,400 | 199.16 | 199.16 | 4,115.9 | 4,115.9 |
| DeepSeek-V4.1-Flash | 231 | 369,600 | 201.40 | 201.40 | 4,059.8 | 4,059.8 |
| DeepSeek-V4.1-Flash | 347 | 555,200 | 203.63 | 203.63 | 4,120.3 | 4,120.3 |

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
| DeepSeek-V4.1-Flash | 4 | 6,400 | 472.9 | 1,413.4 | — | tensor | 194.05 | 27.4% | weight_read |
| DeepSeek-V4.1-Flash | 21 | 33,600 | 472.9 | 3,327.3 | 2,013.8 | tensor | 194.60 | 64.8% | link_latency |
| DeepSeek-V4.1-Flash | 22 | 35,200 | 472.9 | 3,376.2 | 2,068.2 | tensor | 194.61 | 65.7% | link_latency |
| DeepSeek-V4.1-Flash | 24 | 38,400 | 472.9 | 3,465.4 | 2,171.0 | tensor | 194.62 | 67.4% | link_latency |
| DeepSeek-V4.1-Flash | 29 | 46,400 | 472.9 | 3,648.0 | 2,045.4 | tensor | 194.64 | 71.0% | link_latency |
| DeepSeek-V4.1-Flash | 31 | 49,600 | 472.9 | 3,708.5 | 2,123.3 | tensor | 194.64 | 72.2% | link_latency |
| DeepSeek-V4.1-Flash | 38 | 60,800 | 472.9 | 3,880.5 | 2,090.6 | tensor | 194.66 | 75.5% | link_latency |
| DeepSeek-V4.1-Flash | 43 | 68,800 | 472.9 | 3,975.4 | 2,013.7 | tensor | 194.67 | 77.4% | link_latency |
| DeepSeek-V4.1-Flash | 44 | 70,400 | 472.9 | 3,992.2 | 2,040.0 | tensor | 194.67 | 77.7% | link_latency |
| DeepSeek-V4.1-Flash | 48 | 76,800 | 472.9 | 4,053.9 | 2,139.8 | tensor | 194.67 | 78.9% | link_latency |
| DeepSeek-V4.1-Flash | 50 | 80,000 | 472.9 | 4,081.6 | 2,001.0 | tensor | 194.68 | 79.5% | link_latency |
| DeepSeek-V4.1-Flash | 52 | 83,200 | 472.9 | 4,107.6 | 2,045.3 | tensor | 194.68 | 80.0% | link_latency |
| DeepSeek-V4.1-Flash | 56 | 89,600 | 472.9 | 4,154.7 | 2,129.7 | tensor | 194.68 | 80.9% | link_latency |
| DeepSeek-V4.1-Flash | 58 | 92,800 | 472.9 | 4,176.2 | 2,008.7 | tensor | 194.68 | 81.3% | link_latency |
| DeepSeek-V4.1-Flash | 63 | 100,800 | 472.9 | 4,224.7 | 2,101.8 | tensor | 194.69 | 82.2% | link_latency |
| DeepSeek-V4.1-Flash | 64 | 102,400 | 472.9 | 4,233.6 | 2,119.6 | tensor | 194.69 | 82.4% | link_latency |
| DeepSeek-V4.1-Flash | 67 | 107,200 | 472.9 | 4,259.0 | 2,029.2 | tensor | 194.69 | 82.9% | link_latency |
| DeepSeek-V4.1-Flash | 76 | 121,600 | 472.9 | 1,722.3 | 3,846.6 | hybrid | 196.93 | 75.8% | link_latency |
| DeepSeek-V4.1-Flash | 77 | 123,200 | 472.9 | 1,723.3 | 3,856.8 | hybrid | 196.93 | 76.0% | link_latency |
| DeepSeek-V4.1-Flash | 84 | 134,400 | 472.9 | 1,729.8 | 3,922.7 | hybrid | 196.93 | 77.2% | link_latency |
| DeepSeek-V4.1-Flash | 87 | 139,200 | 472.9 | 1,732.3 | 3,948.4 | hybrid | 196.93 | 77.8% | link_latency |
| DeepSeek-V4.1-Flash | 90 | 144,000 | 472.9 | 1,734.6 | 3,972.6 | hybrid | 196.93 | 78.2% | link_latency |
| DeepSeek-V4.1-Flash | 91 | 145,600 | 472.9 | 1,735.4 | 3,980.3 | hybrid | 196.93 | 78.4% | link_latency |
| DeepSeek-V4.1-Flash | 116 | 185,600 | 472.9 | 1,749.8 | 4,137.4 | hybrid | 196.93 | 81.5% | link_latency |
| DeepSeek-V4.1-Flash | 125 | 200,000 | 472.9 | 1,753.7 | 4,180.6 | hybrid | 196.93 | 82.3% | link_latency |
| DeepSeek-V4.1-Flash | 134 | 214,400 | 472.9 | 1,757.0 | 4,218.8 | hybrid | 196.93 | 83.1% | link_latency |
| DeepSeek-V4.1-Flash | 167 | 267,200 | 472.9 | 1,741.0 | 4,075.2 | hybrid | 199.16 | 81.2% | link_latency |
| DeepSeek-V4.1-Flash | 173 | 276,800 | 472.9 | 1,742.3 | 4,096.1 | hybrid | 199.16 | 81.6% | link_latency |
| DeepSeek-V4.1-Flash | 179 | 286,400 | 472.9 | 1,743.5 | 4,115.9 | hybrid | 199.16 | 82.0% | link_latency |
| DeepSeek-V4.1-Flash | 231 | 369,600 | 472.9 | 1,738.8 | 4,059.8 | hybrid | 201.40 | 81.8% | link_latency |
| DeepSeek-V4.1-Flash | 347 | 555,200 | 472.9 | 1,740.1 | 4,120.3 | hybrid | 203.63 | 83.9% | link_latency |

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
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x87 | DeepSeek-V4.1-Flash | 87 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x86 | DeepSeek-V4.1-Flash | 86 | tensor | rom_package_ucie | rom_board_serdes | 160 | 73.76 us | 1,355.7 tok/s | 13,556.7 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 22 on rom_board_serdes (traversals 8.8) = 71.70 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x87 | DeepSeek-V4.1-Flash | 87 | hybrid | rom_package_ucie | rom_board_serdes | 101 | 4.28 us | 23,363.0 tok/s | 233,630.3 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 21 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.22 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x87 | DeepSeek-V4.1-Flash | 87 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-tensor-x85 | DeepSeek-V4.1-Flash | 85 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash | 2 | tensor | on_wafer_n5 | rom_wafer_serdes | 160 | 171.80 us | 582.1 tok/s | 5,820.6 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 17.80 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hybrid-x87 | DeepSeek-V4.1-Flash | 87 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 81 | 154.10 us | 648.9 tok/s | 6,489.2 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x179 | DeepSeek-V4.1-Flash | 179 | pipeline | rom_package_ucie | rom_board_serdes | 39 | 1.33 us | 75,301.2 tok/s | 753,012.0 tok/s | 30 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.38 us; 9 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.95 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x98 | DeepSeek-V4.1-Flash | 98 | tensor | rom_package_ucie | rom_board_serdes | 160 | 73.77 us | 1,355.5 tok/s | 13,555.4 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 80 x all_reduce span 25 on rom_board_serdes (traversals 8.8) = 71.71 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x176 | DeepSeek-V4.1-Flash | 176 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 6.18 us | 16,174.3 tok/s | 161,742.5 tok/s | 80 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.06 us; 39 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.12 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-pipeline-x178 | DeepSeek-V4.1-Flash | 178 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x3 | DeepSeek-V4.1-Flash | 3 | pipeline | on_wafer_n5 | rom_wafer_serdes | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-tensor-x95 | DeepSeek-V4.1-Flash | 95 | tensor | nvlink5 | infiniband_ndr | 160 | 564.25 us | 177.2 tok/s | 1,772.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 369.86 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash | 2 | tensor | on_wafer_n5 | rom_wafer_serdes | 160 | 171.80 us | 582.1 tok/s | 5,820.6 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 17.80 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hybrid-x126 | DeepSeek-V4.1-Flash | 126 | hybrid | nvlink5 | infiniband_ndr | 95 | 227.91 us | 438.8 tok/s | 4,387.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.52 us |
| DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 81 | 154.10 us | 648.9 tok/s | 6,489.2 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DeepSeek-V4.1-Flash/b200_sxm-x4-pipeline | DeepSeek-V4.1-Flash | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 3.63 us | 27,516.9 tok/s | 275,168.8 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.63 us |
| DeepSeek-V4.1-Flash/b200_sxm-x4-tensor | DeepSeek-V4.1-Flash | 4 | tensor | nvlink5 | infiniband_ndr | 80 | 194.05 us | 515.3 tok/s | 5,153.4 tok/s | 80 x all_reduce span 4 on nvlink5 (traversals 2.0) = 194.05 us |
| DeepSeek-V4.1-Flash/b200_sxm-x4-nvl72-tensor | DeepSeek-V4.1-Flash | 4 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.05 us | 515.3 tok/s | 5,153.4 tok/s | 80 x all_reduce span 4 on nvlink5_nvl72 (traversals 2.0) = 194.05 us |
| DeepSeek-V4.1-Flash/b200_sxm-x4-expert | DeepSeek-V4.1-Flash | 4 | expert | nvlink5 | infiniband_ndr | 160 | 291.41 us | 343.2 tok/s | 3,431.6 tok/s | 80 x all_reduce span 4 on nvlink5 (traversals 2.0) = 194.05 us; 80 x point_to_point span 2 on nvlink5 (traversals 1.0) = 97.37 us |
| DeepSeek-V4.1-Flash/b200_sxm-x4-nvl72-expert | DeepSeek-V4.1-Flash | 4 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 291.41 us | 343.2 tok/s | 3,431.6 tok/s | 80 x all_reduce span 4 on nvlink5_nvl72 (traversals 2.0) = 194.05 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 97.37 us |
| DeepSeek-V4.1-Flash/b200_sxm-x21-pipeline | DeepSeek-V4.1-Flash | 21 | pipeline | nvlink5 | infiniband_ndr | 20 | 26.27 us | 3,806.0 tok/s | 38,059.9 tok/s | 18 x point_to_point span 2 on nvlink5 (traversals 1.0) = 21.80 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x21-tensor | DeepSeek-V4.1-Flash | 21 | tensor | nvlink5 | infiniband_ndr | 160 | 551.96 us | 181.2 tok/s | 1,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x21-hybrid | DeepSeek-V4.1-Flash | 21 | hybrid | nvlink5 | infiniband_ndr | 82 | 198.86 us | 502.9 tok/s | 5,028.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x21-nvl72-tensor | DeepSeek-V4.1-Flash | 21 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.60 us | 513.9 tok/s | 5,138.7 tok/s | 80 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 194.60 us |
| DeepSeek-V4.1-Flash/b200_sxm-x21-expert | DeepSeek-V4.1-Flash | 21 | expert | nvlink5 | infiniband_ndr | 160 | 360.28 us | 277.6 tok/s | 2,775.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 193.19 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 167.08 us |
| DeepSeek-V4.1-Flash/b200_sxm-x21-nvl72-expert | DeepSeek-V4.1-Flash | 21 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.86 us | 343.8 tok/s | 3,438.1 tok/s | 80 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 194.60 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.26 us |
| DeepSeek-V4.1-Flash/b200_sxm-x22-pipeline | DeepSeek-V4.1-Flash | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 27.49 us | 3,638.2 tok/s | 36,382.5 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 23.02 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x22-tensor | DeepSeek-V4.1-Flash | 22 | tensor | nvlink5 | infiniband_ndr | 160 | 551.96 us | 181.2 tok/s | 1,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x22-hybrid | DeepSeek-V4.1-Flash | 22 | hybrid | nvlink5 | infiniband_ndr | 82 | 198.86 us | 502.9 tok/s | 5,028.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x22-nvl72-tensor | DeepSeek-V4.1-Flash | 22 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.61 us | 513.9 tok/s | 5,138.6 tok/s | 80 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 194.61 us |
| DeepSeek-V4.1-Flash/b200_sxm-x22-expert | DeepSeek-V4.1-Flash | 22 | expert | nvlink5 | infiniband_ndr | 160 | 360.06 us | 277.7 tok/s | 2,777.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 193.19 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 166.87 us |
| DeepSeek-V4.1-Flash/b200_sxm-x22-nvl72-expert | DeepSeek-V4.1-Flash | 22 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.85 us | 343.8 tok/s | 3,438.1 tok/s | 80 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 194.61 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.25 us |
| DeepSeek-V4.1-Flash/b200_sxm-x24-pipeline | DeepSeek-V4.1-Flash | 24 | pipeline | nvlink5 | infiniband_ndr | 23 | 29.91 us | 3,343.5 tok/s | 33,435.3 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.44 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x24-tensor | DeepSeek-V4.1-Flash | 24 | tensor | nvlink5 | infiniband_ndr | 160 | 551.96 us | 181.2 tok/s | 1,811.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x24-hybrid | DeepSeek-V4.1-Flash | 24 | hybrid | nvlink5 | infiniband_ndr | 82 | 198.86 us | 502.9 tok/s | 5,028.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x24-nvl72-tensor | DeepSeek-V4.1-Flash | 24 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.62 us | 513.8 tok/s | 5,138.3 tok/s | 80 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 194.62 us |
| DeepSeek-V4.1-Flash/b200_sxm-x24-expert | DeepSeek-V4.1-Flash | 24 | expert | nvlink5 | infiniband_ndr | 160 | 359.29 us | 278.3 tok/s | 2,783.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 166.50 us |
| DeepSeek-V4.1-Flash/b200_sxm-x24-nvl72-expert | DeepSeek-V4.1-Flash | 24 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.84 us | 343.8 tok/s | 3,438.3 tok/s | 80 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 194.62 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x29-pipeline | DeepSeek-V4.1-Flash | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.99 us | 2,703.5 tok/s | 27,035.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.28 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x29-tensor | DeepSeek-V4.1-Flash | 29 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash/b200_sxm-x29-hybrid | DeepSeek-V4.1-Flash | 29 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x29-nvl72-tensor | DeepSeek-V4.1-Flash | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.64 us | 513.8 tok/s | 5,137.8 tok/s | 80 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 194.64 us |
| DeepSeek-V4.1-Flash/b200_sxm-x29-expert | DeepSeek-V4.1-Flash | 29 | expert | nvlink5 | infiniband_ndr | 160 | 358.59 us | 278.9 tok/s | 2,788.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.79 us |
| DeepSeek-V4.1-Flash/b200_sxm-x29-nvl72-expert | DeepSeek-V4.1-Flash | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.8 tok/s | 3,438.5 tok/s | 80 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 194.64 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.19 us |
| DeepSeek-V4.1-Flash/b200_sxm-x31-pipeline | DeepSeek-V4.1-Flash | 31 | pipeline | nvlink5 | infiniband_ndr | 30 | 39.41 us | 2,537.3 tok/s | 25,373.2 tok/s | 27 x point_to_point span 2 on nvlink5 (traversals 1.0) = 32.71 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x31-tensor | DeepSeek-V4.1-Flash | 31 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash/b200_sxm-x31-hybrid | DeepSeek-V4.1-Flash | 31 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x31-nvl72-tensor | DeepSeek-V4.1-Flash | 31 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.64 us | 513.8 tok/s | 5,137.6 tok/s | 80 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 194.64 us |
| DeepSeek-V4.1-Flash/b200_sxm-x31-expert | DeepSeek-V4.1-Flash | 31 | expert | nvlink5 | infiniband_ndr | 160 | 358.37 us | 279.0 tok/s | 2,790.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.80 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 165.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x31-nvl72-expert | DeepSeek-V4.1-Flash | 31 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.82 us | 343.9 tok/s | 3,438.6 tok/s | 80 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 194.64 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.18 us |
| DeepSeek-V4.1-Flash/b200_sxm-x38-pipeline | DeepSeek-V4.1-Flash | 38 | pipeline | nvlink5 | infiniband_ndr | 37 | 48.91 us | 2,044.4 tok/s | 20,443.8 tok/s | 33 x point_to_point span 2 on nvlink5 (traversals 1.0) = 39.98 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x38-tensor | DeepSeek-V4.1-Flash | 38 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash/b200_sxm-x38-hybrid | DeepSeek-V4.1-Flash | 38 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x38-nvl72-tensor | DeepSeek-V4.1-Flash | 38 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.66 us | 513.7 tok/s | 5,137.2 tok/s | 80 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 194.66 us |
| DeepSeek-V4.1-Flash/b200_sxm-x38-expert | DeepSeek-V4.1-Flash | 38 | expert | nvlink5 | infiniband_ndr | 160 | 357.58 us | 279.7 tok/s | 2,796.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.60 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.99 us |
| DeepSeek-V4.1-Flash/b200_sxm-x38-nvl72-expert | DeepSeek-V4.1-Flash | 38 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.80 us | 343.9 tok/s | 3,438.8 tok/s | 80 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 194.66 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.14 us |
| DeepSeek-V4.1-Flash/b200_sxm-x43-pipeline | DeepSeek-V4.1-Flash | 43 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x43-tensor | DeepSeek-V4.1-Flash | 43 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash/b200_sxm-x43-hybrid | DeepSeek-V4.1-Flash | 43 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash/b200_sxm-x43-nvl72-tensor | DeepSeek-V4.1-Flash | 43 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,137.0 tok/s | 80 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash/b200_sxm-x43-expert | DeepSeek-V4.1-Flash | 43 | expert | nvlink5 | infiniband_ndr | 160 | 357.16 us | 280.0 tok/s | 2,799.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.69 us |
| DeepSeek-V4.1-Flash/b200_sxm-x43-nvl72-expert | DeepSeek-V4.1-Flash | 43 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.13 us |
| DeepSeek-V4.1-Flash/b200_sxm-x44-pipeline | DeepSeek-V4.1-Flash | 44 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x44-tensor | DeepSeek-V4.1-Flash | 44 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash/b200_sxm-x44-hybrid | DeepSeek-V4.1-Flash | 44 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash/b200_sxm-x44-nvl72-tensor | DeepSeek-V4.1-Flash | 44 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.9 tok/s | 80 x all_reduce span 44 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash/b200_sxm-x44-expert | DeepSeek-V4.1-Flash | 44 | expert | nvlink5 | infiniband_ndr | 160 | 357.11 us | 280.0 tok/s | 2,800.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.48 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.63 us |
| DeepSeek-V4.1-Flash/b200_sxm-x44-nvl72-expert | DeepSeek-V4.1-Flash | 44 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 44 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.12 us |
| DeepSeek-V4.1-Flash/b200_sxm-x48-pipeline | DeepSeek-V4.1-Flash | 48 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x48-tensor | DeepSeek-V4.1-Flash | 48 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash/b200_sxm-x48-hybrid | DeepSeek-V4.1-Flash | 48 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash/b200_sxm-x48-nvl72-tensor | DeepSeek-V4.1-Flash | 48 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.67 us | 513.7 tok/s | 5,136.8 tok/s | 80 x all_reduce span 48 on nvlink5_nvl72 (traversals 2.0) = 194.67 us |
| DeepSeek-V4.1-Flash/b200_sxm-x48-expert | DeepSeek-V4.1-Flash | 48 | expert | nvlink5 | infiniband_ndr | 160 | 356.85 us | 280.2 tok/s | 2,802.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.45 us |
| DeepSeek-V4.1-Flash/b200_sxm-x48-nvl72-expert | DeepSeek-V4.1-Flash | 48 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,438.9 tok/s | 80 x all_reduce span 48 on nvlink5_nvl72 (traversals 2.0) = 194.67 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.11 us |
| DeepSeek-V4.1-Flash/b200_sxm-x50-pipeline | DeepSeek-V4.1-Flash | 50 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x50-tensor | DeepSeek-V4.1-Flash | 50 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash/b200_sxm-x50-hybrid | DeepSeek-V4.1-Flash | 50 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash/b200_sxm-x50-nvl72-tensor | DeepSeek-V4.1-Flash | 50 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.7 tok/s | 80 x all_reduce span 50 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x50-expert | DeepSeek-V4.1-Flash | 50 | expert | nvlink5 | infiniband_ndr | 160 | 356.76 us | 280.3 tok/s | 2,803.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.37 us |
| DeepSeek-V4.1-Flash/b200_sxm-x50-nvl72-expert | DeepSeek-V4.1-Flash | 50 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.79 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 50 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.11 us |
| DeepSeek-V4.1-Flash/b200_sxm-x52-pipeline | DeepSeek-V4.1-Flash | 52 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x52-tensor | DeepSeek-V4.1-Flash | 52 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash/b200_sxm-x52-hybrid | DeepSeek-V4.1-Flash | 52 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash/b200_sxm-x52-nvl72-tensor | DeepSeek-V4.1-Flash | 52 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.7 tok/s | 80 x all_reduce span 52 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x52-expert | DeepSeek-V4.1-Flash | 52 | expert | nvlink5 | infiniband_ndr | 160 | 356.69 us | 280.4 tok/s | 2,803.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.40 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.29 us |
| DeepSeek-V4.1-Flash/b200_sxm-x52-nvl72-expert | DeepSeek-V4.1-Flash | 52 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 52 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.11 us |
| DeepSeek-V4.1-Flash/b200_sxm-x56-pipeline | DeepSeek-V4.1-Flash | 56 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x56-tensor | DeepSeek-V4.1-Flash | 56 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash/b200_sxm-x56-hybrid | DeepSeek-V4.1-Flash | 56 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash/b200_sxm-x56-nvl72-tensor | DeepSeek-V4.1-Flash | 56 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.6 tok/s | 80 x all_reduce span 56 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x56-expert | DeepSeek-V4.1-Flash | 56 | expert | nvlink5 | infiniband_ndr | 160 | 356.50 us | 280.5 tok/s | 2,805.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.34 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.16 us |
| DeepSeek-V4.1-Flash/b200_sxm-x56-nvl72-expert | DeepSeek-V4.1-Flash | 56 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.0 tok/s | 80 x all_reduce span 56 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.10 us |
| DeepSeek-V4.1-Flash/b200_sxm-x58-pipeline | DeepSeek-V4.1-Flash | 58 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x58-tensor | DeepSeek-V4.1-Flash | 58 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash/b200_sxm-x58-hybrid | DeepSeek-V4.1-Flash | 58 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash/b200_sxm-x58-nvl72-tensor | DeepSeek-V4.1-Flash | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.68 us | 513.7 tok/s | 5,136.5 tok/s | 80 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 194.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x58-expert | DeepSeek-V4.1-Flash | 58 | expert | nvlink5 | infiniband_ndr | 160 | 356.44 us | 280.6 tok/s | 2,805.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.34 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 164.09 us |
| DeepSeek-V4.1-Flash/b200_sxm-x58-nvl72-expert | DeepSeek-V4.1-Flash | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.78 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 194.68 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.09 us |
| DeepSeek-V4.1-Flash/b200_sxm-x63-pipeline | DeepSeek-V4.1-Flash | 63 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x63-tensor | DeepSeek-V4.1-Flash | 63 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash/b200_sxm-x63-hybrid | DeepSeek-V4.1-Flash | 63 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash/b200_sxm-x63-nvl72-tensor | DeepSeek-V4.1-Flash | 63 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.4 tok/s | 80 x all_reduce span 63 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash/b200_sxm-x63-expert | DeepSeek-V4.1-Flash | 63 | expert | nvlink5 | infiniband_ndr | 160 | 356.30 us | 280.7 tok/s | 2,806.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.34 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.96 us |
| DeepSeek-V4.1-Flash/b200_sxm-x63-nvl72-expert | DeepSeek-V4.1-Flash | 63 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 63 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.09 us |
| DeepSeek-V4.1-Flash/b200_sxm-x64-pipeline | DeepSeek-V4.1-Flash | 64 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x64-tensor | DeepSeek-V4.1-Flash | 64 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash/b200_sxm-x64-hybrid | DeepSeek-V4.1-Flash | 64 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash/b200_sxm-x64-nvl72-tensor | DeepSeek-V4.1-Flash | 64 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.4 tok/s | 80 x all_reduce span 64 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash/b200_sxm-x64-expert | DeepSeek-V4.1-Flash | 64 | expert | nvlink5 | infiniband_ndr | 160 | 356.23 us | 280.7 tok/s | 2,807.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.30 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x64-nvl72-expert | DeepSeek-V4.1-Flash | 64 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 64 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.09 us |
| DeepSeek-V4.1-Flash/b200_sxm-x67-pipeline | DeepSeek-V4.1-Flash | 67 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x67-tensor | DeepSeek-V4.1-Flash | 67 | tensor | nvlink5 | infiniband_ndr | 160 | 562.88 us | 177.7 tok/s | 1,776.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 368.49 us |
| DeepSeek-V4.1-Flash/b200_sxm-x67-hybrid | DeepSeek-V4.1-Flash | 67 | hybrid | nvlink5 | infiniband_ndr | 88 | 212.27 us | 471.1 tok/s | 4,711.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.88 us |
| DeepSeek-V4.1-Flash/b200_sxm-x67-nvl72-tensor | DeepSeek-V4.1-Flash | 67 | tensor | nvlink5_nvl72 | infiniband_ndr | 80 | 194.69 us | 513.6 tok/s | 5,136.4 tok/s | 80 x all_reduce span 67 on nvlink5_nvl72 (traversals 2.0) = 194.69 us |
| DeepSeek-V4.1-Flash/b200_sxm-x67-expert | DeepSeek-V4.1-Flash | 67 | expert | nvlink5 | infiniband_ndr | 160 | 356.17 us | 280.8 tok/s | 2,807.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.30 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.87 us |
| DeepSeek-V4.1-Flash/b200_sxm-x67-nvl72-expert | DeepSeek-V4.1-Flash | 67 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 290.77 us | 343.9 tok/s | 3,439.1 tok/s | 80 x all_reduce span 67 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 96.08 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-pipeline | DeepSeek-V4.1-Flash | 76 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-tensor | DeepSeek-V4.1-Flash | 76 | tensor | nvlink5 | infiniband_ndr | 160 | 563.43 us | 177.5 tok/s | 1,774.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 369.04 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-hybrid | DeepSeek-V4.1-Flash | 76 | hybrid | nvlink5 | infiniband_ndr | 89 | 214.50 us | 466.2 tok/s | 4,661.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.11 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-nvl72-tensor | DeepSeek-V4.1-Flash | 76 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-nvl72-hybrid | DeepSeek-V4.1-Flash | 76 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-expert | DeepSeek-V4.1-Flash | 76 | expert | nvlink5 | infiniband_ndr | 160 | 355.96 us | 280.9 tok/s | 2,809.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.27 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.69 us |
| DeepSeek-V4.1-Flash/b200_sxm-x76-nvl72-expert | DeepSeek-V4.1-Flash | 76 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.39 us | 279.0 tok/s | 2,790.3 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.69 us |
| DeepSeek-V4.1-Flash/b200_sxm-x77-pipeline | DeepSeek-V4.1-Flash | 77 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x77-tensor | DeepSeek-V4.1-Flash | 77 | tensor | nvlink5 | infiniband_ndr | 160 | 563.43 us | 177.5 tok/s | 1,774.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 369.04 us |
| DeepSeek-V4.1-Flash/b200_sxm-x77-hybrid | DeepSeek-V4.1-Flash | 77 | hybrid | nvlink5 | infiniband_ndr | 89 | 214.50 us | 466.2 tok/s | 4,661.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.11 us |
| DeepSeek-V4.1-Flash/b200_sxm-x77-nvl72-tensor | DeepSeek-V4.1-Flash | 77 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x77-nvl72-hybrid | DeepSeek-V4.1-Flash | 77 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x77-expert | DeepSeek-V4.1-Flash | 77 | expert | nvlink5 | infiniband_ndr | 160 | 355.94 us | 280.9 tok/s | 2,809.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.27 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x77-nvl72-expert | DeepSeek-V4.1-Flash | 77 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.37 us | 279.0 tok/s | 2,790.4 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-pipeline | DeepSeek-V4.1-Flash | 84 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-tensor | DeepSeek-V4.1-Flash | 84 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-hybrid | DeepSeek-V4.1-Flash | 84 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-nvl72-tensor | DeepSeek-V4.1-Flash | 84 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-nvl72-hybrid | DeepSeek-V4.1-Flash | 84 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-expert | DeepSeek-V4.1-Flash | 84 | expert | nvlink5 | infiniband_ndr | 160 | 355.81 us | 281.0 tok/s | 2,810.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x84-nvl72-expert | DeepSeek-V4.1-Flash | 84 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.26 us | 279.1 tok/s | 2,791.2 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-pipeline | DeepSeek-V4.1-Flash | 87 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-tensor | DeepSeek-V4.1-Flash | 87 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-hybrid | DeepSeek-V4.1-Flash | 87 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-tensor | DeepSeek-V4.1-Flash | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-hybrid | DeepSeek-V4.1-Flash | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-expert | DeepSeek-V4.1-Flash | 87 | expert | nvlink5 | infiniband_ndr | 160 | 355.77 us | 281.1 tok/s | 2,810.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.24 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.53 us |
| DeepSeek-V4.1-Flash/b200_sxm-x87-nvl72-expert | DeepSeek-V4.1-Flash | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.22 us | 279.2 tok/s | 2,791.6 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.53 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-pipeline | DeepSeek-V4.1-Flash | 90 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-tensor | DeepSeek-V4.1-Flash | 90 | tensor | nvlink5 | infiniband_ndr | 160 | 564.25 us | 177.2 tok/s | 1,772.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 369.86 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-hybrid | DeepSeek-V4.1-Flash | 90 | hybrid | nvlink5 | infiniband_ndr | 91 | 218.97 us | 456.7 tok/s | 4,566.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 24.58 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-nvl72-tensor | DeepSeek-V4.1-Flash | 90 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-nvl72-hybrid | DeepSeek-V4.1-Flash | 90 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-expert | DeepSeek-V4.1-Flash | 90 | expert | nvlink5 | infiniband_ndr | 160 | 355.71 us | 281.1 tok/s | 2,811.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.22 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.49 us |
| DeepSeek-V4.1-Flash/b200_sxm-x90-nvl72-expert | DeepSeek-V4.1-Flash | 90 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.19 us | 279.2 tok/s | 2,791.9 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.49 us |
| DeepSeek-V4.1-Flash/b200_sxm-x91-pipeline | DeepSeek-V4.1-Flash | 91 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x91-tensor | DeepSeek-V4.1-Flash | 91 | tensor | nvlink5 | infiniband_ndr | 160 | 564.25 us | 177.2 tok/s | 1,772.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 369.86 us |
| DeepSeek-V4.1-Flash/b200_sxm-x91-hybrid | DeepSeek-V4.1-Flash | 91 | hybrid | nvlink5 | infiniband_ndr | 91 | 218.97 us | 456.7 tok/s | 4,566.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 24.58 us |
| DeepSeek-V4.1-Flash/b200_sxm-x91-nvl72-tensor | DeepSeek-V4.1-Flash | 91 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x91-nvl72-hybrid | DeepSeek-V4.1-Flash | 91 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x91-expert | DeepSeek-V4.1-Flash | 91 | expert | nvlink5 | infiniband_ndr | 160 | 355.70 us | 281.1 tok/s | 2,811.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.22 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.48 us |
| DeepSeek-V4.1-Flash/b200_sxm-x91-nvl72-expert | DeepSeek-V4.1-Flash | 91 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 358.17 us | 279.2 tok/s | 2,791.9 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.48 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-pipeline | DeepSeek-V4.1-Flash | 116 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-tensor | DeepSeek-V4.1-Flash | 116 | tensor | nvlink5 | infiniband_ndr | 160 | 565.06 us | 177.0 tok/s | 1,769.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 370.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-hybrid | DeepSeek-V4.1-Flash | 116 | hybrid | nvlink5 | infiniband_ndr | 94 | 225.68 us | 443.1 tok/s | 4,431.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 31.29 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-nvl72-tensor | DeepSeek-V4.1-Flash | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-nvl72-hybrid | DeepSeek-V4.1-Flash | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-expert | DeepSeek-V4.1-Flash | 116 | expert | nvlink5 | infiniband_ndr | 160 | 355.42 us | 281.4 tok/s | 2,813.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.17 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.25 us |
| DeepSeek-V4.1-Flash/b200_sxm-x116-nvl72-expert | DeepSeek-V4.1-Flash | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.94 us | 279.4 tok/s | 2,793.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.25 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-pipeline | DeepSeek-V4.1-Flash | 125 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-tensor | DeepSeek-V4.1-Flash | 125 | tensor | nvlink5 | infiniband_ndr | 160 | 565.27 us | 176.9 tok/s | 1,769.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 370.88 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-hybrid | DeepSeek-V4.1-Flash | 125 | hybrid | nvlink5 | infiniband_ndr | 95 | 227.91 us | 438.8 tok/s | 4,387.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.52 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-nvl72-tensor | DeepSeek-V4.1-Flash | 125 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-nvl72-hybrid | DeepSeek-V4.1-Flash | 125 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-expert | DeepSeek-V4.1-Flash | 125 | expert | nvlink5 | infiniband_ndr | 160 | 355.35 us | 281.4 tok/s | 2,814.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.16 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.19 us |
| DeepSeek-V4.1-Flash/b200_sxm-x125-nvl72-expert | DeepSeek-V4.1-Flash | 125 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.88 us | 279.4 tok/s | 2,794.2 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.19 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-pipeline | DeepSeek-V4.1-Flash | 134 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-tensor | DeepSeek-V4.1-Flash | 134 | tensor | nvlink5 | infiniband_ndr | 160 | 565.45 us | 176.9 tok/s | 1,768.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 17 on infiniband_ndr (traversals 2.0) = 371.06 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-hybrid | DeepSeek-V4.1-Flash | 134 | hybrid | nvlink5 | infiniband_ndr | 96 | 230.15 us | 434.5 tok/s | 4,345.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 16 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 35.76 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-nvl72-tensor | DeepSeek-V4.1-Flash | 134 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 544.07 us | 183.8 tok/s | 1,838.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 349.38 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-nvl72-hybrid | DeepSeek-V4.1-Flash | 134 | hybrid | nvlink5_nvl72 | infiniband_ndr | 81 | 196.93 us | 507.8 tok/s | 5,078.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.23 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-expert | DeepSeek-V4.1-Flash | 134 | expert | nvlink5 | infiniband_ndr | 160 | 355.28 us | 281.5 tok/s | 2,814.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.15 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.13 us |
| DeepSeek-V4.1-Flash/b200_sxm-x134-nvl72-expert | DeepSeek-V4.1-Flash | 134 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 357.83 us | 279.5 tok/s | 2,794.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.13 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-pipeline | DeepSeek-V4.1-Flash | 167 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-tensor | DeepSeek-V4.1-Flash | 167 | tensor | nvlink5 | infiniband_ndr | 160 | 566.00 us | 176.7 tok/s | 1,766.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 21 on infiniband_ndr (traversals 2.0) = 371.61 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-hybrid | DeepSeek-V4.1-Flash | 167 | hybrid | nvlink5 | infiniband_ndr | 100 | 239.09 us | 418.3 tok/s | 4,182.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 20 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 44.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-nvl72-tensor | DeepSeek-V4.1-Flash | 167 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-nvl72-hybrid | DeepSeek-V4.1-Flash | 167 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-expert | DeepSeek-V4.1-Flash | 167 | expert | nvlink5 | infiniband_ndr | 160 | 355.11 us | 281.6 tok/s | 2,816.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.12 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash/b200_sxm-x167-nvl72-expert | DeepSeek-V4.1-Flash | 167 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.34 us | 280.6 tok/s | 2,806.3 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.99 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-pipeline | DeepSeek-V4.1-Flash | 173 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-tensor | DeepSeek-V4.1-Flash | 173 | tensor | nvlink5 | infiniband_ndr | 160 | 566.11 us | 176.6 tok/s | 1,766.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 371.72 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-hybrid | DeepSeek-V4.1-Flash | 173 | hybrid | nvlink5 | infiniband_ndr | 101 | 241.32 us | 414.4 tok/s | 4,143.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.93 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-nvl72-tensor | DeepSeek-V4.1-Flash | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-nvl72-hybrid | DeepSeek-V4.1-Flash | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-expert | DeepSeek-V4.1-Flash | 173 | expert | nvlink5 | infiniband_ndr | 160 | 355.08 us | 281.6 tok/s | 2,816.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.11 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.97 us |
| DeepSeek-V4.1-Flash/b200_sxm-x173-nvl72-expert | DeepSeek-V4.1-Flash | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.31 us | 280.7 tok/s | 2,806.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.97 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-pipeline | DeepSeek-V4.1-Flash | 179 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-tensor | DeepSeek-V4.1-Flash | 179 | tensor | nvlink5 | infiniband_ndr | 160 | 566.20 us | 176.6 tok/s | 1,766.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 23 on infiniband_ndr (traversals 2.0) = 371.81 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-hybrid | DeepSeek-V4.1-Flash | 179 | hybrid | nvlink5 | infiniband_ndr | 102 | 243.55 us | 410.6 tok/s | 4,105.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 22 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 49.17 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-nvl72-tensor | DeepSeek-V4.1-Flash | 179 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 552.26 us | 181.1 tok/s | 1,810.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 357.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-nvl72-hybrid | DeepSeek-V4.1-Flash | 179 | hybrid | nvlink5_nvl72 | infiniband_ndr | 82 | 199.16 us | 502.1 tok/s | 5,021.0 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.47 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-expert | DeepSeek-V4.1-Flash | 179 | expert | nvlink5 | infiniband_ndr | 160 | 355.06 us | 281.6 tok/s | 2,816.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.11 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.95 us |
| DeepSeek-V4.1-Flash/b200_sxm-x179-nvl72-expert | DeepSeek-V4.1-Flash | 179 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 356.30 us | 280.7 tok/s | 2,806.7 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 193.35 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.95 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-pipeline | DeepSeek-V4.1-Flash | 231 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-tensor | DeepSeek-V4.1-Flash | 231 | tensor | nvlink5 | infiniband_ndr | 160 | 566.65 us | 176.5 tok/s | 1,764.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 372.26 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-hybrid | DeepSeek-V4.1-Flash | 231 | hybrid | nvlink5 | infiniband_ndr | 108 | 256.96 us | 389.2 tok/s | 3,891.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 62.57 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-nvl72-tensor | DeepSeek-V4.1-Flash | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 556.36 us | 179.7 tok/s | 1,797.4 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-nvl72-hybrid | DeepSeek-V4.1-Flash | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 83 | 201.40 us | 496.5 tok/s | 4,965.3 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-expert | DeepSeek-V4.1-Flash | 231 | expert | nvlink5 | infiniband_ndr | 160 | 354.91 us | 281.8 tok/s | 2,817.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.09 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.83 us |
| DeepSeek-V4.1-Flash/b200_sxm-x231-nvl72-expert | DeepSeek-V4.1-Flash | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.72 us | 281.1 tok/s | 2,811.2 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.90 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.83 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-pipeline | DeepSeek-V4.1-Flash | 347 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-tensor | DeepSeek-V4.1-Flash | 347 | tensor | nvlink5 | infiniband_ndr | 160 | 567.22 us | 176.3 tok/s | 1,763.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 372.83 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-hybrid | DeepSeek-V4.1-Flash | 347 | hybrid | nvlink5 | infiniband_ndr | 119 | 281.55 us | 355.2 tok/s | 3,551.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 39 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 87.16 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-tensor | DeepSeek-V4.1-Flash | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 160 | 558.81 us | 179.0 tok/s | 1,789.5 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-hybrid | DeepSeek-V4.1-Flash | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 84 | 203.63 us | 491.1 tok/s | 4,910.8 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 194.69 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-expert | DeepSeek-V4.1-Flash | 347 | expert | nvlink5 | infiniband_ndr | 160 | 354.74 us | 281.9 tok/s | 2,819.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 192.06 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.68 us |
| DeepSeek-V4.1-Flash/b200_sxm-x347-nvl72-expert | DeepSeek-V4.1-Flash | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 160 | 355.36 us | 281.4 tok/s | 2,814.1 tok/s | 80 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 192.67 us; 80 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 162.68 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4.1-Flash | 1 | array | array | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170 | 138,550 | 15,490.3 | 0.112 | 15,490.3 (138,550) | 5,892.7 (92,450) | 0.38x | compute |
| DeepSeek-V4.1-Flash | 2 | array | array | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170 | 138,550 | 15,490.3 | 0.112 | 15,490.3 (138,550) | 5,892.7 (92,450) | 0.38x | compute |
| DeepSeek-V4.1-Flash | 4 | array | array | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170 | 138,550 | 15,490.3 | 0.112 | 15,490.3 (138,550) | 5,706.1 (92,450) | 0.37x | compute |
| DeepSeek-V4.1-Flash | 8 | array | array | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170 | 138,550 | 15,490.3 | 0.112 | 15,490.3 (138,550) | 5,810.0 (138,675) | 0.38x | compute |
| DeepSeek-V4.1-Flash | 16 | array | array | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170 | 138,550 | 15,490.3 | 0.112 | 15,490.3 (138,550) | 5,749.8 (184,900) | 0.37x | compute |
| DeepSeek-V4.1-Flash | 32 | array | array | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170 | 138,550 | 15,490.3 | 0.112 | 15,490.3 (138,550) | 5,468.3 (138,675) | 0.35x | compute |
| DeepSeek-V4.1-Flash | 64 | array | array | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 13,436.0 | 0.073 | 13,436.0 (185,005) | 5,468.3 (138,675) | 0.41x | weight_read |
| DeepSeek-V4.1-Flash | 256 | array | array | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x264 | 215,160 | 6,568.4 | 0.031 | 6,568.4 (215,160) | 4,543.5 (277,350) | 0.69x | compute |
| DeepSeek-V4.1-Flash | 1024 | wafer | array | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3,096.2 | 0.006 | 2,511.0 (277,100) | 3,096.2 (554,700) | 1.23x | compute |
| DeepSeek-V4.1-Flash | 4096 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,312.3 | 0.002 | 661.9 (277,100) | 1,312.3 (554,700) | 1.98x | compute |

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
| DeepSeek-V4.1-Flash | 384 | 752.0 MB | 128.3 mm2 | 23.09 mm2 (18.0%) | 49,261 mm2 | 8,867 mm2 | 87,047 mm2 = 106.8 reticles |

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
| DeepSeek-V4.1-Flash | 1 | sram | 999,852.2 | 28,795.8 | 28,795.8 | 34.72x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | sram | 999,852.2 | 28,795.8 | 28,795.8 | 34.72x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | sram | 999,852.2 | 28,795.8 | 31,744.8 | 34.72x | 1.10x | weight_read | weight_read | link_latency |
| DeepSeek-V4.1-Flash | 8 | sram | 999,852.2 | 28,795.8 | 51,833.7 | 34.72x | 1.80x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | sram | 999,852.2 | 28,795.8 | 84,636.0 | 34.72x | 2.94x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 32 | sram | 999,852.2 | 28,795.8 | 126,734.2 | 34.72x | 4.40x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | sram | 999,852.2 | 28,819.6 | 191,793.5 | 34.69x | 6.65x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 256 | sram | 1,681,520.9 | 28,965.6 | 472,336.4 | 58.05x | 16.31x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1024 | sram | 2,792,756.3 | 29,002.3 | 882,529.1 | 96.29x | 30.43x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4096 | sram | 5,375,012.0 | 29,011.5 | 1,271,764.2 | 185.27x | 43.84x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1 | rom | 3,098,388.4 | 41,608.6 | 41,608.6 | 74.47x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | rom | 3,098,388.4 | 41,608.6 | 41,608.6 | 74.47x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | rom | 3,098,388.4 | 41,608.6 | 41,608.6 | 74.47x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 8 | rom | 3,098,388.4 | 41,608.6 | 58,397.9 | 74.47x | 1.40x | compute | weight_read | link_latency |
| DeepSeek-V4.1-Flash | 16 | rom | 3,098,388.4 | 41,608.6 | 95,756.0 | 74.47x | 2.30x | compute | weight_read | link_latency |
| DeepSeek-V4.1-Flash | 32 | rom | 3,098,388.4 | 41,608.6 | 144,478.6 | 74.47x | 3.47x | compute | weight_read | link_latency |
| DeepSeek-V4.1-Flash | 64 | rom | 3,098,388.4 | 41,608.6 | 220,173.6 | 74.47x | 5.29x | compute | weight_read | link_latency |
| DeepSeek-V4.1-Flash | 256 | rom | 3,098,388.4 | 41,796.6 | 573,780.5 | 74.13x | 13.73x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1024 | rom | 3,170,512.0 | 41,854.3 | 1,128,105.1 | 75.75x | 26.95x | compute | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4096 | rom | 3,284,354.8 | 41,868.7 | 1,674,728.4 | 78.44x | 40.00x | compute | weight_read | weight_read |

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
| DeepSeek-V4.1-Flash | 1 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 999,852.2 | 1.803 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 3,098,388.4 | 5.586 | compute | 3.10x |
| DeepSeek-V4.1-Flash | 1 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 1 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 1.60 | 1.00 | 41,608.6 | 0.690 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 1 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 1 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perregion-romfill | 60,310 | 1.60 | 1.00 | 41,608.6 | 0.690 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 2 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 999,852.2 | 1.803 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 2 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 3,098,388.4 | 5.586 | compute | 3.10x |
| DeepSeek-V4.1-Flash | 2 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 2 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 1.60 | 1.00 | 41,608.6 | 0.690 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 2 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 2 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perregion-romfill | 60,310 | 1.60 | 1.00 | 41,608.6 | 0.690 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 4 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 999,852.2 | 1.803 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 4 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 3,098,388.4 | 5.586 | compute | 3.10x |
| DeepSeek-V4.1-Flash | 4 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 4 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 1.60 | 1.00 | 41,608.6 | 0.690 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 4 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x42-perregion | 34,230 | 1.00 | 1.43 | 31,744.8 | 0.927 | link_latency | 0.03x |
| DeepSeek-V4.1-Flash | 4 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perregion-romfill | 60,310 | 1.60 | 1.00 | 41,608.6 | 0.690 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 8 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 999,852.2 | 1.803 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 8 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 3,098,388.4 | 5.586 | compute | 3.10x |
| DeepSeek-V4.1-Flash | 8 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 8 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 1.60 | 1.00 | 41,608.6 | 0.690 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 8 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x42-perregion | 34,230 | 1.00 | 1.99 | 51,833.7 | 1.514 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash | 8 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x60-perregion-romfill | 48,900 | 1.30 | 1.99 | 58,397.9 | 1.194 | link_latency | 0.06x |
| DeepSeek-V4.1-Flash | 16 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 999,852.2 | 1.803 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 16 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 3,098,388.4 | 5.586 | compute | 3.10x |
| DeepSeek-V4.1-Flash | 16 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 16 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 1.60 | 1.00 | 41,608.6 | 0.690 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 16 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x42-perregion | 34,230 | 1.00 | 2.54 | 84,636.0 | 2.473 | weight_read | 0.08x |
| DeepSeek-V4.1-Flash | 16 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x60-perregion-romfill | 48,900 | 1.30 | 2.54 | 95,756.0 | 1.958 | link_latency | 0.10x |
| DeepSeek-V4.1-Flash | 32 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 999,852.2 | 1.803 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 32 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 3,098,388.4 | 5.586 | compute | 3.10x |
| DeepSeek-V4.1-Flash | 32 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 32 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 1.60 | 1.00 | 41,608.6 | 0.690 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 32 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x42-perregion | 34,230 | 1.00 | 3.49 | 126,734.2 | 3.702 | weight_read | 0.13x |
| DeepSeek-V4.1-Flash | 32 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x74-perregion-romfill | 60,310 | 1.60 | 3.49 | 144,478.6 | 2.396 | link_latency | 0.14x |
| DeepSeek-V4.1-Flash | 64 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 999,852.2 | 1.803 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 64 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 3,098,388.4 | 5.586 | compute | 3.10x |
| DeepSeek-V4.1-Flash | 64 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,819.6 | 0.623 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash | 64 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 1.60 | 1.00 | 41,608.6 | 0.690 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 64 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 4.92 | 191,793.5 | 4.149 | weight_read | 0.19x |
| DeepSeek-V4.1-Flash | 64 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.34 | 4.92 | 220,173.6 | 4.763 | link_latency | 0.22x |
| DeepSeek-V4.1-Flash | 256 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x264 | 215,160 | 1.00 | 1.00 | 1,681,520.9 | 7.815 | compute | 1.00x |
| DeepSeek-V4.1-Flash | 256 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 3,098,388.4 | 5.586 | compute | 1.84x |
| DeepSeek-V4.1-Flash | 256 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,965.6 | 0.627 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash | 256 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 1.60 | 3.46 | 41,796.6 | 0.693 | weight_read | 0.02x |
| DeepSeek-V4.1-Flash | 256 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 10.96 | 472,336.4 | 10.218 | weight_read | 0.28x |
| DeepSeek-V4.1-Flash | 256 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.34 | 10.96 | 573,780.5 | 12.413 | weight_read | 0.34x |
| DeepSeek-V4.1-Flash | 1024 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 2,792,756.3 | 5.035 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1024 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 3,170,512.0 | 5.716 | compute | 1.14x |
| DeepSeek-V4.1-Flash | 1024 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 17.96 | 29,002.3 | 0.627 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash | 1024 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 1.60 | 13.84 | 41,854.3 | 0.694 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash | 1024 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 28.90 | 882,529.1 | 19.092 | weight_read | 0.32x |
| DeepSeek-V4.1-Flash | 1024 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.34 | 28.90 | 1,128,105.1 | 24.405 | weight_read | 0.40x |
| DeepSeek-V4.1-Flash | 4096 | batched | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 5,375,012.0 | 9.690 | compute | 1.00x |
| DeepSeek-V4.1-Flash | 4096 | batched | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.78 | 1.00 | 3,284,354.8 | 5.921 | compute | 0.61x |
| DeepSeek-V4.1-Flash | 4096 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 71.86 | 29,011.5 | 0.628 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash | 4096 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x74-perstream-romfill | 60,310 | 1.60 | 55.35 | 41,868.7 | 0.694 | weight_read | 0.01x |
| DeepSeek-V4.1-Flash | 4096 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 88.68 | 1,271,764.2 | 27.512 | weight_read | 0.24x |
| DeepSeek-V4.1-Flash | 4096 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 1.34 | 88.68 | 1,674,728.4 | 36.230 | weight_read | 0.31x |

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
| DeepSeek-V4.1-Flash | 1 | 42 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 2 | 42 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 4 | 42 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 8 | 42 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 16 | 42 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 32 | 42 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 64 | 57 | 1.12 | 1.001 | 1.009 | 1.01x |
| DeepSeek-V4.1-Flash | 256 | 57 | 4.49 | 1.028 | 1.519 | 1.48x |
| DeepSeek-V4.1-Flash | 1024 | 57 | 17.96 | 1.139 | 2.691 | 2.36x |
| DeepSeek-V4.1-Flash | 4096 | 47 | 87.15 | 1.824 | 5.801 | 3.18x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash | 1 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4.1-Flash | 2 | 4 | 3.87 | 2.63 | 1.47x |
| DeepSeek-V4.1-Flash | 4 | 4 | 4.00 | 2.91 | 1.37x |
| DeepSeek-V4.1-Flash | 8 | 4 | 4.00 | 3.16 | 1.27x |
| DeepSeek-V4.1-Flash | 16 | 4 | 4.00 | 3.35 | 1.19x |
| DeepSeek-V4.1-Flash | 32 | 4 | 4.00 | 3.49 | 1.15x |
| DeepSeek-V4.1-Flash | 64 | 4 | 4.00 | 3.59 | 1.11x |
| DeepSeek-V4.1-Flash | 256 | 4 | 4.00 | 3.66 | 1.09x |
| DeepSeek-V4.1-Flash | 1024 | 4 | 4.00 | 3.66 | 1.09x |
| DeepSeek-V4.1-Flash | 4096 | 4 | 4.00 | 3.66 | 1.09x |
| DeepSeek-V4.1-Flash | 1 | 21 | 5.33 | 3.97 | 1.34x |
| DeepSeek-V4.1-Flash | 2 | 21 | 9.25 | 5.30 | 1.75x |
| DeepSeek-V4.1-Flash | 4 | 21 | 14.31 | 6.93 | 2.06x |
| DeepSeek-V4.1-Flash | 8 | 21 | 18.71 | 8.71 | 2.15x |
| DeepSeek-V4.1-Flash | 16 | 21 | 20.68 | 10.49 | 1.97x |
| DeepSeek-V4.1-Flash | 32 | 21 | 20.99 | 12.09 | 1.74x |
| DeepSeek-V4.1-Flash | 64 | 21 | 21.00 | 13.34 | 1.57x |
| DeepSeek-V4.1-Flash | 256 | 21 | 21.00 | 14.41 | 1.46x |
| DeepSeek-V4.1-Flash | 1024 | 21 | 21.00 | 14.46 | 1.45x |
| DeepSeek-V4.1-Flash | 4096 | 21 | 21.00 | 14.46 | 1.45x |
| DeepSeek-V4.1-Flash | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4.1-Flash | 2 | 22 | 9.36 | 5.37 | 1.74x |
| DeepSeek-V4.1-Flash | 4 | 22 | 14.61 | 7.06 | 2.07x |
| DeepSeek-V4.1-Flash | 8 | 22 | 19.34 | 8.91 | 2.17x |
| DeepSeek-V4.1-Flash | 16 | 22 | 21.59 | 10.77 | 2.00x |
| DeepSeek-V4.1-Flash | 32 | 22 | 21.98 | 12.46 | 1.76x |
| DeepSeek-V4.1-Flash | 64 | 22 | 22.00 | 13.78 | 1.60x |
| DeepSeek-V4.1-Flash | 256 | 22 | 22.00 | 14.92 | 1.47x |
| DeepSeek-V4.1-Flash | 1024 | 22 | 22.00 | 14.97 | 1.47x |
| DeepSeek-V4.1-Flash | 4096 | 22 | 22.00 | 14.97 | 1.47x |
| DeepSeek-V4.1-Flash | 1 | 24 | 5.41 | 4.10 | 1.32x |
| DeepSeek-V4.1-Flash | 2 | 24 | 9.54 | 5.52 | 1.73x |
| DeepSeek-V4.1-Flash | 4 | 24 | 15.15 | 7.31 | 2.07x |
| DeepSeek-V4.1-Flash | 8 | 24 | 20.53 | 9.30 | 2.21x |
| DeepSeek-V4.1-Flash | 16 | 24 | 23.37 | 11.32 | 2.06x |
| DeepSeek-V4.1-Flash | 32 | 24 | 23.96 | 13.17 | 1.82x |
| DeepSeek-V4.1-Flash | 64 | 24 | 24.00 | 14.64 | 1.64x |
| DeepSeek-V4.1-Flash | 256 | 24 | 24.00 | 15.91 | 1.51x |
| DeepSeek-V4.1-Flash | 1024 | 24 | 24.00 | 15.96 | 1.50x |
| DeepSeek-V4.1-Flash | 4096 | 24 | 24.00 | 15.96 | 1.50x |
| DeepSeek-V4.1-Flash | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4.1-Flash | 2 | 29 | 9.90 | 5.83 | 1.70x |
| DeepSeek-V4.1-Flash | 4 | 29 | 16.26 | 7.87 | 2.07x |
| DeepSeek-V4.1-Flash | 8 | 29 | 23.12 | 10.16 | 2.27x |
| DeepSeek-V4.1-Flash | 16 | 29 | 27.56 | 12.57 | 2.19x |
| DeepSeek-V4.1-Flash | 32 | 29 | 28.86 | 14.82 | 1.95x |
| DeepSeek-V4.1-Flash | 64 | 29 | 28.99 | 16.64 | 1.74x |
| DeepSeek-V4.1-Flash | 256 | 29 | 29.00 | 18.25 | 1.59x |
| DeepSeek-V4.1-Flash | 1024 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4.1-Flash | 4096 | 29 | 29.00 | 18.31 | 1.58x |
| DeepSeek-V4.1-Flash | 1 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4.1-Flash | 2 | 31 | 10.02 | 5.94 | 1.69x |
| DeepSeek-V4.1-Flash | 4 | 31 | 16.63 | 8.07 | 2.06x |
| DeepSeek-V4.1-Flash | 8 | 31 | 24.02 | 10.47 | 2.29x |
| DeepSeek-V4.1-Flash | 16 | 31 | 29.12 | 13.02 | 2.24x |
| DeepSeek-V4.1-Flash | 32 | 31 | 30.79 | 15.43 | 2.00x |
| DeepSeek-V4.1-Flash | 64 | 31 | 30.99 | 17.39 | 1.78x |
| DeepSeek-V4.1-Flash | 256 | 31 | 31.00 | 19.13 | 1.62x |
| DeepSeek-V4.1-Flash | 1024 | 31 | 31.00 | 19.20 | 1.61x |
| DeepSeek-V4.1-Flash | 4096 | 31 | 31.00 | 19.20 | 1.61x |
| DeepSeek-V4.1-Flash | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4.1-Flash | 2 | 38 | 10.34 | 6.29 | 1.64x |
| DeepSeek-V4.1-Flash | 4 | 38 | 17.66 | 8.67 | 2.04x |
| DeepSeek-V4.1-Flash | 8 | 38 | 26.69 | 11.45 | 2.33x |
| DeepSeek-V4.1-Flash | 16 | 38 | 34.12 | 14.46 | 2.36x |
| DeepSeek-V4.1-Flash | 32 | 38 | 37.34 | 17.39 | 2.15x |
| DeepSeek-V4.1-Flash | 64 | 38 | 37.94 | 19.83 | 1.91x |
| DeepSeek-V4.1-Flash | 256 | 38 | 38.00 | 22.03 | 1.72x |
| DeepSeek-V4.1-Flash | 1024 | 38 | 38.00 | 22.12 | 1.72x |
| DeepSeek-V4.1-Flash | 4096 | 38 | 38.00 | 22.12 | 1.72x |
| DeepSeek-V4.1-Flash | 1 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4.1-Flash | 2 | 43 | 10.51 | 6.50 | 1.62x |
| DeepSeek-V4.1-Flash | 4 | 43 | 18.23 | 9.04 | 2.02x |
| DeepSeek-V4.1-Flash | 8 | 43 | 28.24 | 12.05 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 43 | 37.25 | 15.38 | 2.42x |
| DeepSeek-V4.1-Flash | 32 | 43 | 41.80 | 18.66 | 2.24x |
| DeepSeek-V4.1-Flash | 64 | 43 | 42.86 | 21.42 | 2.00x |
| DeepSeek-V4.1-Flash | 256 | 43 | 42.99 | 23.94 | 1.80x |
| DeepSeek-V4.1-Flash | 1024 | 43 | 42.99 | 24.04 | 1.79x |
| DeepSeek-V4.1-Flash | 4096 | 43 | 42.99 | 24.04 | 1.79x |
| DeepSeek-V4.1-Flash | 1 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4.1-Flash | 2 | 44 | 10.54 | 6.54 | 1.61x |
| DeepSeek-V4.1-Flash | 4 | 44 | 18.33 | 9.11 | 2.01x |
| DeepSeek-V4.1-Flash | 8 | 44 | 28.53 | 12.16 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 44 | 37.84 | 15.55 | 2.43x |
| DeepSeek-V4.1-Flash | 32 | 44 | 42.66 | 18.90 | 2.26x |
| DeepSeek-V4.1-Flash | 64 | 44 | 43.84 | 21.72 | 2.02x |
| DeepSeek-V4.1-Flash | 256 | 44 | 43.99 | 24.31 | 1.81x |
| DeepSeek-V4.1-Flash | 1024 | 44 | 43.99 | 24.41 | 1.80x |
| DeepSeek-V4.1-Flash | 4096 | 44 | 43.99 | 24.41 | 1.80x |
| DeepSeek-V4.1-Flash | 1 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4.1-Flash | 2 | 48 | 10.64 | 6.69 | 1.59x |
| DeepSeek-V4.1-Flash | 4 | 48 | 18.70 | 9.37 | 2.00x |
| DeepSeek-V4.1-Flash | 8 | 48 | 29.57 | 12.59 | 2.35x |
| DeepSeek-V4.1-Flash | 16 | 48 | 40.07 | 16.21 | 2.47x |
| DeepSeek-V4.1-Flash | 32 | 48 | 46.04 | 19.82 | 2.32x |
| DeepSeek-V4.1-Flash | 64 | 48 | 47.72 | 22.90 | 2.08x |
| DeepSeek-V4.1-Flash | 256 | 48 | 47.98 | 25.74 | 1.86x |
| DeepSeek-V4.1-Flash | 1024 | 48 | 47.99 | 25.86 | 1.86x |
| DeepSeek-V4.1-Flash | 4096 | 48 | 47.99 | 25.86 | 1.86x |
| DeepSeek-V4.1-Flash | 1 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4.1-Flash | 2 | 50 | 10.69 | 6.77 | 1.58x |
| DeepSeek-V4.1-Flash | 4 | 50 | 18.86 | 9.49 | 1.99x |
| DeepSeek-V4.1-Flash | 8 | 50 | 30.04 | 12.80 | 2.35x |
| DeepSeek-V4.1-Flash | 16 | 50 | 41.12 | 16.53 | 2.49x |
| DeepSeek-V4.1-Flash | 32 | 50 | 47.68 | 20.27 | 2.35x |
| DeepSeek-V4.1-Flash | 64 | 50 | 49.64 | 23.47 | 2.11x |
| DeepSeek-V4.1-Flash | 256 | 50 | 49.98 | 26.43 | 1.89x |
| DeepSeek-V4.1-Flash | 1024 | 50 | 49.98 | 26.55 | 1.88x |
| DeepSeek-V4.1-Flash | 4096 | 50 | 49.98 | 26.55 | 1.88x |
| DeepSeek-V4.1-Flash | 1 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4.1-Flash | 2 | 52 | 10.73 | 6.84 | 1.57x |
| DeepSeek-V4.1-Flash | 4 | 52 | 19.02 | 9.60 | 1.98x |
| DeepSeek-V4.1-Flash | 8 | 52 | 30.49 | 12.99 | 2.35x |
| DeepSeek-V4.1-Flash | 16 | 52 | 42.12 | 16.83 | 2.50x |
| DeepSeek-V4.1-Flash | 32 | 52 | 49.28 | 20.70 | 2.38x |
| DeepSeek-V4.1-Flash | 64 | 52 | 51.54 | 24.02 | 2.15x |
| DeepSeek-V4.1-Flash | 256 | 52 | 51.97 | 27.11 | 1.92x |
| DeepSeek-V4.1-Flash | 1024 | 52 | 51.97 | 27.24 | 1.91x |
| DeepSeek-V4.1-Flash | 4096 | 52 | 51.97 | 27.24 | 1.91x |
| DeepSeek-V4.1-Flash | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4.1-Flash | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4.1-Flash | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4.1-Flash | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4.1-Flash | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4.1-Flash | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4.1-Flash | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4.1-Flash | 4096 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4.1-Flash | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash | 2 | 58 | 10.85 | 7.04 | 1.54x |
| DeepSeek-V4.1-Flash | 4 | 58 | 19.42 | 9.92 | 1.96x |
| DeepSeek-V4.1-Flash | 8 | 58 | 31.69 | 13.53 | 2.34x |
| DeepSeek-V4.1-Flash | 16 | 58 | 44.90 | 17.69 | 2.54x |
| DeepSeek-V4.1-Flash | 32 | 58 | 53.88 | 21.92 | 2.46x |
| DeepSeek-V4.1-Flash | 64 | 58 | 57.17 | 25.61 | 2.23x |
| DeepSeek-V4.1-Flash | 256 | 58 | 57.92 | 29.06 | 1.99x |
| DeepSeek-V4.1-Flash | 1024 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash | 4096 | 58 | 57.93 | 29.20 | 1.98x |
| DeepSeek-V4.1-Flash | 1 | 63 | 5.77 | 4.97 | 1.16x |
| DeepSeek-V4.1-Flash | 2 | 63 | 10.93 | 7.19 | 1.52x |
| DeepSeek-V4.1-Flash | 4 | 63 | 19.71 | 10.15 | 1.94x |
| DeepSeek-V4.1-Flash | 8 | 63 | 32.56 | 13.95 | 2.33x |
| DeepSeek-V4.1-Flash | 16 | 63 | 46.97 | 18.35 | 2.56x |
| DeepSeek-V4.1-Flash | 32 | 63 | 57.47 | 22.88 | 2.51x |
| DeepSeek-V4.1-Flash | 64 | 63 | 61.73 | 26.85 | 2.30x |
| DeepSeek-V4.1-Flash | 256 | 63 | 62.85 | 30.60 | 2.05x |
| DeepSeek-V4.1-Flash | 1024 | 63 | 62.86 | 30.75 | 2.04x |
| DeepSeek-V4.1-Flash | 4096 | 63 | 62.86 | 30.75 | 2.04x |
| DeepSeek-V4.1-Flash | 1 | 64 | 5.77 | 4.98 | 1.16x |
| DeepSeek-V4.1-Flash | 2 | 64 | 10.94 | 7.22 | 1.52x |
| DeepSeek-V4.1-Flash | 4 | 64 | 19.76 | 10.19 | 1.94x |
| DeepSeek-V4.1-Flash | 8 | 64 | 32.72 | 14.03 | 2.33x |
| DeepSeek-V4.1-Flash | 16 | 64 | 47.36 | 18.48 | 2.56x |
| DeepSeek-V4.1-Flash | 32 | 64 | 58.16 | 23.06 | 2.52x |
| DeepSeek-V4.1-Flash | 64 | 64 | 62.62 | 27.09 | 2.31x |
| DeepSeek-V4.1-Flash | 256 | 64 | 63.83 | 30.89 | 2.07x |
| DeepSeek-V4.1-Flash | 1024 | 64 | 63.85 | 31.05 | 2.06x |
| DeepSeek-V4.1-Flash | 4096 | 64 | 63.85 | 31.05 | 2.06x |
| DeepSeek-V4.1-Flash | 1 | 67 | 5.78 | 5.02 | 1.15x |
| DeepSeek-V4.1-Flash | 2 | 67 | 10.98 | 7.30 | 1.50x |
| DeepSeek-V4.1-Flash | 4 | 67 | 19.91 | 10.32 | 1.93x |
| DeepSeek-V4.1-Flash | 8 | 67 | 33.18 | 14.26 | 2.33x |
| DeepSeek-V4.1-Flash | 16 | 67 | 48.49 | 18.85 | 2.57x |
| DeepSeek-V4.1-Flash | 32 | 67 | 60.19 | 23.60 | 2.55x |
| DeepSeek-V4.1-Flash | 64 | 67 | 65.29 | 27.79 | 2.35x |
| DeepSeek-V4.1-Flash | 256 | 67 | 66.77 | 31.78 | 2.10x |
| DeepSeek-V4.1-Flash | 1024 | 67 | 66.79 | 31.94 | 2.09x |
| DeepSeek-V4.1-Flash | 4096 | 67 | 66.79 | 31.94 | 2.09x |
| DeepSeek-V4.1-Flash | 1 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4.1-Flash | 2 | 76 | 11.09 | 7.54 | 1.47x |
| DeepSeek-V4.1-Flash | 4 | 76 | 20.29 | 10.66 | 1.90x |
| DeepSeek-V4.1-Flash | 8 | 76 | 34.38 | 14.92 | 2.30x |
| DeepSeek-V4.1-Flash | 16 | 76 | 51.52 | 19.89 | 2.59x |
| DeepSeek-V4.1-Flash | 32 | 76 | 65.85 | 25.12 | 2.62x |
| DeepSeek-V4.1-Flash | 64 | 76 | 72.99 | 29.79 | 2.45x |
| DeepSeek-V4.1-Flash | 256 | 76 | 75.49 | 34.28 | 2.20x |
| DeepSeek-V4.1-Flash | 1024 | 76 | 75.53 | 34.47 | 2.19x |
| DeepSeek-V4.1-Flash | 4096 | 76 | 75.53 | 34.47 | 2.19x |
| DeepSeek-V4.1-Flash | 1 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4.1-Flash | 2 | 77 | 11.10 | 7.56 | 1.47x |
| DeepSeek-V4.1-Flash | 4 | 77 | 20.32 | 10.70 | 1.90x |
| DeepSeek-V4.1-Flash | 8 | 77 | 34.50 | 14.98 | 2.30x |
| DeepSeek-V4.1-Flash | 16 | 77 | 51.83 | 20.00 | 2.59x |
| DeepSeek-V4.1-Flash | 32 | 77 | 66.44 | 25.28 | 2.63x |
| DeepSeek-V4.1-Flash | 64 | 77 | 73.82 | 30.00 | 2.46x |
| DeepSeek-V4.1-Flash | 256 | 77 | 76.44 | 34.55 | 2.21x |
| DeepSeek-V4.1-Flash | 1024 | 77 | 76.49 | 34.74 | 2.20x |
| DeepSeek-V4.1-Flash | 4096 | 77 | 76.49 | 34.74 | 2.20x |
| DeepSeek-V4.1-Flash | 1 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4.1-Flash | 2 | 84 | 11.16 | 7.73 | 1.44x |
| DeepSeek-V4.1-Flash | 4 | 84 | 20.56 | 10.93 | 1.88x |
| DeepSeek-V4.1-Flash | 8 | 84 | 35.26 | 15.45 | 2.28x |
| DeepSeek-V4.1-Flash | 16 | 84 | 53.84 | 20.73 | 2.60x |
| DeepSeek-V4.1-Flash | 32 | 84 | 70.40 | 26.35 | 2.67x |
| DeepSeek-V4.1-Flash | 64 | 84 | 79.47 | 31.44 | 2.53x |
| DeepSeek-V4.1-Flash | 256 | 84 | 83.08 | 36.36 | 2.28x |
| DeepSeek-V4.1-Flash | 1024 | 84 | 83.15 | 36.57 | 2.27x |
| DeepSeek-V4.1-Flash | 4096 | 84 | 83.15 | 36.57 | 2.27x |
| DeepSeek-V4.1-Flash | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4.1-Flash | 2 | 87 | 11.19 | 7.80 | 1.44x |
| DeepSeek-V4.1-Flash | 4 | 87 | 20.65 | 11.02 | 1.87x |
| DeepSeek-V4.1-Flash | 8 | 87 | 35.56 | 15.63 | 2.27x |
| DeepSeek-V4.1-Flash | 16 | 87 | 54.63 | 21.03 | 2.60x |
| DeepSeek-V4.1-Flash | 32 | 87 | 71.99 | 26.79 | 2.69x |
| DeepSeek-V4.1-Flash | 64 | 87 | 81.81 | 32.02 | 2.55x |
| DeepSeek-V4.1-Flash | 256 | 87 | 85.89 | 37.11 | 2.31x |
| DeepSeek-V4.1-Flash | 1024 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4.1-Flash | 4096 | 87 | 85.97 | 37.32 | 2.30x |
| DeepSeek-V4.1-Flash | 1 | 90 | 5.84 | 5.22 | 1.12x |
| DeepSeek-V4.1-Flash | 2 | 90 | 11.21 | 7.86 | 1.43x |
| DeepSeek-V4.1-Flash | 4 | 90 | 20.74 | 11.11 | 1.87x |
| DeepSeek-V4.1-Flash | 8 | 90 | 35.84 | 15.82 | 2.27x |
| DeepSeek-V4.1-Flash | 16 | 90 | 55.39 | 21.32 | 2.60x |
| DeepSeek-V4.1-Flash | 32 | 90 | 73.53 | 27.22 | 2.70x |
| DeepSeek-V4.1-Flash | 64 | 90 | 84.10 | 32.60 | 2.58x |
| DeepSeek-V4.1-Flash | 256 | 90 | 88.67 | 37.84 | 2.34x |
| DeepSeek-V4.1-Flash | 1024 | 90 | 88.77 | 38.06 | 2.33x |
| DeepSeek-V4.1-Flash | 4096 | 90 | 88.77 | 38.06 | 2.33x |
| DeepSeek-V4.1-Flash | 1 | 91 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4.1-Flash | 2 | 91 | 11.22 | 7.88 | 1.42x |
| DeepSeek-V4.1-Flash | 4 | 91 | 20.77 | 11.14 | 1.86x |
| DeepSeek-V4.1-Flash | 8 | 91 | 35.93 | 15.88 | 2.26x |
| DeepSeek-V4.1-Flash | 16 | 91 | 55.63 | 21.42 | 2.60x |
| DeepSeek-V4.1-Flash | 32 | 91 | 74.03 | 27.36 | 2.71x |
| DeepSeek-V4.1-Flash | 64 | 91 | 84.85 | 32.79 | 2.59x |
| DeepSeek-V4.1-Flash | 256 | 91 | 89.59 | 38.08 | 2.35x |
| DeepSeek-V4.1-Flash | 1024 | 91 | 89.69 | 38.30 | 2.34x |
| DeepSeek-V4.1-Flash | 4096 | 91 | 89.69 | 38.30 | 2.34x |
| DeepSeek-V4.1-Flash | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash | 2 | 116 | 11.36 | 8.35 | 1.36x |
| DeepSeek-V4.1-Flash | 4 | 116 | 21.31 | 11.79 | 1.81x |
| DeepSeek-V4.1-Flash | 8 | 116 | 37.74 | 17.21 | 2.19x |
| DeepSeek-V4.1-Flash | 16 | 116 | 60.68 | 23.52 | 2.58x |
| DeepSeek-V4.1-Flash | 32 | 116 | 84.89 | 30.52 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 116 | 101.95 | 37.06 | 2.75x |
| DeepSeek-V4.1-Flash | 256 | 116 | 111.57 | 43.59 | 2.56x |
| DeepSeek-V4.1-Flash | 1024 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4.1-Flash | 4096 | 116 | 111.83 | 43.86 | 2.55x |
| DeepSeek-V4.1-Flash | 1 | 125 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4.1-Flash | 2 | 125 | 11.40 | 8.49 | 1.34x |
| DeepSeek-V4.1-Flash | 4 | 125 | 21.45 | 11.99 | 1.79x |
| DeepSeek-V4.1-Flash | 8 | 125 | 38.23 | 17.62 | 2.17x |
| DeepSeek-V4.1-Flash | 16 | 125 | 62.11 | 24.16 | 2.57x |
| DeepSeek-V4.1-Flash | 32 | 125 | 88.13 | 31.52 | 2.80x |
| DeepSeek-V4.1-Flash | 64 | 125 | 107.37 | 38.43 | 2.79x |
| DeepSeek-V4.1-Flash | 256 | 125 | 118.96 | 45.37 | 2.62x |
| DeepSeek-V4.1-Flash | 1024 | 125 | 119.28 | 45.67 | 2.61x |
| DeepSeek-V4.1-Flash | 4096 | 125 | 119.28 | 45.67 | 2.61x |
| DeepSeek-V4.1-Flash | 1 | 134 | 5.89 | 5.44 | 1.08x |
| DeepSeek-V4.1-Flash | 2 | 134 | 11.43 | 8.62 | 1.33x |
| DeepSeek-V4.1-Flash | 4 | 134 | 21.58 | 12.19 | 1.77x |
| DeepSeek-V4.1-Flash | 8 | 134 | 38.67 | 18.00 | 2.15x |
| DeepSeek-V4.1-Flash | 16 | 134 | 63.39 | 24.76 | 2.56x |
| DeepSeek-V4.1-Flash | 32 | 134 | 91.09 | 32.45 | 2.81x |
| DeepSeek-V4.1-Flash | 64 | 134 | 112.43 | 39.73 | 2.83x |
| DeepSeek-V4.1-Flash | 256 | 134 | 126.06 | 47.07 | 2.68x |
| DeepSeek-V4.1-Flash | 1024 | 134 | 126.45 | 47.38 | 2.67x |
| DeepSeek-V4.1-Flash | 4096 | 134 | 126.45 | 47.38 | 2.67x |
| DeepSeek-V4.1-Flash | 1 | 167 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 167 | 11.53 | 9.02 | 1.28x |
| DeepSeek-V4.1-Flash | 4 | 167 | 21.93 | 12.83 | 1.71x |
| DeepSeek-V4.1-Flash | 8 | 167 | 39.90 | 19.14 | 2.08x |
| DeepSeek-V4.1-Flash | 16 | 167 | 67.09 | 26.63 | 2.52x |
| DeepSeek-V4.1-Flash | 32 | 167 | 99.98 | 35.45 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 167 | 128.39 | 43.94 | 2.92x |
| DeepSeek-V4.1-Flash | 256 | 167 | 149.67 | 52.65 | 2.84x |
| DeepSeek-V4.1-Flash | 1024 | 167 | 150.36 | 53.03 | 2.84x |
| DeepSeek-V4.1-Flash | 4096 | 167 | 150.36 | 53.03 | 2.84x |
| DeepSeek-V4.1-Flash | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash | 2 | 173 | 11.54 | 9.09 | 1.27x |
| DeepSeek-V4.1-Flash | 4 | 173 | 21.98 | 12.94 | 1.70x |
| DeepSeek-V4.1-Flash | 8 | 173 | 40.08 | 19.31 | 2.08x |
| DeepSeek-V4.1-Flash | 16 | 173 | 67.63 | 26.93 | 2.51x |
| DeepSeek-V4.1-Flash | 32 | 173 | 101.33 | 35.95 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 173 | 130.91 | 44.63 | 2.93x |
| DeepSeek-V4.1-Flash | 256 | 173 | 153.57 | 53.58 | 2.87x |
| DeepSeek-V4.1-Flash | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4.1-Flash | 4096 | 173 | 154.32 | 53.96 | 2.86x |
| DeepSeek-V4.1-Flash | 1 | 179 | 5.92 | 5.57 | 1.06x |
| DeepSeek-V4.1-Flash | 2 | 179 | 11.55 | 9.15 | 1.26x |
| DeepSeek-V4.1-Flash | 4 | 179 | 22.03 | 13.04 | 1.69x |
| DeepSeek-V4.1-Flash | 8 | 179 | 40.24 | 19.48 | 2.07x |
| DeepSeek-V4.1-Flash | 16 | 179 | 68.14 | 27.23 | 2.50x |
| DeepSeek-V4.1-Flash | 32 | 179 | 102.61 | 36.43 | 2.82x |
| DeepSeek-V4.1-Flash | 64 | 179 | 133.34 | 45.30 | 2.94x |
| DeepSeek-V4.1-Flash | 256 | 179 | 157.37 | 54.48 | 2.89x |
| DeepSeek-V4.1-Flash | 1024 | 179 | 158.18 | 54.87 | 2.88x |
| DeepSeek-V4.1-Flash | 4096 | 179 | 158.18 | 54.87 | 2.88x |
| DeepSeek-V4.1-Flash | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 231 | 11.63 | 9.58 | 1.21x |
| DeepSeek-V4.1-Flash | 4 | 231 | 22.34 | 13.86 | 1.61x |
| DeepSeek-V4.1-Flash | 8 | 231 | 41.34 | 20.63 | 2.00x |
| DeepSeek-V4.1-Flash | 16 | 231 | 71.61 | 29.55 | 2.42x |
| DeepSeek-V4.1-Flash | 32 | 231 | 111.55 | 40.16 | 2.78x |
| DeepSeek-V4.1-Flash | 64 | 231 | 150.80 | 50.51 | 2.99x |
| DeepSeek-V4.1-Flash | 256 | 231 | 186.03 | 61.46 | 3.03x |
| DeepSeek-V4.1-Flash | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4.1-Flash | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4.1-Flash | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4.1-Flash | 2 | 347 | 11.72 | 10.18 | 1.15x |
| DeepSeek-V4.1-Flash | 4 | 347 | 22.70 | 15.30 | 1.48x |
| DeepSeek-V4.1-Flash | 8 | 347 | 42.66 | 22.28 | 1.92x |
| DeepSeek-V4.1-Flash | 16 | 347 | 75.90 | 33.59 | 2.26x |
| DeepSeek-V4.1-Flash | 32 | 347 | 123.23 | 45.96 | 2.68x |
| DeepSeek-V4.1-Flash | 64 | 347 | 175.33 | 59.00 | 2.97x |
| DeepSeek-V4.1-Flash | 256 | 347 | 230.16 | 73.28 | 3.14x |
| DeepSeek-V4.1-Flash | 1024 | 347 | 232.44 | 73.90 | 3.15x |
| DeepSeek-V4.1-Flash | 4096 | 347 | 232.44 | 73.90 | 3.15x |

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
| gpu | DeepSeek-V4.1-Flash | 1 | 10.05 | 4.3% |
| rom | DeepSeek-V4.1-Flash | 1 | 10.05 | 16.3% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash | sram | interleaved | 128 B | 1.42x |
| DeepSeek-V4.1-Flash | hbm | interleaved | 32 B | 1.12x |

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
| DeepSeek-V4.1-Flash | 1 | 42 | 1.78% | 11.78 | 15.79 |
| DeepSeek-V4.1-Flash | 2 | 42 | 1.78% | 11.78 | 15.79 |
| DeepSeek-V4.1-Flash | 4 | 42 | 1.78% | 11.78 | 15.79 |
| DeepSeek-V4.1-Flash | 8 | 42 | 1.78% | 11.78 | 15.79 |
| DeepSeek-V4.1-Flash | 16 | 42 | 1.78% | 11.78 | 15.79 |
| DeepSeek-V4.1-Flash | 32 | 42 | 1.78% | 11.78 | 15.79 |
| DeepSeek-V4.1-Flash | 64 | 1 | 0.04% | 0.33 | 15.79 |
| DeepSeek-V4.1-Flash | 256 | 1 | 0.15% | 1.34 | 15.79 |
| DeepSeek-V4.1-Flash | 1024 | 1 | 0.59% | 5.34 | 15.79 |

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
| DeepSeek-V4.1-Flash | 1 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 793.4 | 75,374.4 |
| DeepSeek-V4.1-Flash | 2 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 793.4 | 75,374.4 |
| DeepSeek-V4.1-Flash | 4 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 793.4 | 75,374.4 |
| DeepSeek-V4.1-Flash | 8 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 793.4 | 75,374.4 |
| DeepSeek-V4.1-Flash | 16 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 793.4 | 75,374.4 |
| DeepSeek-V4.1-Flash | 32 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 793.4 | 75,374.4 |
| DeepSeek-V4.1-Flash | 64 | 1.56% | 13.0 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 793.4 | 75,374.4 |
| DeepSeek-V4.1-Flash | 256 | 4.15% | 20.5 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 296.1 | 75,800.0 |
| DeepSeek-V4.1-Flash | 1024 | 15.61% | 53.6 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 74.2 | 75,989.9 |
| DeepSeek-V4.1-Flash | 4096 | 49.29% | 150.9 GB | 100.00% | 14,805.75 TB/s | 14,805.75 TB/s | 18.6 | 76,037.5 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 4 |
| gpu | link_latency | 1013 |
| gpu | thermal | 314 |
| gpu | weight_read | 659 |
| rom | compute | 1010 |
| rom | infeasible | 2248 |
| rom | kv_read | 90 |
| rom | link_latency | 1217 |
| rom | weight_read | 755 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2248 |

## Mechanical consistency audit

**FAIL** over 157,137 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x85', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x86', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x87', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x103', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x123', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x164', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x246', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x328', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x85', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x86', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x87', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x103', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x123', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x164', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x246', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x328', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x85', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x86', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x87', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x103', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x123', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x164', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x246', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x328', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x85', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x86', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x87', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x103', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x113', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x123', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x164', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x170', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x246', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x328', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x2', 'DeepSeek-V4.1-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x3', 'DeepSeek-V4.1-Flash', 1)

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

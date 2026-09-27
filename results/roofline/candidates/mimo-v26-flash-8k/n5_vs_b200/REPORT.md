# Area-constrained roofline: n5_vs_b200-mimo-v26-flash-8k

> CANDIDATE MODEL under n5_vs_b200: MiMo-V2.6-Flash at 8,192 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 60x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 2 devices. On the GPU side the correction reaches 6x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 29 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Flash takes 32 x 815 mm2 (26,080 mm2, array, KV in SRAM) at 4,433 tok/s per user and 170 tok/s per 1,000 mm2, holding 1 session, against 16 copies of one unified HBM die at the same silicon: 3.5x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Flash on 138,675 mm2 of ROM silicon at 6,422 tok/s per user against 139,200 mm2 of b200_sxm-x87-nvl72-hybrid at 1,383 tok/s: **4.6x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 12,189 resident sessions against the GPU cluster's 64,959. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 3.37x to it.** At 97,800 mm2 on MiMo-V2.6-Flash the pipeline-only GPU delivers 420.82 tok/s and the same silicon running tensor delivers 1,417 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.01x (MiMo-V2.6-Flash, ROM binding on `link_latency`) to 2.63x (MiMo-V2.6-Flash, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Flash engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 979 to 34,168 tok/s, and its rate with every slot occupied from 31,336 to 34,168. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 32 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 669 us over NVLink, capping per-user decode at 1,496 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 229.1 us and cap it at 4,364 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 7 of 10 operating points and an array 3; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 201 of 4174 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 58.5x of aggregate throughput (MiMo-V2.6-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 11.95x, on MiMo-V2.6-Flash at batch 4096, where the busiest region carries 2.99x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 61 of 4,174 feasible points (1.5%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `MiMo-V2.6-Flash/b200_sxm-x7-pipeline` at batch 4096 on 11,200 mm2, throttled 1.09x from 22 to 20 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 55% weight read against 54.7% weight read. The ROM sweep is not what melts it.


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

### MiMo-V2.6-Flash at 8,192 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-hybrid-x32`** -- 32 x 815 mm2 reticle dies, 26,080 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **4,432.9 tok/s per user** (0.23 ms/token), binding on `layer_fixed_latency`
- **170.0 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,433 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 1,626 W at 0.062 W/mm2, 366.8 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 16 copies of one unified HBM die -- `b200_sxm-x16-nvl72-tensor`, 25,600 mm2, area ratio 1.0188 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 26,080 | 25,600 | 1.0188 |
| user tok/s | 4,432.9 | 1,254.5 | 3.53x |
| aggregate tok/s | 4,433 | 1,254 | 0.65x |
| resident sessions | 1 | 11,288 | -- |
| J/token | 0.3668 | 5.8266 | 15.9x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 11,288 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x61-nvl72-tensor` at 97,600 mm2 and 1,417.2 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 6,512.3 | 70.4 | 8,126 | 4.61x |
| rank on per-user rate alone | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 6,512.3 | 70.4 | 8,126 | 4.61x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-hybrid-x30` | 24,450 | 3,655.3 | 149.5 | 1 | 2.94x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | 26,080 | 4,432.9 | 170.0 | 1 | 3.53x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | 26,080 | 4,432.9 | 170.0 | -- | 170.0 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x34` | 27,710 | 4,478.5 | 161.6 | 28.0 | 170.0 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x38` | 30,970 | 4,876.8 | 157.5 | 90.8 | 170.0 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x40` | 32,600 | 5,090.1 | 156.1 | 100.8 | 170.0 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x47` | 38,305 | 5,636.6 | 147.1 | 98.5 | 170.0 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x49` | 39,935 | 5,665.2 | 141.9 | 88.9 | 170.0 | stop |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 5,716.5 | 116.9 | 56.2 | 170.0 | stop |
| `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 6,512.3 | 70.4 | 31.3 | 170.0 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` **<-- recommended** | 26,080 | 32 | 4,432.9 | 4,433 | 170.0 | 1 | `layer_fixed_latency` | 1,626 | 366.8 | `b200_sxm-x16-nvl72-tensor` | 3.53x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x34` | 27,710 | 34 | 4,478.5 | 4,478 | 161.6 | 1 | `layer_fixed_latency` | 1,726 | 385.4 | `b200_sxm-x17-nvl72-tensor` | 3.54x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x38` | 30,970 | 38 | 4,876.8 | 24,384 | 157.5 | 17,953 | `layer_fixed_latency` | 3,385 | 583.0 | `b200_sxm-x19-nvl72-tensor` | 3.79x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x40` | 32,600 | 40 | 5,090.1 | 50,901 | 156.1 | 18,898 | `layer_fixed_latency` | 4,386 | 611.7 | `b200_sxm-x20-nvl72-tensor` | 3.93x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x47` | 38,305 | 47 | 5,636.6 | 67,639 | 147.1 | 22,205 | `layer_fixed_latency` | 5,776 | 719.2 | `b200_sxm-x24-nvl72-tensor` | 4.26x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x49` | 39,935 | 49 | 5,665.2 | 73,647 | 141.9 | 23,150 | `layer_fixed_latency` | 6,207 | 762.4 | `b200_sxm-x25-nvl72-tensor` | 4.26x |
| `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 60 | 5,716.5 | 85,747 | 116.9 | 28,347 | `layer_fixed_latency` | 7,616 | 943.5 | `b200_sxm-x31-nvl72-tensor` | 4.21x |
| `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 2 | 6,512.3 | 52,098 | 70.4 | 8,126 | `layer_fixed_latency` | 12,778 | 1,767.8 | `b200_sxm-x58-nvl72-tensor` | 4.61x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 336 | densest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | 26,080 | 4,432.9 | 170.0 | 1 |
| array | 336 | fastest | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 5,716.5 | 116.9 | 28,347 |
| array | 336 | smallest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x30` | 24,450 | 3,655.3 | 149.5 | 1 |
| wafer | 76 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,526.8 | 119.6 | 1 |
| wafer | 76 | fastest | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 6,512.3 | 70.4 | 8,126 |
| wafer | 76 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,526.8 | 119.6 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 5,716.5 | 85,747 | 28,347 | 7,616 | 943.5 | `layer_fixed_latency` | `b200_sxm-x31-nvl72-tensor` | 1,356.6 | 22,627 | 9,364.8 | 0.986 | 4.21x | 9.9x |
| 1 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 6,512.3 | 52,098 | 8,126 | 12,778 | 1,767.8 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 1,413.8 | 43,037 | 15,733.5 | 0.996 | 4.61x | 8.9x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 92,095 | 5,580.9 | 161,845 | 53,388 | 14,354 | 1,794.3 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 1,413.8 | 43,037 | 15,733.5 | 0.992 | 3.95x | 8.8x |
| 1 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 6,512.3 | -- | 8,126 | -- | 1,767.8 | -- | -- | -- | -- | -- | 0.996 | 1.17x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 5,716.5 | 85,747 | 28,347 | 7,616 | 485.6 | `layer_fixed_latency` | `b200_sxm-x31-nvl72-tensor` | 1,305.7 | 22,627 | 5,106.9 | 0.986 | 4.38x | 10.5x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 6,512.3 | 52,098 | 8,126 | 12,778 | 897.8 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 1,380.6 | 43,037 | 8,308.1 | 0.996 | 4.72x | 9.3x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 92,095 | 5,580.9 | 161,845 | 53,388 | 14,354 | 911.0 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 1,380.6 | 43,037 | 8,308.1 | 0.992 | 4.04x | 9.1x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 6,512.3 | -- | 8,126 | -- | 897.8 | -- | -- | -- | -- | -- | 0.996 | 1.17x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 5,716.5 | 85,747 | 28,347 | 7,616 | 256.7 | `layer_fixed_latency` | `b200_sxm-x31-nvl72-tensor` | 1,217.9 | 22,627 | 2,960.0 | 0.986 | 4.69x | 11.5x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 6,512.3 | 52,098 | 8,126 | 12,778 | 462.8 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 1,320.7 | 43,037 | 4,577.4 | 0.996 | 4.93x | 9.9x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 92,095 | 5,580.9 | 161,845 | 53,388 | 14,354 | 469.4 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 1,320.7 | 43,037 | 4,577.4 | 0.992 | 4.23x | 9.8x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 6,512.3 | -- | 8,126 | -- | 462.8 | -- | -- | -- | -- | -- | 0.996 | 1.17x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x60-romfill` | 48,900 | 5,716.5 | 85,747 | 28,347 | 7,616 | 142.2 | `layer_fixed_latency` | `b200_sxm-x31-nvl72-tensor` | 1,083.1 | 22,627 | 1,853.2 | 0.986 | 5.28x | 13.0x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 6,512.3 | 52,098 | 8,126 | 12,778 | 245.3 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 1,222.0 | 43,037 | 2,678.6 | 0.996 | 5.33x | 10.9x |
| 8 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x113-romfill` | 92,095 | 5,580.9 | 161,845 | 53,388 | 14,354 | 248.6 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 1,222.0 | 43,037 | 2,678.6 | 0.992 | 4.57x | 10.8x |
| 8 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | 6,512.3 | -- | 8,126 | -- | 245.3 | -- | -- | -- | -- | -- | 0.996 | 1.17x wafer/array | -- |
| 16 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x90-romfill` | 73,350 | 5,630.3 | 129,496 | 42,521 | 11,449 | 114.9 | `layer_fixed_latency` | `b200_sxm-x46-nvl72-tensor` | 1,023.3 | 33,966 | 1,480.6 | 0.997 | 5.50x | 12.9x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 6,352.9 | 139,764 | 24,379 | 28,481 | 269.8 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,271.3 | 129,970 | 3,649.9 | 1.002 | 5.00x | 13.5x |
| 16 | array @ wafer area | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 5,472.4 | 465,151 | 160,637 | 42,582 | 366.6 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 1,271.3 | 129,970 | 3,649.9 | 1.001 | 4.30x | 10.0x |
| 16 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 6,352.9 | -- | 24,379 | -- | 269.8 | -- | -- | -- | -- | -- | 0.999 | 1.16x wafer/array | -- |
| 32 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x170-romfill` | 138,550 | 5,495.4 | 236,302 | 80,318 | 21,394 | 112.1 | `layer_fixed_latency` | `b200_sxm-x87-nvl72-hybrid` | 1,001.3 | 64,959 | 1,447.6 | 0.995 | 5.49x | 12.9x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 6,240.7 | 268,351 | 48,758 | 56,651 | 274.1 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 1,262.4 | 261,504 | 3,646.4 | 0.999 | 4.94x | 13.3x |
| 64 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 5,472.4 | 465,151 | 160,637 | 42,582 | 112.5 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 998.3 | 129,970 | 1,401.4 | 1.001 | 5.48x | 12.5x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 6,047.0 | 520,042 | 48,758 | 63,642 | 154.9 | `layer_fixed_latency` | `b200_sxm-x347-nvl72-hybrid` | 1,142.3 | 261,504 | 2,192.2 | 0.999 | 5.29x | 14.2x |
| 256 | array | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 4,472.1 | 1,144,856 | 160,637 | 60,534 | 52.9 | `layer_fixed_latency` | `b200_sxm-x173-nvl72-hybrid` | 678.9 | 129,970 | 568.1 | 1.001 | 6.59x | 10.7x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,122.1 | 1,055,255 | 48,758 | 77,663 | 73.6 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 818.9 | 261,504 | 885.9 | 0.999 | 5.03x | 12.0x |
| 1024 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 1,830.9 | 1,874,867 | 160,637 | 78,675 | 42.0 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 413.1 | 129,970 | 271.6 | 1.001 | 4.43x | 6.5x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 1,614.2 | 1,652,964 | 48,758 | 93,773 | 56.7 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 509.4 | 261,504 | 361.4 | 0.999 | 3.17x | 6.4x |
| 4096 | array | `ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 525.0 | 2,150,318 | 160,637 | 84,189 | 39.2 | `compute` | `b200_sxm-x173-nvl72-hybrid` | 221.7 | 129,970 | 139.3 | 1.001 | 2.37x | 3.6x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 452.3 | 1,852,781 | 48,758 | 96,778 | 52.2 | `kv_read` | `b200_sxm-x347-nvl72-hybrid` | 285.3 | 261,504 | 176.6 | 0.999 | 1.59x | 3.4x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | 26,080 | array | SRAM | 1 |
| 2-4 | `ROM-N5-native-HBMKV-array-hw-hybrid-x38` | 30,970 | array | HBM | 17,953 |
| 8 | `ROM-N5-native-HBMKV-array-hw-hybrid-x40` | 32,600 | array | HBM | 18,898 |
| 16 | `ROM-N5-native-HBMKV-array-hw-hybrid-x47` | 38,305 | array | HBM | 22,205 |
| 32 | `ROM-N5-native-HBMKV-array-hw-hybrid-x49` | 39,935 | array | HBM | 23,150 |
| 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x57` | 46,455 | array | HBM | 26,930 |
| 256 | `ROM-N5-native-HBMKV-array-hw-pipeline-x60` | 48,900 | array | HBM | 28,347 |
| 1024 | `ROM-N5-native-HBMKV-array-hw-hybrid-x90` | 73,350 | array | HBM | 42,521 |
| 4096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x113` | 92,095 | array | HBM | 53,388 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Flash | HBM | rom | 32, 38, 40, 45, 47, 49, 57, 60, 90, 113, 120, 170, 227, 340 |
| MiMo-V2.6-Flash | HBM | sram | 32, 38, 40, 45, 47, 49, 57, 60, 90, 113, 120, 170, 227, 340 |
| MiMo-V2.6-Flash | SRAM | rom | 30, 31, 32, 34, 35, 42, 56, 57, 84, 112, 113, 170, 227, 340 |
| MiMo-V2.6-Flash | SRAM | sram | 30, 31, 32, 34, 35, 42, 56, 57, 84, 112, 113, 170, 227, 340 |

A wafer chosen over the array class is now compared against an array sampled at the wafer's own area and at four rungs above the array's floor; the `array @ wafer area` rows in the iso-area table above are that comparison. The curve BETWEEN rungs is still not evidence and must not be read as any.

## Serial latency and collectives

The serial part of every step is the longest path of one token's operator
dependency graph (`src/opentallas/critical_path.py`): the dependent-operator
chain priced with measured RTL depths (ROM) or, on the GPU, a megakernel/PDL
execution in which every remaining dependent boundary pays only its measured
residual dependency signal (all-SM gather or one-to-one handoff, no launch;
`serial_latency.gpu_datapath`), every collective the weight split needs with its
latency and real payload, and every pipeline hop. A hybrid layout's tensor
group and every collective's reduction algorithm are searched per point.
`legacy` is the flat per-layer floor plus two all-reduces per layer this
replaced.

| Model | Design | Batch | Group | Coll./layer | Algorithms | Chain (us) | Comm. (us) | Sweep (us) | Legacy serial (us) | tok/s/user |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x32` | 1 | 8 | 3.00 | hierarchical | 115.70 | 69.64 | 48.24 | 59.06 | 4,432.9 |
| MiMo-V2.6-Flash | `b200_sxm-x16-nvl72-tensor` | 1 | 16 | 3.00 | measured_floor | 323.95 | 348.93 | 124.29 | 243.69 | 1,254.5 |
| MiMo-V2.6-Flash | `b200_sxm-x16-nvl72-tensor` | 64 | 16 | 3.00 | measured_floor | 323.95 | 558.52 | 1,554.28 | 398.52 | 410.4 |

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
| A100 80GB, weight-bound gate, same model and batch | 1.487141 J/token | 352.1 | 236.7 |

That is a factor of 206 in tokens per joule, and **it is a ceiling on the ROM advantage, not a measurement of it**, for three reasons that all point the same way. The GPU is at batch 1, which is a GPU's worst operating point -- it re-reads the whole checkpoint from DRAM for one token, and the batched rows in the table below are the fair comparison. The ROM side's read energy is `assumed` over a 17x bracket. And the HC1 power gate says this model's ROM total is 2.6-3.2x below the shipping part's published card power, so the ROM joules here are a lower bound by roughly that factor.

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

- **61 of 4,174 feasible points (1.5%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 61.
- By area class: large array (5,000-40,000 mm2) 35, wafer (>=40,000 mm2) 26.
- By KV store: hbm 61.
- By batch: B=64 2, B=256 14, B=1024 21, B=4096 24.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 45% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 64 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 640 | 35 | 56.5% | 100.0% | 0.625 | 62% |
| gpu | wafer (>=40,000 mm2) | 830 | 26 | 41.8% | 100.0% | 0.625 | 84% |
| rom | large array (5,000-40,000 mm2) | 1,092 | 0 | 23.3% | 87.8% | 0.439 | 72% |
| rom | wafer (>=40,000 mm2) | 1,612 | 0 | 29.3% | 92.5% | 0.463 | 87% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `MiMo-V2.6-Flash/b200_sxm-x7-pipeline` | MiMo-V2.6-Flash | 4096 | 11,200 | hbm | 1.087x | 7,000.0 / 7,000.0 W | 35% | 20.1 | 21.9 |
| `MiMo-V2.6-Flash/b200_sxm-x8-pipeline` | MiMo-V2.6-Flash | 4096 | 12,800 | hbm | 1.083x | 8,000.0 / 8,000.0 W | 35% | 21.3 | 23.1 |
| `MiMo-V2.6-Flash/b200_sxm-x15-pipeline` | MiMo-V2.6-Flash | 4096 | 24,000 | hbm | 1.065x | 15,000.0 / 15,000.0 W | 35% | 26.5 | 28.2 |
| `MiMo-V2.6-Flash/b200_sxm-x16-pipeline` | MiMo-V2.6-Flash | 4096 | 25,600 | hbm | 1.063x | 16,000.0 / 16,000.0 W | 35% | 27.0 | 28.7 |
| `MiMo-V2.6-Flash/b200_sxm-x17-pipeline` | MiMo-V2.6-Flash | 4096 | 27,200 | hbm | 1.061x | 17,000.0 / 17,000.0 W | 35% | 27.4 | 29.0 |
| `MiMo-V2.6-Flash/b200_sxm-x18-pipeline` | MiMo-V2.6-Flash | 4096 | 28,800 | hbm | 1.059x | 18,000.0 / 18,000.0 W | 35% | 27.8 | 29.4 |
| `MiMo-V2.6-Flash/b200_sxm-x19-pipeline` | MiMo-V2.6-Flash | 4096 | 30,400 | hbm | 1.058x | 19,000.0 / 19,000.0 W | 35% | 28.2 | 29.8 |
| `MiMo-V2.6-Flash/b200_sxm-x20-pipeline` | MiMo-V2.6-Flash | 4096 | 32,000 | hbm | 1.057x | 20,000.0 / 20,000.0 W | 35% | 28.5 | 30.1 |
| `MiMo-V2.6-Flash/b200_sxm-x21-pipeline` | MiMo-V2.6-Flash | 4096 | 33,600 | hbm | 1.056x | 21,000.0 / 21,000.0 W | 35% | 28.8 | 30.4 |
| `MiMo-V2.6-Flash/b200_sxm-x23-pipeline` | MiMo-V2.6-Flash | 4096 | 36,800 | hbm | 1.055x | 23,000.0 / 23,000.0 W | 35% | 29.4 | 31.0 |
| `MiMo-V2.6-Flash/b200_sxm-x7-pipeline` | MiMo-V2.6-Flash | 1024 | 11,200 | hbm | 1.055x | 7,000.0 / 7,000.0 W | 35% | 30.6 | 32.3 |
| `MiMo-V2.6-Flash/b200_sxm-x24-pipeline` | MiMo-V2.6-Flash | 4096 | 38,400 | hbm | 1.054x | 24,000.0 / 24,000.0 W | 35% | 29.7 | 31.3 |

The worst point's dynamic energy is weight read 54.7%, kv read 40.7%, arithmetic 4.3%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| MiMo-V2.6-Flash | 1 | 92,450 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2` | 1.767772 | 12,778.3 | layer_fixed_latency | `MiMo-V2.6-Flash/b200_sxm-x58-nvl72-tensor` | 15.733538 | 22,243.8 | link_latency | 8.90x |
| MiMo-V2.6-Flash | 2 | 92,450 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2` | 0.897772 | 12,778.3 | layer_fixed_latency | `MiMo-V2.6-Flash/b200_sxm-x58-nvl72-tensor` | 8.308098 | 22,939.9 | link_latency | 9.25x |
| MiMo-V2.6-Flash | 4 | 92,450 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2` | 0.462772 | 12,778.3 | layer_fixed_latency | `MiMo-V2.6-Flash/b200_sxm-x58-nvl72-tensor` | 4.577398 | 24,181.7 | link_latency | 9.89x |
| MiMo-V2.6-Flash | 8 | 92,450 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2` | 0.245273 | 12,778.3 | layer_fixed_latency | `MiMo-V2.6-Flash/b200_sxm-x58-nvl72-tensor` | 2.678636 | 26,185.5 | link_latency | 10.92x |
| MiMo-V2.6-Flash | 16 | 138,675 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 0.154021 | 16,020.0 | layer_fixed_latency | `MiMo-V2.6-Flash/b200_sxm-x87-nvl72-hybrid` | 2.245960 | 41,588.2 | link_latency | 14.58x |
| MiMo-V2.6-Flash | 32 | 277,350 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 0.154665 | 31,834.1 | layer_fixed_latency | `MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid` | 2.197547 | 81,142.6 | link_latency | 14.21x |
| MiMo-V2.6-Flash | 64 | 554,700 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.154898 | 63,641.6 | layer_fixed_latency | `MiMo-V2.6-Flash/b200_sxm-x347-nvl72-hybrid` | 2.192213 | 160,264.6 | link_latency | 14.15x |
| MiMo-V2.6-Flash | 256 | 277,100 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.052874 | 60,533.5 | layer_fixed_latency | `MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid` | 0.568140 | 98,742.2 | link_latency | 10.75x |
| MiMo-V2.6-Flash | 1024 | 277,100 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.041963 | 78,674.8 | compute | `MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid` | 0.271598 | 114,896.8 | link_latency | 6.47x |
| MiMo-V2.6-Flash | 4096 | 277,100 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.039152 | 84,188.7 | compute | `MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid` | 0.139274 | 126,475.6 | link_latency | 3.56x |

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
| MiMo-V2.6-Flash | 8,192 | 309 B | 172.9 GB | 4.48 | 0.214 GB | 0.214 GB | 59.1 |

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
| MiMo-V2.6-Flash | 1 | 46,225 | 8,486.3 | wafer-pipeline | 5,526.8 | wafer-tensor | 1.54x | 2,318.3 | pipeline | 1,348.5 | tensor | 1.72x | 3.66x | 4.10x | 1.12x |
| MiMo-V2.6-Flash | 2 | 92,450 | 8,902.6 | wafer-pipeline | 6,512.3 | wafer-hybrid | 1.37x | 2,369.6 | pipeline | 1,413.8 | tensor | 1.68x | 3.76x | 4.61x | 1.23x |
| MiMo-V2.6-Flash | 3 | 138,675 | 8,934.2 | wafer-pipeline | 6,422.4 | wafer-hybrid | 1.39x | 2,435.5 | pipeline | 1,383.2 | hybrid | 1.76x | 3.67x | 4.64x | 1.27x |
| MiMo-V2.6-Flash | 4 | 184,900 | 8,947.8 | wafer-pipeline | 6,383.9 | wafer-hybrid | 1.40x | 2,469.9 | pipeline | 1,405.4 | hybrid | 1.76x | 3.62x | 4.54x | 1.25x |
| MiMo-V2.6-Flash | 6 | 277,350 | 8,960.2 | wafer-pipeline | 6,352.9 | wafer-hybrid | 1.41x | 2,504.9 | pipeline | 1,400.7 | hybrid | 1.79x | 3.58x | 4.54x | 1.27x |
| MiMo-V2.6-Flash | 8 | 369,800 | 8,969.1 | wafer-pipeline | 6,318.7 | wafer-hybrid | 1.42x | 2,523.1 | pipeline | 1,396.5 | hybrid | 1.81x | 3.55x | 4.52x | 1.27x |
| MiMo-V2.6-Flash | 12 | 554,700 | 8,978.0 | wafer-pipeline | 6,240.7 | wafer-hybrid | 1.44x | 2,541.6 | pipeline | 1,403.5 | hybrid | 1.81x | 3.53x | 4.45x | 1.26x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.12x to 1.27x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Flash | 1 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 6,512.3 | 52,098.3 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x58-nvl72-tensor | 92,800 | 1.00x | tensor | 349.09 | 1,413.8 | 1,413.8 | link_latency | 4.61x | 2.13x | 15.48x | 4.61x |
| MiMo-V2.6-Flash | 1 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x30 | 24,450 | 3,655.3 | 3,655.3 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x15-nvl72-tensor | 24,000 | 1.02x | tensor | 348.91 | 1,241.6 | 1,241.6 | link_latency | 2.94x | 0.57x | 8.53x | 2.94x |
| MiMo-V2.6-Flash | 2 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 6,512.3 | 52,098.3 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x58-nvl72-tensor | 92,800 | 1.00x | tensor | 352.58 | 1,380.6 | 2,761.1 | link_latency | 4.72x | 2.13x | 15.48x | 4.72x |
| MiMo-V2.6-Flash | 2 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x32 | 26,080 | 3,466.5 | 13,865.9 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 352.25 | 1,177.1 | 2,354.2 | link_latency | 2.94x | 2.02x | 8.09x | 2.94x |
| MiMo-V2.6-Flash | 4 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 6,512.3 | 52,098.3 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x58-nvl72-tensor | 92,800 | 1.00x | tensor | 359.55 | 1,320.7 | 5,282.9 | link_latency | 4.93x | 2.13x | 15.48x | 4.93x |
| MiMo-V2.6-Flash | 4 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x32 | 26,080 | 3,466.5 | 13,865.9 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 358.91 | 1,052.7 | 4,211.0 | link_latency | 3.29x | 2.02x | 8.09x | 3.29x |
| MiMo-V2.6-Flash | 8 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 6,512.3 | 52,098.3 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x58-nvl72-tensor | 92,800 | 1.00x | tensor | 373.50 | 1,222.0 | 9,775.7 | link_latency | 5.33x | 2.13x | 15.48x | 5.33x |
| MiMo-V2.6-Flash | 8 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x32 | 26,080 | 2,710.4 | 21,682.9 | compute | MiMo-V2.6-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 372.22 | 881.5 | 7,051.9 | weight_read | 3.07x | 3.07x | 6.33x | 3.07x |
| MiMo-V2.6-Flash | 16 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 6,352.9 | 139,764.2 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 372.07 | 1,271.3 | 20,340.9 | link_latency | 5.00x | 1.92x | 15.10x | 5.00x |
| MiMo-V2.6-Flash | 16 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x32 | 26,080 | 1,774.0 | 28,384.0 | compute | MiMo-V2.6-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 398.83 | 690.8 | 11,053.0 | weight_read | 2.57x | 2.57x | 4.14x | 2.57x |
| MiMo-V2.6-Flash | 32 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 6,240.7 | 268,351.0 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 382.34 | 1,262.4 | 40,398.2 | link_latency | 4.94x | 1.84x | 14.83x | 4.94x |
| MiMo-V2.6-Flash | 32 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x32 | 26,080 | 979.2 | 31,336.0 | compute | MiMo-V2.6-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 452.06 | 524.7 | 16,791.5 | weight_read | 1.87x | 1.87x | 3.05x | 1.87x |
| MiMo-V2.6-Flash | 64 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 6,047.0 | 520,042.0 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x347-nvl72-hybrid | 555,200 | 1.00x | hybrid | 408.93 | 1,142.3 | 73,106.3 | link_latency | 5.29x | 3.56x | 14.37x | 5.29x |
| MiMo-V2.6-Flash | 64 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x32 | 26,080 | 511.4 | 32,731.7 | compute | MiMo-V2.6-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 558.52 | 410.4 | 26,264.4 | weight_read | 1.25x | 1.25x | 2.36x | 1.25x |
| MiMo-V2.6-Flash | 256 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 4,472.1 | 1,144,855.8 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 677.76 | 678.9 | 173,799.1 | link_latency | 6.59x | 6.59x | 12.33x | 6.59x |
| MiMo-V2.6-Flash | 256 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x32 | 26,080 | 132.3 | 33,862.9 | compute | MiMo-V2.6-Flash/b200_sxm-x16-nvl72-tensor | 25,600 | 1.02x | tensor | 1,197.30 | 272.1 | 69,646.3 | weight_read | 0.49x | 0.49x | 1.62x | 0.49x |
| MiMo-V2.6-Flash | 1024 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 1,830.9 | 1,874,867.2 | compute | MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 1,002.63 | 413.1 | 423,039.4 | link_latency | 4.43x | 4.43x | 11.03x | 4.43x |
| MiMo-V2.6-Flash | 1024 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x32 | 26,080 | 33.3 | 34,141.9 | compute | MiMo-V2.6-Flash/b200_sxm-x16-hybrid | 25,600 | 1.02x | hybrid | 2,023.46 | 129.6 | 132,700.0 | weight_read | 0.26x | 0.26x | 0.88x | 0.26x |
| MiMo-V2.6-Flash | 4096 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 525.0 | 2,150,317.9 | compute | MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid | 276,800 | 1.00x | hybrid | 1,749.31 | 221.7 | 908,104.9 | link_latency | 2.37x | 2.37x | 8.35x | 2.37x |
| MiMo-V2.6-Flash | 4096 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x32 | 26,080 | 8.3 | 34,168.4 | compute | MiMo-V2.6-Flash/b200_sxm-x16-hybrid | 25,600 | 1.02x | hybrid | 3,264.07 | 53.9 | 220,641.6 | kv_read | 0.15x | 0.15x | 0.31x | 0.15x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| MiMo-V2.6-Flash | 7 | 11,200 | 348.64 | 232.65 | 1,045.3 | 1,189.5 |
| MiMo-V2.6-Flash | 8 | 12,800 | 348.71 | 232.69 | 1,085.5 | 1,241.9 |
| MiMo-V2.6-Flash | 15 | 24,000 | 348.91 | 232.85 | 1,241.6 | 1,450.6 |
| MiMo-V2.6-Flash | 16 | 25,600 | 348.93 | 232.86 | 1,254.5 | 1,468.2 |
| MiMo-V2.6-Flash | 17 | 27,200 | 348.94 | 232.87 | 1,266.0 | 1,484.1 |
| MiMo-V2.6-Flash | 18 | 28,800 | 348.95 | 232.88 | 1,276.5 | 1,498.6 |
| MiMo-V2.6-Flash | 19 | 30,400 | 348.96 | 232.88 | 1,286.1 | 1,511.7 |
| MiMo-V2.6-Flash | 20 | 32,000 | 348.97 | 232.89 | 1,294.8 | 1,523.8 |
| MiMo-V2.6-Flash | 21 | 33,600 | 348.98 | 232.90 | 1,302.7 | 1,534.8 |
| MiMo-V2.6-Flash | 23 | 36,800 | 348.99 | 232.91 | 1,316.8 | 1,554.4 |
| MiMo-V2.6-Flash | 24 | 38,400 | 349.00 | 232.91 | 1,323.1 | 1,563.2 |
| MiMo-V2.6-Flash | 25 | 40,000 | 349.01 | 232.92 | 1,328.9 | 1,571.3 |
| MiMo-V2.6-Flash | 29 | 46,400 | 349.03 | 232.93 | 1,348.5 | 1,598.8 |
| MiMo-V2.6-Flash | 31 | 49,600 | 349.03 | 232.94 | 1,356.6 | 1,610.2 |
| MiMo-V2.6-Flash | 43 | 68,800 | 349.07 | 232.96 | 1,390.3 | 1,657.9 |
| MiMo-V2.6-Flash | 46 | 73,600 | 349.07 | 232.96 | 1,396.2 | 1,666.3 |
| MiMo-V2.6-Flash | 57 | 91,200 | 349.09 | 232.98 | 1,412.6 | 1,689.7 |
| MiMo-V2.6-Flash | 58 | 92,800 | 349.09 | 232.98 | 1,413.8 | 1,691.4 |
| MiMo-V2.6-Flash | 61 | 97,600 | 349.09 | 232.98 | 1,417.2 | 1,696.3 |
| MiMo-V2.6-Flash | 87 | 139,200 | 353.32 | 235.18 | 1,383.2 | 1,653.3 |
| MiMo-V2.6-Flash | 116 | 185,600 | 353.32 | 235.18 | 1,405.4 | 1,685.2 |
| MiMo-V2.6-Flash | 173 | 276,800 | 355.51 | 237.37 | 1,400.7 | 1,678.4 |
| MiMo-V2.6-Flash | 231 | 369,600 | 357.70 | 239.57 | 1,396.5 | 1,672.4 |
| MiMo-V2.6-Flash | 347 | 555,200 | 359.90 | 241.76 | 1,403.5 | 1,682.5 |

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
| MiMo-V2.6-Flash | 7 | 11,200 | 430.8 | 1,045.3 | — | tensor | 348.64 | 36.4% | link_latency |
| MiMo-V2.6-Flash | 8 | 12,800 | 430.6 | 1,085.5 | — | tensor | 348.71 | 37.9% | link_latency |
| MiMo-V2.6-Flash | 15 | 24,000 | 428.7 | 1,241.6 | 1,061.5 | tensor | 348.91 | 43.3% | link_latency |
| MiMo-V2.6-Flash | 16 | 25,600 | 428.5 | 1,254.5 | 1,080.6 | tensor | 348.93 | 43.8% | link_latency |
| MiMo-V2.6-Flash | 17 | 27,200 | 428.1 | 1,266.0 | 970.9 | tensor | 348.94 | 44.2% | link_latency |
| MiMo-V2.6-Flash | 18 | 28,800 | 427.9 | 1,276.5 | 989.6 | tensor | 348.95 | 44.5% | link_latency |
| MiMo-V2.6-Flash | 19 | 30,400 | 427.7 | 1,286.1 | 1,007.0 | tensor | 348.96 | 44.9% | link_latency |
| MiMo-V2.6-Flash | 20 | 32,000 | 427.4 | 1,294.8 | 1,023.2 | tensor | 348.97 | 45.2% | link_latency |
| MiMo-V2.6-Flash | 21 | 33,600 | 427.2 | 1,302.7 | 1,038.3 | tensor | 348.98 | 45.5% | link_latency |
| MiMo-V2.6-Flash | 23 | 36,800 | 426.8 | 1,316.8 | 1,065.6 | tensor | 348.99 | 46.0% | link_latency |
| MiMo-V2.6-Flash | 24 | 38,400 | 426.6 | 1,323.1 | 1,078.0 | tensor | 349.00 | 46.2% | link_latency |
| MiMo-V2.6-Flash | 25 | 40,000 | 426.2 | 1,328.9 | 1,000.6 | tensor | 349.01 | 46.4% | link_latency |
| MiMo-V2.6-Flash | 29 | 46,400 | 425.3 | 1,348.5 | 1,046.5 | tensor | 349.03 | 47.1% | link_latency |
| MiMo-V2.6-Flash | 31 | 49,600 | 424.8 | 1,356.6 | 1,066.3 | tensor | 349.03 | 47.4% | link_latency |
| MiMo-V2.6-Flash | 43 | 68,800 | 421.9 | 1,390.3 | 1,038.3 | tensor | 349.07 | 48.5% | link_latency |
| MiMo-V2.6-Flash | 46 | 73,600 | 421.2 | 1,396.2 | 1,058.2 | tensor | 349.07 | 48.7% | link_latency |
| MiMo-V2.6-Flash | 57 | 91,200 | 420.8 | 1,412.6 | 1,031.8 | tensor | 349.09 | 49.3% | link_latency |
| MiMo-V2.6-Flash | 58 | 92,800 | 420.8 | 1,413.8 | 1,037.0 | tensor | 349.09 | 49.4% | link_latency |
| MiMo-V2.6-Flash | 61 | 97,600 | 420.8 | 1,417.2 | 1,051.7 | tensor | 349.09 | 49.5% | link_latency |
| MiMo-V2.6-Flash | 87 | 139,200 | 420.8 | 646.7 | 1,383.2 | hybrid | 353.32 | 48.9% | link_latency |
| MiMo-V2.6-Flash | 116 | 185,600 | 420.8 | 649.1 | 1,405.4 | hybrid | 353.32 | 49.7% | link_latency |
| MiMo-V2.6-Flash | 173 | 276,800 | 420.8 | 647.0 | 1,400.7 | hybrid | 355.51 | 49.8% | link_latency |
| MiMo-V2.6-Flash | 231 | 369,600 | 420.8 | 646.0 | 1,396.5 | hybrid | 357.70 | 50.0% | link_latency |
| MiMo-V2.6-Flash | 347 | 555,200 | 420.8 | 645.8 | 1,403.5 | hybrid | 359.90 | 50.5% | link_latency |

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
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x34 | MiMo-V2.6-Flash | 34 | pipeline | rom_package_ucie | rom_board_serdes | 33 | 3.62 us | 27,587.3 tok/s | 275,873.2 tok/s | 17 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.20 us; 16 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 3.42 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x31 | MiMo-V2.6-Flash | 31 | tensor | rom_package_ucie | rom_board_serdes | 192 | 136.13 us | 734.6 tok/s | 7,346.1 tok/s | 96 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.39 us; 96 x all_reduce span 16 on rom_board_serdes (traversals 6.6) = 133.73 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x32 | MiMo-V2.6-Flash | 32 | hybrid | rom_package_ucie | rom_board_serdes | 111 | 5.60 us | 17,854.9 tok/s | 178,548.9 tok/s | 96 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.39 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 3.21 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x34 | MiMo-V2.6-Flash | 34 | pipeline | nvlink5 | infiniband_ndr | 33 | 43.84 us | 2,281.1 tok/s | 22,810.6 tok/s | 29 x point_to_point span 2 on nvlink5 (traversals 1.0) = 35.06 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | MiMo-V2.6-Flash | 1 | pipeline | on_wafer_n5 | rom_wafer_serdes | 47 | 5.88 us | 17,021.2 tok/s | 170,212.3 tok/s | 47 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.88 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-tensor-x30 | MiMo-V2.6-Flash | 30 | tensor | nvlink5 | infiniband_ndr | 192 | 657.84 us | 152.0 tok/s | 1,520.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | MiMo-V2.6-Flash | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 96 | 184.80 us | 541.1 tok/s | 5,411.3 tok/s | 96 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 184.80 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hybrid-x32 | MiMo-V2.6-Flash | 32 | hybrid | nvlink5 | infiniband_ndr | 99 | 239.28 us | 417.9 tok/s | 4,179.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x49 | MiMo-V2.6-Flash | 49 | pipeline | rom_package_ucie | rom_board_serdes | 47 | 5.21 us | 19,210.5 tok/s | 192,104.6 tok/s | 24 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.29 us; 23 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.92 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-tensor-x32 | MiMo-V2.6-Flash | 32 | tensor | rom_package_ucie | rom_board_serdes | 192 | 136.13 us | 734.6 tok/s | 7,346.1 tok/s | 96 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.39 us; 96 x all_reduce span 16 on rom_board_serdes (traversals 6.6) = 133.73 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x47 | MiMo-V2.6-Flash | 47 | hybrid | rom_package_ucie | rom_board_serdes | 119 | 7.31 us | 13,677.0 tok/s | 136,769.8 tok/s | 96 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 2.39 us; 23 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.92 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-pipeline-x49 | MiMo-V2.6-Flash | 49 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2 | MiMo-V2.6-Flash | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 47 | 5.88 us | 17,021.2 tok/s | 170,212.3 tok/s | 47 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.88 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-tensor-x32 | MiMo-V2.6-Flash | 32 | tensor | nvlink5 | infiniband_ndr | 192 | 657.84 us | 152.0 tok/s | 1,520.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-tensor-x2 | MiMo-V2.6-Flash | 2 | tensor | on_wafer_n5 | rom_wafer_serdes | 192 | 229.15 us | 436.4 tok/s | 4,364.0 tok/s | 96 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 184.80 us; 96 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 44.35 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hybrid-x40 | MiMo-V2.6-Flash | 40 | hybrid | nvlink5 | infiniband_ndr | 100 | 241.47 us | 414.1 tok/s | 4,141.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | MiMo-V2.6-Flash | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 97 | 185.01 us | 540.5 tok/s | 5,405.1 tok/s | 96 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 184.80 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.21 us |
| MiMo-V2.6-Flash/b200_sxm-x7-pipeline | MiMo-V2.6-Flash | 7 | pipeline | nvlink5 | infiniband_ndr | 6 | 7.25 us | 13,784.3 tok/s | 137,843.3 tok/s | 6 x point_to_point span 2 on nvlink5 (traversals 1.0) = 7.25 us |
| MiMo-V2.6-Flash/b200_sxm-x7-tensor | MiMo-V2.6-Flash | 7 | tensor | nvlink5 | infiniband_ndr | 96 | 232.65 us | 429.8 tok/s | 4,298.4 tok/s | 96 x all_reduce span 7 on nvlink5 (traversals 2.0) = 232.65 us |
| MiMo-V2.6-Flash/b200_sxm-x7-nvl72-tensor | MiMo-V2.6-Flash | 7 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.65 us | 429.8 tok/s | 4,298.4 tok/s | 96 x all_reduce span 7 on nvlink5_nvl72 (traversals 2.0) = 232.65 us |
| MiMo-V2.6-Flash/b200_sxm-x7-expert | MiMo-V2.6-Flash | 7 | expert | nvlink5 | infiniband_ndr | 192 | 348.85 us | 286.7 tok/s | 2,866.6 tok/s | 96 x all_reduce span 7 on nvlink5 (traversals 2.0) = 232.65 us; 96 x point_to_point span 2 on nvlink5 (traversals 1.0) = 116.20 us |
| MiMo-V2.6-Flash/b200_sxm-x7-nvl72-expert | MiMo-V2.6-Flash | 7 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.85 us | 286.7 tok/s | 2,866.6 tok/s | 96 x all_reduce span 7 on nvlink5_nvl72 (traversals 2.0) = 232.65 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 116.20 us |
| MiMo-V2.6-Flash/b200_sxm-x8-pipeline | MiMo-V2.6-Flash | 8 | pipeline | nvlink5 | infiniband_ndr | 7 | 8.46 us | 11,815.1 tok/s | 118,151.4 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.46 us |
| MiMo-V2.6-Flash/b200_sxm-x8-tensor | MiMo-V2.6-Flash | 8 | tensor | nvlink5 | infiniband_ndr | 96 | 232.69 us | 429.7 tok/s | 4,297.5 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us |
| MiMo-V2.6-Flash/b200_sxm-x8-nvl72-tensor | MiMo-V2.6-Flash | 8 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.69 us | 429.7 tok/s | 4,297.5 tok/s | 96 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 232.69 us |
| MiMo-V2.6-Flash/b200_sxm-x8-expert | MiMo-V2.6-Flash | 8 | expert | nvlink5 | infiniband_ndr | 192 | 348.77 us | 286.7 tok/s | 2,867.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x point_to_point span 2 on nvlink5 (traversals 1.0) = 116.07 us |
| MiMo-V2.6-Flash/b200_sxm-x8-nvl72-expert | MiMo-V2.6-Flash | 8 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.77 us | 286.7 tok/s | 2,867.2 tok/s | 96 x all_reduce span 8 on nvlink5_nvl72 (traversals 2.0) = 232.69 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 116.07 us |
| MiMo-V2.6-Flash/b200_sxm-x15-pipeline | MiMo-V2.6-Flash | 15 | pipeline | nvlink5 | infiniband_ndr | 14 | 17.91 us | 5,582.8 tok/s | 55,828.0 tok/s | 13 x point_to_point span 2 on nvlink5 (traversals 1.0) = 15.72 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x15-tensor | MiMo-V2.6-Flash | 15 | tensor | nvlink5 | infiniband_ndr | 192 | 646.05 us | 154.8 tok/s | 1,547.9 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 413.35 us |
| MiMo-V2.6-Flash/b200_sxm-x15-hybrid | MiMo-V2.6-Flash | 15 | hybrid | nvlink5 | infiniband_ndr | 97 | 234.89 us | 425.7 tok/s | 4,257.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x15-nvl72-tensor | MiMo-V2.6-Flash | 15 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.85 us | 429.5 tok/s | 4,294.7 tok/s | 96 x all_reduce span 15 on nvlink5_nvl72 (traversals 2.0) = 232.85 us |
| MiMo-V2.6-Flash/b200_sxm-x15-expert | MiMo-V2.6-Flash | 15 | expert | nvlink5 | infiniband_ndr | 192 | 435.96 us | 229.4 tok/s | 2,293.8 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 203.27 us |
| MiMo-V2.6-Flash/b200_sxm-x15-nvl72-expert | MiMo-V2.6-Flash | 15 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.51 us | 286.9 tok/s | 2,869.3 tok/s | 96 x all_reduce span 15 on nvlink5_nvl72 (traversals 2.0) = 232.85 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.67 us |
| MiMo-V2.6-Flash/b200_sxm-x16-pipeline | MiMo-V2.6-Flash | 16 | pipeline | nvlink5 | infiniband_ndr | 15 | 19.12 us | 5,229.8 tok/s | 52,297.8 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x16-tensor | MiMo-V2.6-Flash | 16 | tensor | nvlink5 | infiniband_ndr | 192 | 646.05 us | 154.8 tok/s | 1,547.9 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 413.35 us |
| MiMo-V2.6-Flash/b200_sxm-x16-hybrid | MiMo-V2.6-Flash | 16 | hybrid | nvlink5 | infiniband_ndr | 97 | 234.89 us | 425.7 tok/s | 4,257.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x16-nvl72-tensor | MiMo-V2.6-Flash | 16 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.86 us | 429.4 tok/s | 4,294.5 tok/s | 96 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 232.86 us |
| MiMo-V2.6-Flash/b200_sxm-x16-expert | MiMo-V2.6-Flash | 16 | expert | nvlink5 | infiniband_ndr | 192 | 434.29 us | 230.3 tok/s | 2,302.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 202.74 us |
| MiMo-V2.6-Flash/b200_sxm-x16-nvl72-expert | MiMo-V2.6-Flash | 16 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.49 us | 286.9 tok/s | 2,869.5 tok/s | 96 x all_reduce span 16 on nvlink5_nvl72 (traversals 2.0) = 232.86 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.64 us |
| MiMo-V2.6-Flash/b200_sxm-x17-pipeline | MiMo-V2.6-Flash | 17 | pipeline | nvlink5 | infiniband_ndr | 16 | 21.32 us | 4,691.5 tok/s | 46,915.1 tok/s | 14 x point_to_point span 2 on nvlink5 (traversals 1.0) = 16.93 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x17-tensor | MiMo-V2.6-Flash | 17 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x17-hybrid | MiMo-V2.6-Flash | 17 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x17-nvl72-tensor | MiMo-V2.6-Flash | 17 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.87 us | 429.4 tok/s | 4,294.3 tok/s | 96 x all_reduce span 17 on nvlink5_nvl72 (traversals 2.0) = 232.87 us |
| MiMo-V2.6-Flash/b200_sxm-x17-expert | MiMo-V2.6-Flash | 17 | expert | nvlink5 | infiniband_ndr | 192 | 433.83 us | 230.5 tok/s | 2,305.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 202.28 us |
| MiMo-V2.6-Flash/b200_sxm-x17-nvl72-expert | MiMo-V2.6-Flash | 17 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.48 us | 287.0 tok/s | 2,869.6 tok/s | 96 x all_reduce span 17 on nvlink5_nvl72 (traversals 2.0) = 232.87 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.61 us |
| MiMo-V2.6-Flash/b200_sxm-x18-pipeline | MiMo-V2.6-Flash | 18 | pipeline | nvlink5 | infiniband_ndr | 17 | 22.52 us | 4,439.7 tok/s | 44,396.7 tok/s | 15 x point_to_point span 2 on nvlink5 (traversals 1.0) = 18.14 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x18-tensor | MiMo-V2.6-Flash | 18 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x18-hybrid | MiMo-V2.6-Flash | 18 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x18-nvl72-tensor | MiMo-V2.6-Flash | 18 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.88 us | 429.4 tok/s | 4,294.1 tok/s | 96 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 232.88 us |
| MiMo-V2.6-Flash/b200_sxm-x18-expert | MiMo-V2.6-Flash | 18 | expert | nvlink5 | infiniband_ndr | 192 | 433.42 us | 230.7 tok/s | 2,307.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 201.87 us |
| MiMo-V2.6-Flash/b200_sxm-x18-nvl72-expert | MiMo-V2.6-Flash | 18 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.46 us | 287.0 tok/s | 2,869.7 tok/s | 96 x all_reduce span 18 on nvlink5_nvl72 (traversals 2.0) = 232.88 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.59 us |
| MiMo-V2.6-Flash/b200_sxm-x19-pipeline | MiMo-V2.6-Flash | 19 | pipeline | nvlink5 | infiniband_ndr | 18 | 23.73 us | 4,213.5 tok/s | 42,134.9 tok/s | 16 x point_to_point span 2 on nvlink5 (traversals 1.0) = 19.35 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x19-tensor | MiMo-V2.6-Flash | 19 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x19-hybrid | MiMo-V2.6-Flash | 19 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x19-nvl72-tensor | MiMo-V2.6-Flash | 19 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.88 us | 429.4 tok/s | 4,294.0 tok/s | 96 x all_reduce span 19 on nvlink5_nvl72 (traversals 2.0) = 232.88 us |
| MiMo-V2.6-Flash/b200_sxm-x19-expert | MiMo-V2.6-Flash | 19 | expert | nvlink5 | infiniband_ndr | 192 | 433.05 us | 230.9 tok/s | 2,309.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 201.50 us |
| MiMo-V2.6-Flash/b200_sxm-x19-nvl72-expert | MiMo-V2.6-Flash | 19 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.45 us | 287.0 tok/s | 2,869.8 tok/s | 96 x all_reduce span 19 on nvlink5_nvl72 (traversals 2.0) = 232.88 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.57 us |
| MiMo-V2.6-Flash/b200_sxm-x20-pipeline | MiMo-V2.6-Flash | 20 | pipeline | nvlink5 | infiniband_ndr | 19 | 24.94 us | 4,009.2 tok/s | 40,092.3 tok/s | 17 x point_to_point span 2 on nvlink5 (traversals 1.0) = 20.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x20-tensor | MiMo-V2.6-Flash | 20 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x20-hybrid | MiMo-V2.6-Flash | 20 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x20-nvl72-tensor | MiMo-V2.6-Flash | 20 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.89 us | 429.4 tok/s | 4,293.9 tok/s | 96 x all_reduce span 20 on nvlink5_nvl72 (traversals 2.0) = 232.89 us |
| MiMo-V2.6-Flash/b200_sxm-x20-expert | MiMo-V2.6-Flash | 20 | expert | nvlink5 | infiniband_ndr | 192 | 432.72 us | 231.1 tok/s | 2,311.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 201.17 us |
| MiMo-V2.6-Flash/b200_sxm-x20-nvl72-expert | MiMo-V2.6-Flash | 20 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.44 us | 287.0 tok/s | 2,869.9 tok/s | 96 x all_reduce span 20 on nvlink5_nvl72 (traversals 2.0) = 232.89 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.55 us |
| MiMo-V2.6-Flash/b200_sxm-x21-pipeline | MiMo-V2.6-Flash | 21 | pipeline | nvlink5 | infiniband_ndr | 20 | 26.15 us | 3,823.9 tok/s | 38,238.7 tok/s | 18 x point_to_point span 2 on nvlink5 (traversals 1.0) = 21.76 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x21-tensor | MiMo-V2.6-Flash | 21 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x21-hybrid | MiMo-V2.6-Flash | 21 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x21-nvl72-tensor | MiMo-V2.6-Flash | 21 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.90 us | 429.4 tok/s | 4,293.8 tok/s | 96 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 232.90 us |
| MiMo-V2.6-Flash/b200_sxm-x21-expert | MiMo-V2.6-Flash | 21 | expert | nvlink5 | infiniband_ndr | 192 | 432.42 us | 231.3 tok/s | 2,312.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 200.87 us |
| MiMo-V2.6-Flash/b200_sxm-x21-nvl72-expert | MiMo-V2.6-Flash | 21 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.43 us | 287.0 tok/s | 2,870.0 tok/s | 96 x all_reduce span 21 on nvlink5_nvl72 (traversals 2.0) = 232.90 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.53 us |
| MiMo-V2.6-Flash/b200_sxm-x23-pipeline | MiMo-V2.6-Flash | 23 | pipeline | nvlink5 | infiniband_ndr | 22 | 28.57 us | 3,500.2 tok/s | 35,002.1 tok/s | 20 x point_to_point span 2 on nvlink5 (traversals 1.0) = 24.18 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x23-tensor | MiMo-V2.6-Flash | 23 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x23-hybrid | MiMo-V2.6-Flash | 23 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x23-nvl72-tensor | MiMo-V2.6-Flash | 23 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.91 us | 429.4 tok/s | 4,293.6 tok/s | 96 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 232.91 us |
| MiMo-V2.6-Flash/b200_sxm-x23-expert | MiMo-V2.6-Flash | 23 | expert | nvlink5 | infiniband_ndr | 192 | 431.90 us | 231.5 tok/s | 2,315.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 200.35 us |
| MiMo-V2.6-Flash/b200_sxm-x23-nvl72-expert | MiMo-V2.6-Flash | 23 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.41 us | 287.0 tok/s | 2,870.2 tok/s | 96 x all_reduce span 23 on nvlink5_nvl72 (traversals 2.0) = 232.91 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.50 us |
| MiMo-V2.6-Flash/b200_sxm-x24-pipeline | MiMo-V2.6-Flash | 24 | pipeline | nvlink5 | infiniband_ndr | 23 | 29.78 us | 3,358.1 tok/s | 33,580.9 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x24-tensor | MiMo-V2.6-Flash | 24 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x24-hybrid | MiMo-V2.6-Flash | 24 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x24-nvl72-tensor | MiMo-V2.6-Flash | 24 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.91 us | 429.3 tok/s | 4,293.5 tok/s | 96 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 232.91 us |
| MiMo-V2.6-Flash/b200_sxm-x24-expert | MiMo-V2.6-Flash | 24 | expert | nvlink5 | infiniband_ndr | 192 | 431.29 us | 231.9 tok/s | 2,318.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.16 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 200.12 us |
| MiMo-V2.6-Flash/b200_sxm-x24-nvl72-expert | MiMo-V2.6-Flash | 24 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.40 us | 287.0 tok/s | 2,870.2 tok/s | 96 x all_reduce span 24 on nvlink5_nvl72 (traversals 2.0) = 232.91 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.49 us |
| MiMo-V2.6-Flash/b200_sxm-x25-pipeline | MiMo-V2.6-Flash | 25 | pipeline | nvlink5 | infiniband_ndr | 24 | 31.97 us | 3,127.7 tok/s | 31,276.7 tok/s | 21 x point_to_point span 2 on nvlink5 (traversals 1.0) = 25.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x25-tensor | MiMo-V2.6-Flash | 25 | tensor | nvlink5 | infiniband_ndr | 192 | 657.84 us | 152.0 tok/s | 1,520.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/b200_sxm-x25-hybrid | MiMo-V2.6-Flash | 25 | hybrid | nvlink5 | infiniband_ndr | 99 | 239.28 us | 417.9 tok/s | 4,179.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x25-nvl72-tensor | MiMo-V2.6-Flash | 25 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.92 us | 429.3 tok/s | 4,293.4 tok/s | 96 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 232.92 us |
| MiMo-V2.6-Flash/b200_sxm-x25-expert | MiMo-V2.6-Flash | 25 | expert | nvlink5 | infiniband_ndr | 192 | 431.08 us | 232.0 tok/s | 2,319.8 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.16 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 199.91 us |
| MiMo-V2.6-Flash/b200_sxm-x25-nvl72-expert | MiMo-V2.6-Flash | 25 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.40 us | 287.0 tok/s | 2,870.3 tok/s | 96 x all_reduce span 25 on nvlink5_nvl72 (traversals 2.0) = 232.92 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.48 us |
| MiMo-V2.6-Flash/b200_sxm-x29-pipeline | MiMo-V2.6-Flash | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x29-tensor | MiMo-V2.6-Flash | 29 | tensor | nvlink5 | infiniband_ndr | 192 | 657.84 us | 152.0 tok/s | 1,520.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/b200_sxm-x29-hybrid | MiMo-V2.6-Flash | 29 | hybrid | nvlink5 | infiniband_ndr | 99 | 239.28 us | 417.9 tok/s | 4,179.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x29-nvl72-tensor | MiMo-V2.6-Flash | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.93 us | 429.3 tok/s | 4,293.1 tok/s | 96 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 232.93 us |
| MiMo-V2.6-Flash/b200_sxm-x29-expert | MiMo-V2.6-Flash | 29 | expert | nvlink5 | infiniband_ndr | 192 | 430.38 us | 232.4 tok/s | 2,323.5 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.16 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 199.22 us |
| MiMo-V2.6-Flash/b200_sxm-x29-nvl72-expert | MiMo-V2.6-Flash | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.37 us | 287.0 tok/s | 2,870.5 tok/s | 96 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 232.93 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.44 us |
| MiMo-V2.6-Flash/b200_sxm-x31-pipeline | MiMo-V2.6-Flash | 31 | pipeline | nvlink5 | infiniband_ndr | 30 | 39.23 us | 2,549.2 tok/s | 25,492.5 tok/s | 27 x point_to_point span 2 on nvlink5 (traversals 1.0) = 32.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x31-tensor | MiMo-V2.6-Flash | 31 | tensor | nvlink5 | infiniband_ndr | 192 | 657.84 us | 152.0 tok/s | 1,520.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/b200_sxm-x31-hybrid | MiMo-V2.6-Flash | 31 | hybrid | nvlink5 | infiniband_ndr | 99 | 239.28 us | 417.9 tok/s | 4,179.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x31-nvl72-tensor | MiMo-V2.6-Flash | 31 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.94 us | 429.3 tok/s | 4,293.0 tok/s | 96 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 232.94 us |
| MiMo-V2.6-Flash/b200_sxm-x31-expert | MiMo-V2.6-Flash | 31 | expert | nvlink5 | infiniband_ndr | 192 | 430.10 us | 232.5 tok/s | 2,325.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.16 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 198.94 us |
| MiMo-V2.6-Flash/b200_sxm-x31-nvl72-expert | MiMo-V2.6-Flash | 31 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.36 us | 287.1 tok/s | 2,870.6 tok/s | 96 x all_reduce span 31 on nvlink5_nvl72 (traversals 2.0) = 232.94 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.43 us |
| MiMo-V2.6-Flash/b200_sxm-x43-pipeline | MiMo-V2.6-Flash | 43 | pipeline | nvlink5 | infiniband_ndr | 42 | 55.71 us | 1,795.1 tok/s | 17,951.4 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x43-tensor | MiMo-V2.6-Flash | 43 | tensor | nvlink5 | infiniband_ndr | 192 | 661.78 us | 151.1 tok/s | 1,511.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 429.08 us |
| MiMo-V2.6-Flash/b200_sxm-x43-hybrid | MiMo-V2.6-Flash | 43 | hybrid | nvlink5 | infiniband_ndr | 101 | 243.66 us | 410.4 tok/s | 4,104.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x43-nvl72-tensor | MiMo-V2.6-Flash | 43 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.96 us | 429.3 tok/s | 4,292.6 tok/s | 96 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 232.96 us |
| MiMo-V2.6-Flash/b200_sxm-x43-expert | MiMo-V2.6-Flash | 43 | expert | nvlink5 | infiniband_ndr | 192 | 428.67 us | 233.3 tok/s | 2,332.8 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.86 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 197.81 us |
| MiMo-V2.6-Flash/b200_sxm-x43-nvl72-expert | MiMo-V2.6-Flash | 43 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.32 us | 287.1 tok/s | 2,870.9 tok/s | 96 x all_reduce span 43 on nvlink5_nvl72 (traversals 2.0) = 232.96 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.36 us |
| MiMo-V2.6-Flash/b200_sxm-x46-pipeline | MiMo-V2.6-Flash | 46 | pipeline | nvlink5 | infiniband_ndr | 45 | 59.33 us | 1,685.4 tok/s | 16,853.9 tok/s | 40 x point_to_point span 2 on nvlink5 (traversals 1.0) = 48.36 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x46-tensor | MiMo-V2.6-Flash | 46 | tensor | nvlink5 | infiniband_ndr | 192 | 661.78 us | 151.1 tok/s | 1,511.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 429.08 us |
| MiMo-V2.6-Flash/b200_sxm-x46-hybrid | MiMo-V2.6-Flash | 46 | hybrid | nvlink5 | infiniband_ndr | 101 | 243.66 us | 410.4 tok/s | 4,104.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x46-nvl72-tensor | MiMo-V2.6-Flash | 46 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.96 us | 429.3 tok/s | 4,292.5 tok/s | 96 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 232.96 us |
| MiMo-V2.6-Flash/b200_sxm-x46-expert | MiMo-V2.6-Flash | 46 | expert | nvlink5 | infiniband_ndr | 192 | 428.47 us | 233.4 tok/s | 2,333.9 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.86 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 197.62 us |
| MiMo-V2.6-Flash/b200_sxm-x46-nvl72-expert | MiMo-V2.6-Flash | 46 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.32 us | 287.1 tok/s | 2,871.0 tok/s | 96 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 232.96 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.35 us |
| MiMo-V2.6-Flash/b200_sxm-x57-pipeline | MiMo-V2.6-Flash | 57 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x57-tensor | MiMo-V2.6-Flash | 57 | tensor | nvlink5 | infiniband_ndr | 192 | 663.74 us | 150.7 tok/s | 1,506.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 431.05 us |
| MiMo-V2.6-Flash/b200_sxm-x57-hybrid | MiMo-V2.6-Flash | 57 | hybrid | nvlink5 | infiniband_ndr | 103 | 248.05 us | 403.1 tok/s | 4,031.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| MiMo-V2.6-Flash/b200_sxm-x57-nvl72-tensor | MiMo-V2.6-Flash | 57 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.98 us | 429.2 tok/s | 4,292.3 tok/s | 96 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 232.98 us |
| MiMo-V2.6-Flash/b200_sxm-x57-expert | MiMo-V2.6-Flash | 57 | expert | nvlink5 | infiniband_ndr | 192 | 427.82 us | 233.7 tok/s | 2,337.5 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.73 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 197.09 us |
| MiMo-V2.6-Flash/b200_sxm-x57-nvl72-expert | MiMo-V2.6-Flash | 57 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.30 us | 287.1 tok/s | 2,871.1 tok/s | 96 x all_reduce span 57 on nvlink5_nvl72 (traversals 2.0) = 232.98 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.32 us |
| MiMo-V2.6-Flash/b200_sxm-x58-pipeline | MiMo-V2.6-Flash | 58 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x58-tensor | MiMo-V2.6-Flash | 58 | tensor | nvlink5 | infiniband_ndr | 192 | 663.74 us | 150.7 tok/s | 1,506.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 431.05 us |
| MiMo-V2.6-Flash/b200_sxm-x58-hybrid | MiMo-V2.6-Flash | 58 | hybrid | nvlink5 | infiniband_ndr | 103 | 248.05 us | 403.1 tok/s | 4,031.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| MiMo-V2.6-Flash/b200_sxm-x58-nvl72-tensor | MiMo-V2.6-Flash | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.98 us | 429.2 tok/s | 4,292.3 tok/s | 96 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 232.98 us |
| MiMo-V2.6-Flash/b200_sxm-x58-expert | MiMo-V2.6-Flash | 58 | expert | nvlink5 | infiniband_ndr | 192 | 427.78 us | 233.8 tok/s | 2,337.7 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.73 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 197.05 us |
| MiMo-V2.6-Flash/b200_sxm-x58-nvl72-expert | MiMo-V2.6-Flash | 58 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.30 us | 287.1 tok/s | 2,871.1 tok/s | 96 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 232.98 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.32 us |
| MiMo-V2.6-Flash/b200_sxm-x61-pipeline | MiMo-V2.6-Flash | 61 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x61-tensor | MiMo-V2.6-Flash | 61 | tensor | nvlink5 | infiniband_ndr | 192 | 663.74 us | 150.7 tok/s | 1,506.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 431.05 us |
| MiMo-V2.6-Flash/b200_sxm-x61-hybrid | MiMo-V2.6-Flash | 61 | hybrid | nvlink5 | infiniband_ndr | 103 | 248.05 us | 403.1 tok/s | 4,031.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| MiMo-V2.6-Flash/b200_sxm-x61-nvl72-tensor | MiMo-V2.6-Flash | 61 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.98 us | 429.2 tok/s | 4,292.2 tok/s | 96 x all_reduce span 61 on nvlink5_nvl72 (traversals 2.0) = 232.98 us |
| MiMo-V2.6-Flash/b200_sxm-x61-expert | MiMo-V2.6-Flash | 61 | expert | nvlink5 | infiniband_ndr | 192 | 427.67 us | 233.8 tok/s | 2,338.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.73 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 196.94 us |
| MiMo-V2.6-Flash/b200_sxm-x61-nvl72-expert | MiMo-V2.6-Flash | 61 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.29 us | 287.1 tok/s | 2,871.1 tok/s | 96 x all_reduce span 61 on nvlink5_nvl72 (traversals 2.0) = 232.98 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.31 us |
| MiMo-V2.6-Flash/b200_sxm-x87-pipeline | MiMo-V2.6-Flash | 87 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x87-tensor | MiMo-V2.6-Flash | 87 | tensor | nvlink5 | infiniband_ndr | 192 | 665.35 us | 150.3 tok/s | 1,503.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 432.66 us |
| MiMo-V2.6-Flash/b200_sxm-x87-hybrid | MiMo-V2.6-Flash | 87 | hybrid | nvlink5 | infiniband_ndr | 106 | 254.63 us | 392.7 tok/s | 3,927.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| MiMo-V2.6-Flash/b200_sxm-x87-nvl72-tensor | MiMo-V2.6-Flash | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 646.34 us | 154.7 tok/s | 1,547.2 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 413.35 us |
| MiMo-V2.6-Flash/b200_sxm-x87-nvl72-hybrid | MiMo-V2.6-Flash | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 97 | 235.18 us | 425.2 tok/s | 4,252.1 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x87-expert | MiMo-V2.6-Flash | 87 | expert | nvlink5 | infiniband_ndr | 192 | 426.96 us | 234.2 tok/s | 2,342.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.63 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 196.33 us |
| MiMo-V2.6-Flash/b200_sxm-x87-nvl72-expert | MiMo-V2.6-Flash | 87 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 429.31 us | 232.9 tok/s | 2,329.3 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 196.33 us |
| MiMo-V2.6-Flash/b200_sxm-x116-pipeline | MiMo-V2.6-Flash | 116 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x116-tensor | MiMo-V2.6-Flash | 116 | tensor | nvlink5 | infiniband_ndr | 192 | 666.49 us | 150.0 tok/s | 1,500.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 433.80 us |
| MiMo-V2.6-Flash/b200_sxm-x116-hybrid | MiMo-V2.6-Flash | 116 | hybrid | nvlink5 | infiniband_ndr | 110 | 263.41 us | 379.6 tok/s | 3,796.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| MiMo-V2.6-Flash/b200_sxm-x116-nvl72-tensor | MiMo-V2.6-Flash | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 646.34 us | 154.7 tok/s | 1,547.2 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 413.35 us |
| MiMo-V2.6-Flash/b200_sxm-x116-nvl72-hybrid | MiMo-V2.6-Flash | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 97 | 235.18 us | 425.2 tok/s | 4,252.1 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x116-expert | MiMo-V2.6-Flash | 116 | expert | nvlink5 | infiniband_ndr | 192 | 426.53 us | 234.5 tok/s | 2,344.5 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.56 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.96 us |
| MiMo-V2.6-Flash/b200_sxm-x116-nvl72-expert | MiMo-V2.6-Flash | 116 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 428.95 us | 233.1 tok/s | 2,331.3 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.96 us |
| MiMo-V2.6-Flash/b200_sxm-x173-pipeline | MiMo-V2.6-Flash | 173 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x173-tensor | MiMo-V2.6-Flash | 173 | tensor | nvlink5 | infiniband_ndr | 192 | 667.49 us | 149.8 tok/s | 1,498.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 434.80 us |
| MiMo-V2.6-Flash/b200_sxm-x173-hybrid | MiMo-V2.6-Flash | 173 | hybrid | nvlink5 | infiniband_ndr | 117 | 278.76 us | 358.7 tok/s | 3,587.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| MiMo-V2.6-Flash/b200_sxm-x173-nvl72-tensor | MiMo-V2.6-Flash | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 654.20 us | 152.9 tok/s | 1,528.6 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x173-nvl72-hybrid | MiMo-V2.6-Flash | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 98 | 237.37 us | 421.3 tok/s | 4,212.8 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x173-expert | MiMo-V2.6-Flash | 173 | expert | nvlink5 | infiniband_ndr | 192 | 426.12 us | 234.7 tok/s | 2,346.8 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.51 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.61 us |
| MiMo-V2.6-Flash/b200_sxm-x173-nvl72-expert | MiMo-V2.6-Flash | 173 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 427.30 us | 234.0 tok/s | 2,340.3 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 231.69 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.61 us |
| MiMo-V2.6-Flash/b200_sxm-x231-pipeline | MiMo-V2.6-Flash | 231 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x231-tensor | MiMo-V2.6-Flash | 231 | tensor | nvlink5 | infiniband_ndr | 192 | 668.01 us | 149.7 tok/s | 1,497.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 435.32 us |
| MiMo-V2.6-Flash/b200_sxm-x231-hybrid | MiMo-V2.6-Flash | 231 | hybrid | nvlink5 | infiniband_ndr | 124 | 294.12 us | 340.0 tok/s | 3,400.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 61.43 us |
| MiMo-V2.6-Flash/b200_sxm-x231-nvl72-tensor | MiMo-V2.6-Flash | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 658.13 us | 151.9 tok/s | 1,519.4 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/b200_sxm-x231-nvl72-hybrid | MiMo-V2.6-Flash | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 99 | 239.57 us | 417.4 tok/s | 4,174.2 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x231-expert | MiMo-V2.6-Flash | 231 | expert | nvlink5 | infiniband_ndr | 192 | 425.91 us | 234.8 tok/s | 2,347.9 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.48 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.42 us |
| MiMo-V2.6-Flash/b200_sxm-x231-nvl72-expert | MiMo-V2.6-Flash | 231 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 426.69 us | 234.4 tok/s | 2,343.6 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 231.26 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.42 us |
| MiMo-V2.6-Flash/b200_sxm-x347-pipeline | MiMo-V2.6-Flash | 347 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x347-tensor | MiMo-V2.6-Flash | 347 | tensor | nvlink5 | infiniband_ndr | 192 | 668.57 us | 149.6 tok/s | 1,495.7 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 435.87 us |
| MiMo-V2.6-Flash/b200_sxm-x347-hybrid | MiMo-V2.6-Flash | 347 | hybrid | nvlink5 | infiniband_ndr | 139 | 327.03 us | 305.8 tok/s | 3,057.8 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 94.34 us |
| MiMo-V2.6-Flash/b200_sxm-x347-nvl72-tensor | MiMo-V2.6-Flash | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 660.49 us | 151.4 tok/s | 1,514.0 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 427.51 us |
| MiMo-V2.6-Flash/b200_sxm-x347-nvl72-hybrid | MiMo-V2.6-Flash | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 100 | 241.76 us | 413.6 tok/s | 4,136.3 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| MiMo-V2.6-Flash/b200_sxm-x347-expert | MiMo-V2.6-Flash | 347 | expert | nvlink5 | infiniband_ndr | 192 | 425.70 us | 234.9 tok/s | 2,349.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.45 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.24 us |
| MiMo-V2.6-Flash/b200_sxm-x347-nvl72-expert | MiMo-V2.6-Flash | 347 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 426.29 us | 234.6 tok/s | 2,345.8 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 231.05 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.24 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Flash | 1 | wafer | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 6,512.3 | 0.070 | 5,636.6 (38,305) | 6,512.3 (92,450) | 1.16x | layer_fixed_latency |
| MiMo-V2.6-Flash | 2 | wafer | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 6,512.3 | 0.070 | 5,636.6 (38,305) | 6,512.3 (92,450) | 1.16x | layer_fixed_latency |
| MiMo-V2.6-Flash | 4 | wafer | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 6,512.3 | 0.070 | 5,636.6 (38,305) | 6,512.3 (92,450) | 1.16x | layer_fixed_latency |
| MiMo-V2.6-Flash | 8 | wafer | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 6,512.3 | 0.070 | 5,636.6 (38,305) | 6,512.3 (92,450) | 1.16x | layer_fixed_latency |
| MiMo-V2.6-Flash | 16 | wafer | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 6,089.0 | 0.044 | 5,445.0 (39,935) | 6,089.0 (138,675) | 1.12x | layer_fixed_latency |
| MiMo-V2.6-Flash | 32 | wafer | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 6,058.1 | 0.022 | 5,225.9 (46,455) | 6,058.1 (277,350) | 1.16x | layer_fixed_latency |
| MiMo-V2.6-Flash | 64 | wafer | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 6,047.0 | 0.011 | 5,323.1 (138,550) | 6,047.0 (554,700) | 1.14x | layer_fixed_latency |
| MiMo-V2.6-Flash | 256 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 4,472.1 | 0.016 | 4,472.1 (277,100) | 4,122.1 (554,700) | 0.92x | layer_fixed_latency |
| MiMo-V2.6-Flash | 1024 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 1,830.9 | 0.007 | 1,830.9 (277,100) | 1,614.2 (554,700) | 0.88x | compute |
| MiMo-V2.6-Flash | 4096 | array | array | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 525.0 | 0.002 | 525.0 (277,100) | 452.3 (554,700) | 0.86x | compute |

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
| MiMo-V2.6-Flash | 256 | 628.4 MB | 107.2 mm2 | 19.29 mm2 (18.0%) | 27,440 mm2 | 4,939 mm2 | 29,498 mm2 = 36.2 reticles |

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
| MiMo-V2.6-Flash | 1 | sram | 340,496.7 | 27,662.2 | 27,662.2 | 12.31x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 2 | sram | 340,496.7 | 27,662.2 | 27,662.2 | 12.31x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 4 | sram | 340,496.7 | 27,662.2 | 27,662.2 | 12.31x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 8 | sram | 340,496.7 | 27,662.2 | 27,662.2 | 12.31x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 16 | sram | 340,496.7 | 27,662.2 | 43,452.3 | 12.31x | 1.57x | weight_read | weight_read | layer_fixed_latency |
| MiMo-V2.6-Flash | 32 | sram | 340,496.7 | 27,662.2 | 64,014.5 | 12.31x | 2.31x | weight_read | weight_read | layer_fixed_latency |
| MiMo-V2.6-Flash | 64 | sram | 340,496.7 | 27,802.8 | 92,898.6 | 12.25x | 3.34x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 256 | sram | 564,424.9 | 28,695.6 | 158,805.5 | 19.67x | 5.53x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 1024 | sram | 942,107.0 | 26,050.6 | 255,683.2 | 36.16x | 9.81x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 4096 | sram | 1,526,992.2 | 26,094.7 | 311,952.5 | 58.52x | 11.95x | weight_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 1 | rom | 1,545,640.1 | 177,750.7 | 177,750.7 | 8.70x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 2 | rom | 1,545,640.1 | 177,750.7 | 177,750.7 | 8.70x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 4 | rom | 1,545,640.1 | 177,750.7 | 177,750.7 | 8.70x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 8 | rom | 1,545,640.1 | 177,750.7 | 177,750.7 | 8.70x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 16 | rom | 1,545,640.1 | 177,750.7 | 177,750.7 | 8.70x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 32 | rom | 1,545,640.1 | 177,750.7 | 177,750.7 | 8.70x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 64 | rom | 1,545,640.1 | 177,750.7 | 208,140.8 | 8.70x | 1.17x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 256 | rom | 1,545,640.1 | 192,270.1 | 289,738.1 | 8.04x | 1.51x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 1024 | rom | 1,874,867.2 | 202,619.9 | 313,635.2 | 9.25x | 1.55x | compute | weight_read | kv_read |
| MiMo-V2.6-Flash | 4096 | rom | 2,150,317.9 | 205,321.0 | 319,787.2 | 10.47x | 1.56x | compute | weight_read | kv_read |

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
| MiMo-V2.6-Flash | 1 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 1 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.12 | 1.00 | 1,545,640.1 | 2.786 | kv_read | 4.54x |
| MiMo-V2.6-Flash | 1 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,662.2 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 1 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 1 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,662.2 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 1 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 2 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 2 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.12 | 1.00 | 1,545,640.1 | 2.786 | kv_read | 4.54x |
| MiMo-V2.6-Flash | 2 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,662.2 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 2 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 2 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,662.2 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 2 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 4 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 4 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.12 | 1.00 | 1,545,640.1 | 2.786 | kv_read | 4.54x |
| MiMo-V2.6-Flash | 4 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,662.2 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 4 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 4 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,662.2 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 4 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 8 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 8 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.12 | 1.00 | 1,545,640.1 | 2.786 | kv_read | 4.54x |
| MiMo-V2.6-Flash | 8 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,662.2 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 8 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 8 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 27,662.2 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 8 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 16 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 16 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.12 | 1.00 | 1,545,640.1 | 2.786 | kv_read | 4.54x |
| MiMo-V2.6-Flash | 16 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,662.2 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 16 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 16 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.34 | 43,452.3 | 0.470 | layer_fixed_latency | 0.13x |
| MiMo-V2.6-Flash | 16 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 32 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 32 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.12 | 1.00 | 1,545,640.1 | 2.786 | kv_read | 4.54x |
| MiMo-V2.6-Flash | 32 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 27,662.2 | 0.598 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 32 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 32 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 3.27 | 64,014.5 | 0.692 | layer_fixed_latency | 0.19x |
| MiMo-V2.6-Flash | 32 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 64 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 340,496.7 | 0.614 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 64 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.12 | 1.00 | 1,545,640.1 | 2.786 | kv_read | 4.54x |
| MiMo-V2.6-Flash | 64 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 27,802.8 | 0.601 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 64 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 1.00 | 177,750.7 | 1.923 | weight_read | 0.52x |
| MiMo-V2.6-Flash | 64 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 3.27 | 92,898.6 | 1.005 | weight_read | 0.27x |
| MiMo-V2.6-Flash | 64 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 7.91 | 1.28 | 208,140.8 | 2.251 | kv_read | 0.61x |
| MiMo-V2.6-Flash | 256 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 564,424.9 | 1.526 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 256 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 14.12 | 1.00 | 1,545,640.1 | 2.786 | kv_read | 2.74x |
| MiMo-V2.6-Flash | 256 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,695.6 | 0.621 | weight_read | 0.05x |
| MiMo-V2.6-Flash | 256 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 2.25 | 192,270.1 | 2.080 | weight_read | 0.34x |
| MiMo-V2.6-Flash | 256 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 6.85 | 158,805.5 | 1.718 | weight_read | 0.28x |
| MiMo-V2.6-Flash | 256 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 1.30 | 289,738.1 | 3.134 | kv_read | 0.51x |
| MiMo-V2.6-Flash | 1024 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 942,107.0 | 1.698 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 1024 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.60 | 1.00 | 1,874,867.2 | 6.766 | compute | 1.99x |
| MiMo-V2.6-Flash | 1024 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 8.98 | 26,050.6 | 0.282 | weight_read | 0.03x |
| MiMo-V2.6-Flash | 1024 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 8.98 | 202,619.9 | 2.192 | weight_read | 0.22x |
| MiMo-V2.6-Flash | 1024 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 10.52 | 255,683.2 | 2.766 | weight_read | 0.27x |
| MiMo-V2.6-Flash | 1024 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 2.46 | 313,635.2 | 3.392 | kv_read | 0.33x |
| MiMo-V2.6-Flash | 4096 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 1.00 | 1.00 | 1,526,992.2 | 8.254 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 4096 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 6.60 | 1.00 | 2,150,317.9 | 7.760 | compute | 1.41x |
| MiMo-V2.6-Flash | 4096 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 35.93 | 26,094.7 | 0.282 | weight_read | 0.02x |
| MiMo-V2.6-Flash | 4096 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 7.91 | 35.93 | 205,321.0 | 2.221 | weight_read | 0.13x |
| MiMo-V2.6-Flash | 4096 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 11.22 | 311,952.5 | 3.374 | kv_read | 0.20x |
| MiMo-V2.6-Flash | 4096 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 7.91 | 4.94 | 319,787.2 | 3.459 | kv_read | 0.21x |

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
| MiMo-V2.6-Flash | 1 | 15 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 2 | 15 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 4 | 15 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 8 | 15 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 64 | 57 | 1.12 | 1.002 | 1.027 | 1.02x |
| MiMo-V2.6-Flash | 256 | 57 | 4.49 | 1.056 | 1.885 | 1.78x |
| MiMo-V2.6-Flash | 1024 | 16 | 64.00 | 2.302 | 6.846 | 2.97x |
| MiMo-V2.6-Flash | 4096 | 16 | 256.00 | 8.002 | 16.866 | 2.11x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Flash | 1 | 7 | 4.96 | 3.12 | 1.59x |
| MiMo-V2.6-Flash | 2 | 7 | 6.38 | 3.73 | 1.71x |
| MiMo-V2.6-Flash | 4 | 7 | 6.94 | 4.31 | 1.61x |
| MiMo-V2.6-Flash | 8 | 7 | 7.00 | 4.82 | 1.45x |
| MiMo-V2.6-Flash | 16 | 7 | 7.00 | 5.24 | 1.34x |
| MiMo-V2.6-Flash | 32 | 7 | 7.00 | 5.53 | 1.26x |
| MiMo-V2.6-Flash | 64 | 7 | 7.00 | 5.71 | 1.23x |
| MiMo-V2.6-Flash | 256 | 7 | 7.00 | 5.78 | 1.21x |
| MiMo-V2.6-Flash | 1024 | 7 | 7.00 | 5.78 | 1.21x |
| MiMo-V2.6-Flash | 4096 | 7 | 7.00 | 5.78 | 1.21x |
| MiMo-V2.6-Flash | 1 | 8 | 5.25 | 3.28 | 1.60x |
| MiMo-V2.6-Flash | 2 | 8 | 7.02 | 3.98 | 1.77x |
| MiMo-V2.6-Flash | 4 | 8 | 7.86 | 4.66 | 1.69x |
| MiMo-V2.6-Flash | 8 | 8 | 8.00 | 5.27 | 1.52x |
| MiMo-V2.6-Flash | 16 | 8 | 8.00 | 5.78 | 1.38x |
| MiMo-V2.6-Flash | 32 | 8 | 8.00 | 6.14 | 1.30x |
| MiMo-V2.6-Flash | 64 | 8 | 8.00 | 6.36 | 1.26x |
| MiMo-V2.6-Flash | 256 | 8 | 8.00 | 6.45 | 1.24x |
| MiMo-V2.6-Flash | 1024 | 8 | 8.00 | 6.45 | 1.24x |
| MiMo-V2.6-Flash | 4096 | 8 | 8.00 | 6.45 | 1.24x |
| MiMo-V2.6-Flash | 1 | 15 | 6.36 | 4.06 | 1.57x |
| MiMo-V2.6-Flash | 2 | 15 | 9.94 | 5.24 | 1.90x |
| MiMo-V2.6-Flash | 4 | 15 | 13.17 | 6.51 | 2.02x |
| MiMo-V2.6-Flash | 8 | 15 | 14.71 | 7.78 | 1.89x |
| MiMo-V2.6-Flash | 16 | 15 | 14.99 | 8.90 | 1.68x |
| MiMo-V2.6-Flash | 32 | 15 | 15.00 | 9.77 | 1.54x |
| MiMo-V2.6-Flash | 64 | 15 | 15.00 | 10.30 | 1.46x |
| MiMo-V2.6-Flash | 256 | 15 | 15.00 | 10.54 | 1.42x |
| MiMo-V2.6-Flash | 1024 | 15 | 15.00 | 10.54 | 1.42x |
| MiMo-V2.6-Flash | 4096 | 15 | 15.00 | 10.54 | 1.42x |
| MiMo-V2.6-Flash | 1 | 16 | 6.45 | 4.14 | 1.56x |
| MiMo-V2.6-Flash | 2 | 16 | 10.21 | 5.38 | 1.90x |
| MiMo-V2.6-Flash | 4 | 16 | 13.77 | 6.72 | 2.05x |
| MiMo-V2.6-Flash | 8 | 16 | 15.61 | 8.07 | 1.93x |
| MiMo-V2.6-Flash | 16 | 16 | 15.98 | 9.28 | 1.72x |
| MiMo-V2.6-Flash | 32 | 16 | 16.00 | 10.22 | 1.57x |
| MiMo-V2.6-Flash | 64 | 16 | 16.00 | 10.80 | 1.48x |
| MiMo-V2.6-Flash | 256 | 16 | 16.00 | 11.05 | 1.45x |
| MiMo-V2.6-Flash | 1024 | 16 | 16.00 | 11.05 | 1.45x |
| MiMo-V2.6-Flash | 4096 | 16 | 16.00 | 11.05 | 1.45x |
| MiMo-V2.6-Flash | 1 | 17 | 6.53 | 4.22 | 1.55x |
| MiMo-V2.6-Flash | 2 | 17 | 10.46 | 5.50 | 1.90x |
| MiMo-V2.6-Flash | 4 | 17 | 14.33 | 6.92 | 2.07x |
| MiMo-V2.6-Flash | 8 | 17 | 16.48 | 8.35 | 1.97x |
| MiMo-V2.6-Flash | 16 | 17 | 16.96 | 9.64 | 1.76x |
| MiMo-V2.6-Flash | 32 | 17 | 17.00 | 10.65 | 1.60x |
| MiMo-V2.6-Flash | 64 | 17 | 17.00 | 11.28 | 1.51x |
| MiMo-V2.6-Flash | 256 | 17 | 17.00 | 11.56 | 1.47x |
| MiMo-V2.6-Flash | 1024 | 17 | 17.00 | 11.56 | 1.47x |
| MiMo-V2.6-Flash | 4096 | 17 | 17.00 | 11.56 | 1.47x |
| MiMo-V2.6-Flash | 1 | 18 | 6.61 | 4.29 | 1.54x |
| MiMo-V2.6-Flash | 2 | 18 | 10.68 | 5.62 | 1.90x |
| MiMo-V2.6-Flash | 4 | 18 | 14.86 | 7.11 | 2.09x |
| MiMo-V2.6-Flash | 8 | 18 | 17.32 | 8.62 | 2.01x |
| MiMo-V2.6-Flash | 16 | 18 | 17.95 | 9.99 | 1.80x |
| MiMo-V2.6-Flash | 32 | 18 | 18.00 | 11.08 | 1.62x |
| MiMo-V2.6-Flash | 64 | 18 | 18.00 | 11.76 | 1.53x |
| MiMo-V2.6-Flash | 256 | 18 | 18.00 | 12.05 | 1.49x |
| MiMo-V2.6-Flash | 1024 | 18 | 18.00 | 12.05 | 1.49x |
| MiMo-V2.6-Flash | 4096 | 18 | 18.00 | 12.05 | 1.49x |
| MiMo-V2.6-Flash | 1 | 19 | 6.67 | 4.36 | 1.53x |
| MiMo-V2.6-Flash | 2 | 19 | 10.89 | 5.74 | 1.90x |
| MiMo-V2.6-Flash | 4 | 19 | 15.35 | 7.29 | 2.11x |
| MiMo-V2.6-Flash | 8 | 19 | 18.15 | 8.87 | 2.05x |
| MiMo-V2.6-Flash | 16 | 19 | 18.92 | 10.33 | 1.83x |
| MiMo-V2.6-Flash | 32 | 19 | 19.00 | 11.49 | 1.65x |
| MiMo-V2.6-Flash | 64 | 19 | 19.00 | 12.22 | 1.56x |
| MiMo-V2.6-Flash | 256 | 19 | 19.00 | 12.53 | 1.52x |
| MiMo-V2.6-Flash | 1024 | 19 | 19.00 | 12.53 | 1.52x |
| MiMo-V2.6-Flash | 4096 | 19 | 19.00 | 12.53 | 1.52x |
| MiMo-V2.6-Flash | 1 | 20 | 6.73 | 4.42 | 1.52x |
| MiMo-V2.6-Flash | 2 | 20 | 11.08 | 5.85 | 1.90x |
| MiMo-V2.6-Flash | 4 | 20 | 15.82 | 7.46 | 2.12x |
| MiMo-V2.6-Flash | 8 | 20 | 18.95 | 9.12 | 2.08x |
| MiMo-V2.6-Flash | 16 | 20 | 19.89 | 10.66 | 1.87x |
| MiMo-V2.6-Flash | 32 | 20 | 20.00 | 11.89 | 1.68x |
| MiMo-V2.6-Flash | 64 | 20 | 20.00 | 12.66 | 1.58x |
| MiMo-V2.6-Flash | 256 | 20 | 20.00 | 13.00 | 1.54x |
| MiMo-V2.6-Flash | 1024 | 20 | 20.00 | 13.00 | 1.54x |
| MiMo-V2.6-Flash | 4096 | 20 | 20.00 | 13.00 | 1.54x |
| MiMo-V2.6-Flash | 1 | 21 | 6.79 | 4.48 | 1.51x |
| MiMo-V2.6-Flash | 2 | 21 | 11.26 | 5.95 | 1.89x |
| MiMo-V2.6-Flash | 4 | 21 | 16.27 | 7.62 | 2.13x |
| MiMo-V2.6-Flash | 8 | 21 | 19.72 | 9.36 | 2.11x |
| MiMo-V2.6-Flash | 16 | 21 | 20.85 | 10.98 | 1.90x |
| MiMo-V2.6-Flash | 32 | 21 | 20.99 | 12.28 | 1.71x |
| MiMo-V2.6-Flash | 64 | 21 | 21.00 | 13.10 | 1.60x |
| MiMo-V2.6-Flash | 256 | 21 | 21.00 | 13.46 | 1.56x |
| MiMo-V2.6-Flash | 1024 | 21 | 21.00 | 13.46 | 1.56x |
| MiMo-V2.6-Flash | 4096 | 21 | 21.00 | 13.46 | 1.56x |
| MiMo-V2.6-Flash | 1 | 23 | 6.88 | 4.60 | 1.50x |
| MiMo-V2.6-Flash | 2 | 23 | 11.58 | 6.14 | 1.88x |
| MiMo-V2.6-Flash | 4 | 23 | 17.08 | 7.94 | 2.15x |
| MiMo-V2.6-Flash | 8 | 23 | 21.21 | 9.82 | 2.16x |
| MiMo-V2.6-Flash | 16 | 23 | 22.75 | 11.60 | 1.96x |
| MiMo-V2.6-Flash | 32 | 23 | 22.98 | 13.04 | 1.76x |
| MiMo-V2.6-Flash | 64 | 23 | 23.00 | 13.95 | 1.65x |
| MiMo-V2.6-Flash | 256 | 23 | 23.00 | 14.35 | 1.60x |
| MiMo-V2.6-Flash | 1024 | 23 | 23.00 | 14.35 | 1.60x |
| MiMo-V2.6-Flash | 4096 | 23 | 23.00 | 14.35 | 1.60x |
| MiMo-V2.6-Flash | 1 | 24 | 6.93 | 4.65 | 1.49x |
| MiMo-V2.6-Flash | 2 | 24 | 11.72 | 6.23 | 1.88x |
| MiMo-V2.6-Flash | 4 | 24 | 17.46 | 8.08 | 2.16x |
| MiMo-V2.6-Flash | 8 | 24 | 21.92 | 10.04 | 2.18x |
| MiMo-V2.6-Flash | 16 | 24 | 23.69 | 11.89 | 1.99x |
| MiMo-V2.6-Flash | 32 | 24 | 23.98 | 13.40 | 1.79x |
| MiMo-V2.6-Flash | 64 | 24 | 24.00 | 14.36 | 1.67x |
| MiMo-V2.6-Flash | 256 | 24 | 24.00 | 14.79 | 1.62x |
| MiMo-V2.6-Flash | 1024 | 24 | 24.00 | 14.79 | 1.62x |
| MiMo-V2.6-Flash | 4096 | 24 | 24.00 | 14.79 | 1.62x |
| MiMo-V2.6-Flash | 1 | 25 | 6.97 | 4.71 | 1.48x |
| MiMo-V2.6-Flash | 2 | 25 | 11.86 | 6.32 | 1.88x |
| MiMo-V2.6-Flash | 4 | 25 | 17.81 | 8.22 | 2.17x |
| MiMo-V2.6-Flash | 8 | 25 | 22.60 | 10.25 | 2.21x |
| MiMo-V2.6-Flash | 16 | 25 | 24.61 | 12.18 | 2.02x |
| MiMo-V2.6-Flash | 32 | 25 | 24.97 | 13.75 | 1.82x |
| MiMo-V2.6-Flash | 64 | 25 | 25.00 | 14.76 | 1.69x |
| MiMo-V2.6-Flash | 256 | 25 | 25.00 | 15.21 | 1.64x |
| MiMo-V2.6-Flash | 1024 | 25 | 25.00 | 15.21 | 1.64x |
| MiMo-V2.6-Flash | 4096 | 25 | 25.00 | 15.21 | 1.64x |
| MiMo-V2.6-Flash | 1 | 29 | 7.10 | 4.90 | 1.45x |
| MiMo-V2.6-Flash | 2 | 29 | 12.31 | 6.63 | 1.86x |
| MiMo-V2.6-Flash | 4 | 29 | 19.07 | 8.74 | 2.18x |
| MiMo-V2.6-Flash | 8 | 29 | 25.13 | 11.03 | 2.28x |
| MiMo-V2.6-Flash | 16 | 29 | 28.19 | 13.25 | 2.13x |
| MiMo-V2.6-Flash | 32 | 29 | 28.91 | 15.10 | 1.91x |
| MiMo-V2.6-Flash | 64 | 29 | 28.99 | 16.29 | 1.78x |
| MiMo-V2.6-Flash | 256 | 29 | 29.00 | 16.82 | 1.72x |
| MiMo-V2.6-Flash | 1024 | 29 | 29.00 | 16.82 | 1.72x |
| MiMo-V2.6-Flash | 4096 | 29 | 29.00 | 16.82 | 1.72x |
| MiMo-V2.6-Flash | 1 | 31 | 7.15 | 4.99 | 1.43x |
| MiMo-V2.6-Flash | 2 | 31 | 12.50 | 6.77 | 1.85x |
| MiMo-V2.6-Flash | 4 | 31 | 19.61 | 8.98 | 2.18x |
| MiMo-V2.6-Flash | 8 | 31 | 26.28 | 11.39 | 2.31x |
| MiMo-V2.6-Flash | 16 | 31 | 29.91 | 13.75 | 2.17x |
| MiMo-V2.6-Flash | 32 | 31 | 30.85 | 15.73 | 1.96x |
| MiMo-V2.6-Flash | 64 | 31 | 30.98 | 17.01 | 1.82x |
| MiMo-V2.6-Flash | 256 | 31 | 30.99 | 17.59 | 1.76x |
| MiMo-V2.6-Flash | 1024 | 31 | 30.99 | 17.59 | 1.76x |
| MiMo-V2.6-Flash | 4096 | 31 | 30.99 | 17.59 | 1.76x |
| MiMo-V2.6-Flash | 1 | 43 | 7.38 | 5.41 | 1.36x |
| MiMo-V2.6-Flash | 2 | 43 | 13.32 | 7.44 | 1.79x |
| MiMo-V2.6-Flash | 4 | 43 | 22.04 | 10.17 | 2.17x |
| MiMo-V2.6-Flash | 8 | 43 | 31.87 | 13.24 | 2.41x |
| MiMo-V2.6-Flash | 16 | 43 | 39.10 | 16.36 | 2.39x |
| MiMo-V2.6-Flash | 32 | 43 | 42.08 | 19.07 | 2.21x |
| MiMo-V2.6-Flash | 64 | 43 | 42.77 | 20.88 | 2.05x |
| MiMo-V2.6-Flash | 256 | 43 | 42.90 | 21.70 | 1.98x |
| MiMo-V2.6-Flash | 1024 | 43 | 42.90 | 21.70 | 1.98x |
| MiMo-V2.6-Flash | 4096 | 43 | 42.90 | 21.70 | 1.98x |
| MiMo-V2.6-Flash | 1 | 46 | 7.42 | 5.50 | 1.35x |
| MiMo-V2.6-Flash | 2 | 46 | 13.46 | 7.57 | 1.78x |
| MiMo-V2.6-Flash | 4 | 46 | 22.49 | 10.42 | 2.16x |
| MiMo-V2.6-Flash | 8 | 46 | 32.98 | 13.63 | 2.42x |
| MiMo-V2.6-Flash | 16 | 46 | 41.11 | 16.93 | 2.43x |
| MiMo-V2.6-Flash | 32 | 46 | 44.73 | 19.81 | 2.26x |
| MiMo-V2.6-Flash | 64 | 46 | 45.65 | 21.74 | 2.10x |
| MiMo-V2.6-Flash | 256 | 46 | 45.83 | 22.62 | 2.03x |
| MiMo-V2.6-Flash | 1024 | 46 | 45.83 | 22.63 | 2.03x |
| MiMo-V2.6-Flash | 4096 | 46 | 45.83 | 22.63 | 2.03x |
| MiMo-V2.6-Flash | 1 | 57 | 7.53 | 5.78 | 1.30x |
| MiMo-V2.6-Flash | 2 | 57 | 13.87 | 8.01 | 1.73x |
| MiMo-V2.6-Flash | 4 | 57 | 23.80 | 11.24 | 2.12x |
| MiMo-V2.6-Flash | 8 | 57 | 36.37 | 14.91 | 2.44x |
| MiMo-V2.6-Flash | 16 | 57 | 47.62 | 18.79 | 2.53x |
| MiMo-V2.6-Flash | 32 | 57 | 53.83 | 22.27 | 2.42x |
| MiMo-V2.6-Flash | 64 | 57 | 55.89 | 24.64 | 2.27x |
| MiMo-V2.6-Flash | 256 | 57 | 56.39 | 25.73 | 2.19x |
| MiMo-V2.6-Flash | 1024 | 57 | 56.39 | 25.73 | 2.19x |
| MiMo-V2.6-Flash | 4096 | 57 | 56.39 | 25.73 | 2.19x |
| MiMo-V2.6-Flash | 1 | 58 | 7.53 | 5.80 | 1.30x |
| MiMo-V2.6-Flash | 2 | 58 | 13.90 | 8.05 | 1.73x |
| MiMo-V2.6-Flash | 4 | 58 | 23.89 | 11.30 | 2.11x |
| MiMo-V2.6-Flash | 8 | 58 | 36.63 | 15.01 | 2.44x |
| MiMo-V2.6-Flash | 16 | 58 | 48.15 | 18.95 | 2.54x |
| MiMo-V2.6-Flash | 32 | 58 | 54.61 | 22.48 | 2.43x |
| MiMo-V2.6-Flash | 64 | 58 | 56.79 | 24.88 | 2.28x |
| MiMo-V2.6-Flash | 256 | 58 | 57.32 | 25.99 | 2.21x |
| MiMo-V2.6-Flash | 1024 | 58 | 57.32 | 25.99 | 2.21x |
| MiMo-V2.6-Flash | 4096 | 58 | 57.32 | 25.99 | 2.21x |
| MiMo-V2.6-Flash | 1 | 61 | 7.56 | 5.86 | 1.29x |
| MiMo-V2.6-Flash | 2 | 61 | 13.98 | 8.15 | 1.71x |
| MiMo-V2.6-Flash | 4 | 61 | 24.17 | 11.49 | 2.10x |
| MiMo-V2.6-Flash | 8 | 61 | 37.39 | 15.32 | 2.44x |
| MiMo-V2.6-Flash | 16 | 61 | 49.69 | 19.40 | 2.56x |
| MiMo-V2.6-Flash | 32 | 61 | 56.90 | 23.08 | 2.47x |
| MiMo-V2.6-Flash | 64 | 61 | 59.46 | 25.60 | 2.32x |
| MiMo-V2.6-Flash | 256 | 61 | 60.11 | 26.76 | 2.25x |
| MiMo-V2.6-Flash | 1024 | 61 | 60.11 | 26.76 | 2.25x |
| MiMo-V2.6-Flash | 4096 | 61 | 60.11 | 26.76 | 2.25x |
| MiMo-V2.6-Flash | 1 | 87 | 7.69 | 6.29 | 1.22x |
| MiMo-V2.6-Flash | 2 | 87 | 14.48 | 8.92 | 1.62x |
| MiMo-V2.6-Flash | 4 | 87 | 25.87 | 12.81 | 2.02x |
| MiMo-V2.6-Flash | 8 | 87 | 42.21 | 17.47 | 2.42x |
| MiMo-V2.6-Flash | 16 | 87 | 60.23 | 22.70 | 2.65x |
| MiMo-V2.6-Flash | 32 | 87 | 73.83 | 27.56 | 2.68x |
| MiMo-V2.6-Flash | 64 | 87 | 80.35 | 30.98 | 2.59x |
| MiMo-V2.6-Flash | 256 | 87 | 82.49 | 32.58 | 2.53x |
| MiMo-V2.6-Flash | 1024 | 87 | 82.49 | 32.58 | 2.53x |
| MiMo-V2.6-Flash | 4096 | 87 | 82.49 | 32.58 | 2.53x |
| MiMo-V2.6-Flash | 1 | 116 | 7.76 | 6.60 | 1.18x |
| MiMo-V2.6-Flash | 2 | 116 | 14.79 | 9.59 | 1.54x |
| MiMo-V2.6-Flash | 4 | 116 | 26.95 | 13.78 | 1.96x |
| MiMo-V2.6-Flash | 8 | 116 | 45.44 | 19.29 | 2.36x |
| MiMo-V2.6-Flash | 16 | 116 | 68.02 | 25.53 | 2.66x |
| MiMo-V2.6-Flash | 32 | 116 | 87.79 | 31.47 | 2.79x |
| MiMo-V2.6-Flash | 64 | 116 | 99.09 | 35.74 | 2.77x |
| MiMo-V2.6-Flash | 256 | 116 | 103.35 | 37.76 | 2.74x |
| MiMo-V2.6-Flash | 1024 | 116 | 103.36 | 37.77 | 2.74x |
| MiMo-V2.6-Flash | 4096 | 116 | 103.36 | 37.77 | 2.74x |
| MiMo-V2.6-Flash | 1 | 173 | 7.84 | 6.97 | 1.12x |
| MiMo-V2.6-Flash | 2 | 173 | 15.10 | 10.58 | 1.43x |
| MiMo-V2.6-Flash | 4 | 173 | 28.06 | 15.05 | 1.87x |
| MiMo-V2.6-Flash | 8 | 173 | 48.98 | 22.00 | 2.23x |
| MiMo-V2.6-Flash | 16 | 173 | 77.21 | 29.58 | 2.61x |
| MiMo-V2.6-Flash | 32 | 173 | 105.88 | 37.19 | 2.85x |
| MiMo-V2.6-Flash | 64 | 173 | 125.36 | 42.87 | 2.92x |
| MiMo-V2.6-Flash | 256 | 173 | 133.76 | 45.58 | 2.93x |
| MiMo-V2.6-Flash | 1024 | 173 | 133.78 | 45.59 | 2.93x |
| MiMo-V2.6-Flash | 4096 | 173 | 133.78 | 45.59 | 2.93x |
| MiMo-V2.6-Flash | 1 | 231 | 7.88 | 7.19 | 1.10x |
| MiMo-V2.6-Flash | 2 | 231 | 15.26 | 11.30 | 1.35x |
| MiMo-V2.6-Flash | 4 | 231 | 28.66 | 16.00 | 1.79x |
| MiMo-V2.6-Flash | 8 | 231 | 50.94 | 23.91 | 2.13x |
| MiMo-V2.6-Flash | 16 | 231 | 82.58 | 32.43 | 2.55x |
| MiMo-V2.6-Flash | 32 | 231 | 117.26 | 41.58 | 2.82x |
| MiMo-V2.6-Flash | 64 | 231 | 143.00 | 48.35 | 2.96x |
| MiMo-V2.6-Flash | 256 | 231 | 154.89 | 51.66 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 231 | 154.92 | 51.66 | 3.00x |
| MiMo-V2.6-Flash | 4096 | 231 | 154.92 | 51.66 | 3.00x |
| MiMo-V2.6-Flash | 1 | 347 | 7.92 | 7.43 | 1.07x |
| MiMo-V2.6-Flash | 2 | 347 | 15.42 | 12.28 | 1.26x |
| MiMo-V2.6-Flash | 4 | 347 | 29.27 | 17.53 | 1.67x |
| MiMo-V2.6-Flash | 8 | 347 | 52.99 | 26.19 | 2.02x |
| MiMo-V2.6-Flash | 16 | 347 | 88.46 | 36.85 | 2.40x |
| MiMo-V2.6-Flash | 32 | 347 | 130.41 | 47.91 | 2.72x |
| MiMo-V2.6-Flash | 64 | 347 | 164.39 | 56.35 | 2.92x |
| MiMo-V2.6-Flash | 256 | 347 | 181.21 | 60.46 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 347 | 181.25 | 60.47 | 3.00x |
| MiMo-V2.6-Flash | 4096 | 347 | 181.25 | 60.47 | 3.00x |

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
| gpu | MiMo-V2.6-Flash | 1 | 323.95 | 45.9% |
| rom | MiMo-V2.6-Flash | 1 | 103.85 | 67.6% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| MiMo-V2.6-Flash | sram | interleaved | 128 B | 1.00x |
| MiMo-V2.6-Flash | hbm | interleaved | 32 B | 1.00x |

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
| MiMo-V2.6-Flash | 1 | 15 | 12.32% | 17.16 | 9.28 |
| MiMo-V2.6-Flash | 2 | 15 | 12.32% | 17.16 | 9.28 |
| MiMo-V2.6-Flash | 4 | 15 | 12.32% | 17.16 | 9.28 |
| MiMo-V2.6-Flash | 8 | 15 | 12.32% | 17.16 | 9.28 |
| MiMo-V2.6-Flash | 16 | 1 | 0.25% | 1.32 | 9.28 |
| MiMo-V2.6-Flash | 32 | 1 | 0.25% | 1.32 | 9.28 |
| MiMo-V2.6-Flash | 64 | 1 | 0.28% | 1.48 | 9.28 |
| MiMo-V2.6-Flash | 256 | 1 | 1.12% | 5.93 | 9.28 |

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
| MiMo-V2.6-Flash | 1 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 979.2 | 31,336.0 |
| MiMo-V2.6-Flash | 2 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 979.2 | 31,336.0 |
| MiMo-V2.6-Flash | 4 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 979.2 | 31,336.0 |
| MiMo-V2.6-Flash | 8 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 979.2 | 31,336.0 |
| MiMo-V2.6-Flash | 16 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 979.2 | 31,336.0 |
| MiMo-V2.6-Flash | 32 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 979.2 | 31,336.0 |
| MiMo-V2.6-Flash | 64 | 6.15% | 17.5 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 511.4 | 32,731.7 |
| MiMo-V2.6-Flash | 256 | 22.43% | 43.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 132.3 | 33,862.9 |
| MiMo-V2.6-Flash | 1024 | 63.79% | 110.3 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 33.3 | 34,141.9 |
| MiMo-V2.6-Flash | 4096 | 98.28% | 165.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 8.3 | 34,168.4 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | kv_read | 19 |
| gpu | link_latency | 969 |
| gpu | thermal | 61 |
| gpu | weight_read | 421 |
| rom | compute | 478 |
| rom | infeasible | 2096 |
| rom | kv_read | 182 |
| rom | layer_fixed_latency | 562 |
| rom | link_latency | 899 |
| rom | weight_read | 583 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2096 |

## Mechanical consistency audit

**FAIL** over 131,996 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x30', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x31', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x32', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x34', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x35', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x42', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x56', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x84', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x112', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x30', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x31', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x32', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x34', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x35', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x42', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x56', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x84', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x112', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x30', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x31', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x32', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x34', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x35', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x42', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x56', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x84', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x112', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x30', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x31', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x32', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x34', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x35', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x42', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x56', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x57', 'MiMo-V2.6-Flash', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 75 |
| derived | 52 |
| assumed | 86 |

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
- `links.rom_package_ucie.relay_latency_s`
- `links.rom_package_ucie_diagonal.hop_latency_s`
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

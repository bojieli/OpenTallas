# Area-constrained roofline: n5_vs_b200-mimo-v26-flash-1m

> CANDIDATE MODEL under n5_vs_b200: MiMo-V2.6-Flash at 1,000,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 1,155x (ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream, 6,183 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 105 devices. On the GPU side the correction reaches 6x (b200_sxm-x3149-pipeline, 3,149 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 36 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Flash takes 55 x 815 mm2 (44,825 mm2, array, KV in SRAM) at 3,688 tok/s per user and 82 tok/s per 1,000 mm2, holding 1 session, against 28 copies of one unified HBM die at the same silicon: 5.5x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Flash on 85,575 mm2 of ROM silicon at 4,383 tok/s per user against 84,800 mm2 of b200_sxm-x53-nvl72-tensor at 719 tok/s: **6.1x**, ROM binding on `layer_fixed_latency` and the GPU on `layer_fixed_latency`. It holds 1 resident session against the GPU cluster's 364. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 4.73x to it.** At 554,700 mm2 on MiMo-V2.6-Flash the pipeline-only GPU delivers 153.47 tok/s and the same silicon running hybrid delivers 726 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.07x (MiMo-V2.6-Flash, ROM binding on `layer_fixed_latency`) to 0.28x (MiMo-V2.6-Flash, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Flash engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 27 to 108,744 tok/s, and its rate with every slot occupied from 109,221 to 109,221. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 6,183 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,059 us over NVLink, capping per-user decode at 944 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 396.4 us and cap it at 2,523 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 9 of 10 operating points and an array 1; on tokens per second per square millimetre the same points go 1 to the array and 9 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 475 of 1634 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 6.3x of aggregate throughput (MiMo-V2.6-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 6.21x, on MiMo-V2.6-Flash at batch 4096, where the busiest region carries 3.00x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 18 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **The cooling limit binds, and not where a uniform correction said it would.** 34 of 1,634 feasible points (2.1%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `MiMo-V2.6-Flash/b200_sxm-x585-pipeline` at batch 4096 on 936,000 mm2, throttled 1.06x from 31 to 30 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 77% kv read against 18.9% weight read. The ROM sweep is not what melts it.


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

### MiMo-V2.6-Flash at 1,000,000 tokens

**Recommended: `ROM-N5-native-SRAMKV-array-hw-hybrid-x55-romfill`** -- 55 x 815 mm2 reticle dies, 44,825 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `rom`.

- **3,687.7 tok/s per user** (0.27 ms/token), binding on `layer_fixed_latency`
- **82.3 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 3,688 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 3,739 W at 0.083 W/mm2, 1,013.9 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 28 copies of one unified HBM die -- `b200_sxm-x28-nvl72-tensor`, 44,800 mm2, area ratio 1.0006 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 44,825 | 44,800 | 1.0006 |
| user tok/s | 3,687.7 | 674.2 | 5.47x |
| aggregate tok/s | 3,688 | 674 | 0.85x |
| resident sessions | 1 | 189 | -- |
| J/token | 1.0139 | 18.4339 | 18.2x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 189 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x347-nvl72-hybrid` at 555,200 mm2 and 726.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 85,575 | 4,383.4 | 51.2 | 1 | 6.09x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 85,575 | 4,383.4 | 51.2 | 1 | 6.09x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-tensor-x47` | 38,305 | 2,819.8 | 73.6 | 1 | 4.28x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-array-hw-hybrid-x55-romfill` | 44,825 | 3,687.7 | 82.3 | 1 | 5.47x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x55-romfill` | 44,825 | 3,687.7 | 82.3 | -- | 82.3 | ACCEPT |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 45,640 | 3,709.6 | 81.3 | 26.8 | 82.3 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x57` | 46,455 | 3,729.5 | 80.3 | 25.6 | 82.3 | stop |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x64` | 52,160 | 3,918.7 | 75.1 | 31.5 | 82.3 | stop |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 85,575 | 4,383.4 | 51.2 | 17.1 | 82.3 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x55-romfill` **<-- recommended** | 44,825 | 55 | 3,687.7 | 3,688 | 82.3 | 1 | `layer_fixed_latency` | 3,739 | 1,013.9 | `b200_sxm-x28-nvl72-tensor` | 5.47x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | 45,640 | 56 | 3,709.6 | 3,710 | 81.3 | 1 | `layer_fixed_latency` | 3,859 | 1,040.3 | `b200_sxm-x29-nvl72-tensor` | 5.48x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x57` | 46,455 | 57 | 3,729.5 | 3,730 | 80.3 | 1 | `layer_fixed_latency` | 3,979 | 1,066.8 | `b200_sxm-x29-nvl72-tensor` | 5.51x |
| `ROM-N5-native-SRAMKV-array-hw-tensor-x64` | 52,160 | 64 | 3,918.7 | 3,919 | 75.1 | 1 | `layer_fixed_latency` | 4,822 | 1,230.5 | `b200_sxm-x33-nvl72-tensor` | 5.70x |
| `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 85,575 | 105 | 4,383.4 | 4,383 | 51.2 | 1 | `layer_fixed_latency` | 9,707 | 2,214.4 | `b200_sxm-x53-nvl72-tensor` | 6.09x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 162 | densest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x55-romfill` | 44,825 | 3,687.7 | 82.3 | 1 |
| array | 162 | fastest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 85,575 | 4,383.4 | 51.2 | 1 |
| array | 162 | smallest | `ROM-N5-native-SRAMKV-array-hw-tensor-x47` | 38,305 | 2,819.8 | 73.6 | 1 |
| wafer | 46 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 2,582.2 | 55.9 | 1 |
| wafer | 46 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,406.7 | 36.8 | 1 |
| wafer | 46 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 2,582.2 | 55.9 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 85,575 | 4,383.4 | 4,383 | 1 | 9,707 | 2,214.4 | `layer_fixed_latency` | `b200_sxm-x53-nvl72-tensor` | 719.2 | 364 | 29,704.5 | 1.009 | 6.09x | 13.4x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,406.7 | 3,407 | 1 | 10,621 | 3,117.6 | `link_latency` | `b200_sxm-x58-nvl72-tensor` | 723.9 | 399 | 31,958.6 | 0.996 | 4.71x | 10.3x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-hybrid-x111` | 90,465 | 4,383.4 | 4,383 | 1 | 10,416 | 2,376.2 | `layer_fixed_latency` | `b200_sxm-x57-nvl72-tensor` | 723.0 | 392 | 31,507.8 | 0.992 | 6.06x | 13.3x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 3,406.7 | -- | 1 | -- | 3,117.6 | -- | -- | -- | -- | -- | 0.979 | 0.78x wafer/array | -- |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5,038,525 | 1,382.5 | 38,710 | 4,114 | 836,000 | 270,579.0 | `link_latency` | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 22,109 | 809,363.5 | 1.000 | 2.02x | 3.0x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5,038,525 | 1,382.5 | 38,710 | 4,114 | 836,000 | 136,511.5 | `link_latency` | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 22,109 | 406,621.4 | 1.000 | 2.02x | 3.0x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5,038,525 | 1,382.5 | 38,710 | 4,114 | 836,000 | 69,477.7 | `link_latency` | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 22,109 | 205,250.4 | 1.000 | 2.02x | 3.0x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5,038,525 | 1,382.5 | 38,710 | 4,114 | 836,000 | 35,960.8 | `link_latency` | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 22,109 | 104,564.9 | 1.000 | 2.02x | 2.9x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5,038,525 | 1,332.1 | 42,628 | 4,114 | 845,561 | 19,836.0 | `link_latency` | `b200_sxm-x3149-nvl72-hybrid` | 685.0 | 22,109 | 54,222.2 | 1.000 | 1.94x | 2.7x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5,038,525 | 1,073.9 | 68,730 | 4,114 | 909,342 | 13,230.7 | `link_latency` | `b200_sxm-x3149-nvl72-hybrid` | 670.2 | 22,109 | 29,351.4 | 1.000 | 1.60x | 2.2x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5,038,525 | 543.8 | 139,221 | 4,114 | 1,081,559 | 7,768.7 | `kv_read` | `b200_sxm-x3149-nvl72-hybrid` | 565.7 | 22,109 | 10,993.1 | 1.000 | 0.96x | 1.4x |
| 1024 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5,038,525 | 156.3 | 160,009 | 4,114 | 1,132,351 | 7,076.8 | `kv_read` | `b200_sxm-x3149-nvl72-hybrid` | 351.3 | 22,109 | 6,264.4 | 1.000 | 0.44x | 0.9x |
| 4096 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5,038,525 | 40.0 | 163,819 | 4,114 | 1,141,661 | 6,969.0 | `kv_read` | `b200_sxm-x3149-nvl72-hybrid` | 144.8 | 22,109 | 4,726.1 | 1.000 | 0.28x | 0.7x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x55-romfill` | 44,825 | array | SRAM | 1 |
| 2-4096 | `ROM-N5-native-HBMKV-wafer-hybrid-x109` | 5,038,525 | wafer | HBM | 4,114 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Flash | SRAM | rom | 47, 55, 56, 57, 64, 74, 100, 101, 111, 113, 148, 170, 227, 340 |
| MiMo-V2.6-Flash | SRAM | sram | 47, 56, 57, 64, 70, 74, 105, 111, 113, 148, 170, 227, 340 |

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
| MiMo-V2.6-Flash | `ROM-N5-native-SRAMKV-array-hw-hybrid-x55-romfill` | 1 | 32 | 3.00 | hierarchical | 170.57 | 69.47 | 67.81 | 56.69 | 3,687.7 |
| MiMo-V2.6-Flash | `b200_sxm-x28-nvl72-tensor` | 1 | 28 | 3.00 | measured_floor | 937.30 | 349.02 | 196.96 | 243.76 | 674.2 |
| MiMo-V2.6-Flash | `b200_sxm-x28-nvl72-tensor` | 64 | 28 | 3.00 | measured_floor | 937.30 | 564.61 | 8,948.57 | 403.01 | 95.7 |

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

- **34 of 1,634 feasible points (2.1%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 34.
- By area class: large array (5,000-40,000 mm2) 12, wafer (>=40,000 mm2) 22.
- By KV store: hbm 34.
- By batch: B=32 1, B=64 11, B=256 13, B=1024 6, B=4096 3.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 45% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 32 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 252 | 12 | 73.2% | 100.0% | 0.625 | 48% |
| gpu | wafer (>=40,000 mm2) | 904 | 22 | 56.8% | 100.0% | 0.625 | 62% |
| rom | large array (5,000-40,000 mm2) | 84 | 0 | 13.3% | 14.9% | 0.074 | 97% |
| rom | wafer (>=40,000 mm2) | 394 | 0 | 17.1% | 45.3% | 0.227 | 96% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `MiMo-V2.6-Flash/b200_sxm-x585-pipeline` | MiMo-V2.6-Flash | 4096 | 936,000 | hbm | 1.057x | 585,000.0 / 585,000.0 W | 35% | 29.5 | 31.2 |
| `MiMo-V2.6-Flash/b200_sxm-x38-pipeline` | MiMo-V2.6-Flash | 256 | 60,800 | hbm | 1.056x | 38,000.0 / 38,000.0 W | 35% | 30.6 | 32.3 |
| `MiMo-V2.6-Flash/b200_sxm-x173-pipeline` | MiMo-V2.6-Flash | 1024 | 276,800 | hbm | 1.051x | 173,000.0 / 173,000.0 W | 35% | 34.6 | 36.4 |
| `MiMo-V2.6-Flash/b200_sxm-x13-pipeline` | MiMo-V2.6-Flash | 64 | 20,800 | hbm | 1.046x | 13,000.0 / 13,000.0 W | 35% | 41.1 | 43.0 |
| `MiMo-V2.6-Flash/b200_sxm-x51-pipeline` | MiMo-V2.6-Flash | 256 | 81,600 | hbm | 1.044x | 51,000.0 / 51,000.0 W | 35% | 40.4 | 42.2 |
| `MiMo-V2.6-Flash/b200_sxm-x53-pipeline` | MiMo-V2.6-Flash | 256 | 84,800 | hbm | 1.042x | 53,000.0 / 53,000.0 W | 35% | 41.9 | 43.7 |
| `MiMo-V2.6-Flash/b200_sxm-x57-pipeline` | MiMo-V2.6-Flash | 256 | 91,200 | hbm | 1.039x | 57,000.0 / 57,000.0 W | 35% | 44.8 | 46.6 |
| `MiMo-V2.6-Flash/b200_sxm-x38-hybrid` | MiMo-V2.6-Flash | 256 | 60,800 | hbm | 1.039x | 38,000.0 / 38,000.0 W | 35% | 34.1 | 35.4 |
| `MiMo-V2.6-Flash/b200_sxm-x231-pipeline` | MiMo-V2.6-Flash | 1024 | 369,600 | hbm | 1.038x | 231,000.0 / 231,000.0 W | 35% | 45.4 | 47.1 |
| `MiMo-V2.6-Flash/b200_sxm-x58-pipeline` | MiMo-V2.6-Flash | 256 | 92,800 | hbm | 1.038x | 58,000.0 / 58,000.0 W | 35% | 45.6 | 47.3 |
| `MiMo-V2.6-Flash/b200_sxm-x16-pipeline` | MiMo-V2.6-Flash | 64 | 25,600 | hbm | 1.036x | 16,000.0 / 16,000.0 W | 35% | 49.9 | 51.7 |
| `MiMo-V2.6-Flash/b200_sxm-x17-pipeline` | MiMo-V2.6-Flash | 64 | 27,200 | hbm | 1.032x | 17,000.0 / 17,000.0 W | 35% | 52.8 | 54.5 |

The worst point's dynamic energy is kv read 77.0%, weight read 18.9%, arithmetic 3.9%, operand delivery 0.2%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| MiMo-V2.6-Flash | 1 | 85,575 | `MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x105` | 2.214417 | 9,706.6 | layer_fixed_latency | `MiMo-V2.6-Flash/b200_sxm-x53-nvl72-tensor` | 29.704468 | 21,363.4 | layer_fixed_latency | 13.41x |
| MiMo-V2.6-Flash | 2 | 5,038,525 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109` | 270.579038 | 835,999.7 | link_latency | `MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid` | 809.363465 | 1,220,463.2 | layer_fixed_latency | 2.99x |
| MiMo-V2.6-Flash | 4 | 5,038,525 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109` | 136.511483 | 835,999.7 | link_latency | `MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid` | 406.621435 | 1,220,463.2 | layer_fixed_latency | 2.98x |
| MiMo-V2.6-Flash | 8 | 5,038,525 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109` | 69.477705 | 835,999.7 | link_latency | `MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid` | 205.250420 | 1,220,463.2 | layer_fixed_latency | 2.95x |
| MiMo-V2.6-Flash | 16 | 5,038,525 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109` | 35.960816 | 835,999.7 | link_latency | `MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid` | 104.564912 | 1,220,463.2 | layer_fixed_latency | 2.91x |
| MiMo-V2.6-Flash | 32 | 5,038,525 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109` | 19.836012 | 845,561.0 | link_latency | `MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid` | 54.222158 | 1,220,463.2 | layer_fixed_latency | 2.73x |
| MiMo-V2.6-Flash | 64 | 5,038,525 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109` | 13.230733 | 909,341.8 | link_latency | `MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid` | 29.351375 | 1,259,007.2 | layer_fixed_latency | 2.22x |
| MiMo-V2.6-Flash | 256 | 5,038,525 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109` | 7.768673 | 1,081,559.0 | kv_read | `MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid` | 10.993149 | 1,592,132.7 | layer_fixed_latency | 1.42x |
| MiMo-V2.6-Flash | 1024 | 5,038,525 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109` | 7.076797 | 1,132,351.2 | kv_read | `MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid` | 6.264402 | 2,253,648.3 | kv_read | 0.89x |
| MiMo-V2.6-Flash | 4096 | 5,038,525 | `MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109` | 6.969026 | 1,141,661.1 | kv_read | `MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid` | 4.726122 | 2,803,382.4 | kv_read | 0.68x |

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
| MiMo-V2.6-Flash | 1,000,000 | 309 B | 172.9 GB | 4.48 | 23.066 GB | 23.066 GB | 0.5 |

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
| MiMo-V2.6-Flash | 1 | 46,225 | 5,225.4 | wafer-pipeline | 2,582.2 | wafer-tensor | 2.02x | 857.4 | pipeline | 677.3 | tensor | 1.27x | 6.09x | 3.81x | 0.63x |
| MiMo-V2.6-Flash | 2 | 92,450 | 6,594.6 | wafer-pipeline | 3,406.7 | wafer-hybrid | 1.94x | 912.3 | pipeline | 723.9 | tensor | 1.26x | 7.23x | 4.71x | 0.65x |
| MiMo-V2.6-Flash | 3 | 138,675 | 7,425.1 | wafer-pipeline | 3,080.0 | wafer-hybrid | 2.41x | 939.4 | pipeline | 705.5 | hybrid | 1.33x | 7.90x | 4.37x | 0.55x |
| MiMo-V2.6-Flash | 4 | 184,900 | 7,425.1 | wafer-pipeline | 2,752.7 | wafer-hybrid | 2.70x | 953.6 | pipeline | 721.7 | hybrid | 1.32x | 7.79x | 3.81x | 0.49x |
| MiMo-V2.6-Flash | 6 | 277,350 | 7,425.1 | wafer-pipeline | 2,537.3 | wafer-hybrid | 2.93x | 968.1 | pipeline | 720.2 | hybrid | 1.34x | 7.67x | 3.52x | 0.46x |
| MiMo-V2.6-Flash | 8 | 369,800 | 7,425.1 | wafer-pipeline | 2,295.4 | wafer-hybrid | 3.23x | 975.7 | pipeline | 719.2 | hybrid | 1.36x | 7.61x | 3.19x | 0.42x |
| MiMo-V2.6-Flash | 12 | 554,700 | 7,425.1 | wafer-pipeline | 2,096.5 | wafer-hybrid | 3.54x | 983.3 | pipeline | 726.4 | hybrid | 1.35x | 7.55x | 2.89x | 0.38x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.38x to 0.65x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Flash | 1 | fastest | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x105 | 85,575 | 4,383.4 | 4,383.4 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x53-nvl72-tensor | 84,800 | 1.01x | tensor | 349.08 | 719.2 | 719.2 | layer_fixed_latency | 6.09x | 0.54x | 28.56x | 6.09x |
| MiMo-V2.6-Flash | 1 | smallest silicon | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x47 | 38,305 | 2,819.8 | 2,819.8 | layer_fixed_latency | MiMo-V2.6-Flash/b200_sxm-x24-nvl72-tensor | 38,400 | 1.00x | tensor | 349.00 | 659.6 | 659.6 | layer_fixed_latency | 4.28x | 0.76x | 18.28x | 4.28x |
| MiMo-V2.6-Flash | 2 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1,382.5 | 38,710.1 | link_latency | MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid | 5,038,400 | 1.00x | hybrid | 445.46 | 685.0 | 30,140.6 | layer_fixed_latency | 2.02x | 0.08x | 9.01x | 2.02x |
| MiMo-V2.6-Flash | 4 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1,382.5 | 38,710.1 | link_latency | MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid | 5,038,400 | 1.00x | hybrid | 445.46 | 685.0 | 30,140.6 | layer_fixed_latency | 2.02x | 0.08x | 9.01x | 2.02x |
| MiMo-V2.6-Flash | 8 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1,382.5 | 38,710.1 | link_latency | MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid | 5,038,400 | 1.00x | hybrid | 445.46 | 685.0 | 30,140.6 | layer_fixed_latency | 2.02x | 0.08x | 9.01x | 2.02x |
| MiMo-V2.6-Flash | 16 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1,382.5 | 38,710.1 | link_latency | MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid | 5,038,400 | 1.00x | hybrid | 445.46 | 685.0 | 30,140.6 | layer_fixed_latency | 2.02x | 0.08x | 9.01x | 2.02x |
| MiMo-V2.6-Flash | 32 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1,332.1 | 42,627.6 | link_latency | MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid | 5,038,400 | 1.00x | hybrid | 445.46 | 685.0 | 30,140.6 | layer_fixed_latency | 1.94x | 0.09x | 8.68x | 1.94x |
| MiMo-V2.6-Flash | 64 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1,073.9 | 68,729.5 | link_latency | MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid | 5,038,400 | 1.00x | hybrid | 450.26 | 670.2 | 42,894.3 | layer_fixed_latency | 1.60x | 0.14x | 7.00x | 1.60x |
| MiMo-V2.6-Flash | 256 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 543.8 | 139,220.6 | kv_read | MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid | 5,038,400 | 1.00x | hybrid | 442.32 | 565.7 | 144,829.5 | layer_fixed_latency | 0.96x | 0.29x | 3.54x | 1.01x |
| MiMo-V2.6-Flash | 1024 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 156.3 | 160,009.0 | kv_read | MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid | 5,038,400 | 1.00x | hybrid | 441.53 | 351.3 | 359,754.7 | kv_read | 0.44x | 0.33x | 1.02x | 0.48x |
| MiMo-V2.6-Flash | 4096 | fastest | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 40.0 | 163,819.3 | kv_read | MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid | 5,038,400 | 1.00x | hybrid | 730.31 | 144.8 | 593,167.6 | kv_read | 0.28x | 0.28x | 0.31x | 0.29x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| MiMo-V2.6-Flash | 13 | 20,800 | 348.88 | 232.82 | 584.7 | 627.2 |
| MiMo-V2.6-Flash | 16 | 25,600 | 348.93 | 232.86 | 613.2 | 660.1 |
| MiMo-V2.6-Flash | 17 | 27,200 | 348.94 | 232.87 | 620.9 | 669.1 |
| MiMo-V2.6-Flash | 22 | 35,200 | 348.99 | 232.90 | 650.6 | 703.8 |
| MiMo-V2.6-Flash | 23 | 36,800 | 348.99 | 232.91 | 655.3 | 709.2 |
| MiMo-V2.6-Flash | 24 | 38,400 | 349.00 | 232.91 | 659.6 | 714.3 |
| MiMo-V2.6-Flash | 28 | 44,800 | 349.02 | 232.93 | 674.2 | 731.4 |
| MiMo-V2.6-Flash | 29 | 46,400 | 349.03 | 232.93 | 677.3 | 735.1 |
| MiMo-V2.6-Flash | 33 | 52,800 | 349.04 | 232.94 | 688.0 | 747.7 |
| MiMo-V2.6-Flash | 36 | 57,600 | 349.05 | 232.95 | 694.7 | 755.6 |
| MiMo-V2.6-Flash | 38 | 60,800 | 349.06 | 232.95 | 698.6 | 760.2 |
| MiMo-V2.6-Flash | 51 | 81,600 | 349.08 | 232.97 | 717.1 | 782.2 |
| MiMo-V2.6-Flash | 53 | 84,800 | 349.08 | 232.97 | 719.2 | 784.7 |
| MiMo-V2.6-Flash | 57 | 91,200 | 349.09 | 232.98 | 723.0 | 789.2 |
| MiMo-V2.6-Flash | 58 | 92,800 | 349.09 | 232.98 | 723.9 | 790.3 |
| MiMo-V2.6-Flash | 75 | 120,000 | 353.32 | 235.18 | 695.6 | 757.8 |
| MiMo-V2.6-Flash | 87 | 139,200 | 353.32 | 235.18 | 705.5 | 769.7 |
| MiMo-V2.6-Flash | 116 | 185,600 | 353.32 | 235.18 | 721.7 | 788.9 |
| MiMo-V2.6-Flash | 173 | 276,800 | 355.51 | 237.37 | 720.2 | 787.2 |
| MiMo-V2.6-Flash | 231 | 369,600 | 357.70 | 239.57 | 719.2 | 785.9 |
| MiMo-V2.6-Flash | 347 | 555,200 | 359.90 | 241.76 | 726.4 | 794.6 |
| MiMo-V2.6-Flash | 585 | 936,000 | 368.68 | 250.54 | 719.0 | 785.7 |
| MiMo-V2.6-Flash | 3,149 | 5,038,400 | 445.46 | 327.32 | 685.0 | 745.3 |

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
| MiMo-V2.6-Flash | 13 | 20,800 | 154.6 | 584.7 | 467.6 | tensor | 348.88 | 20.4% | layer_fixed_latency |
| MiMo-V2.6-Flash | 16 | 25,600 | 154.5 | 613.2 | 505.2 | tensor | 348.93 | 21.4% | layer_fixed_latency |
| MiMo-V2.6-Flash | 17 | 27,200 | 154.4 | 620.9 | 441.4 | tensor | 348.94 | 21.7% | layer_fixed_latency |
| MiMo-V2.6-Flash | 22 | 35,200 | 154.3 | 650.6 | 489.1 | tensor | 348.99 | 22.7% | layer_fixed_latency |
| MiMo-V2.6-Flash | 23 | 36,800 | 154.3 | 655.3 | 497.1 | tensor | 348.99 | 22.9% | layer_fixed_latency |
| MiMo-V2.6-Flash | 24 | 38,400 | 154.2 | 659.6 | 504.6 | tensor | 349.00 | 23.0% | layer_fixed_latency |
| MiMo-V2.6-Flash | 28 | 44,800 | 154.1 | 674.2 | 480.2 | tensor | 349.02 | 23.5% | layer_fixed_latency |
| MiMo-V2.6-Flash | 29 | 46,400 | 154.1 | 677.3 | 486.5 | tensor | 349.03 | 23.6% | layer_fixed_latency |
| MiMo-V2.6-Flash | 33 | 52,800 | 153.9 | 688.0 | 469.0 | tensor | 349.04 | 24.0% | layer_fixed_latency |
| MiMo-V2.6-Flash | 36 | 57,600 | 153.8 | 694.7 | 484.8 | tensor | 349.05 | 24.2% | layer_fixed_latency |
| MiMo-V2.6-Flash | 38 | 60,800 | 153.8 | 698.6 | 494.4 | tensor | 349.06 | 24.4% | layer_fixed_latency |
| MiMo-V2.6-Flash | 51 | 81,600 | 153.5 | 717.1 | 485.9 | tensor | 349.08 | 25.0% | layer_fixed_latency |
| MiMo-V2.6-Flash | 53 | 84,800 | 153.5 | 719.2 | 492.7 | tensor | 349.08 | 25.1% | layer_fixed_latency |
| MiMo-V2.6-Flash | 57 | 91,200 | 153.5 | 723.0 | 481.4 | tensor | 349.09 | 25.2% | layer_fixed_latency |
| MiMo-V2.6-Flash | 58 | 92,800 | 153.5 | 723.9 | 484.5 | tensor | 349.09 | 25.3% | layer_fixed_latency |
| MiMo-V2.6-Flash | 75 | 120,000 | 153.5 | 452.4 | 695.6 | hybrid | 353.32 | 24.6% | layer_fixed_latency |
| MiMo-V2.6-Flash | 87 | 139,200 | 153.5 | 454.5 | 705.5 | hybrid | 353.32 | 24.9% | layer_fixed_latency |
| MiMo-V2.6-Flash | 116 | 185,600 | 153.5 | 457.8 | 721.7 | hybrid | 353.32 | 25.5% | layer_fixed_latency |
| MiMo-V2.6-Flash | 173 | 276,800 | 153.5 | 458.9 | 720.2 | hybrid | 355.51 | 25.6% | layer_fixed_latency |
| MiMo-V2.6-Flash | 231 | 369,600 | 153.5 | 459.4 | 719.2 | hybrid | 357.70 | 25.7% | layer_fixed_latency |
| MiMo-V2.6-Flash | 347 | 555,200 | 153.5 | 460.4 | 726.4 | hybrid | 359.90 | 26.1% | layer_fixed_latency |
| MiMo-V2.6-Flash | 585 | 936,000 | 153.5 | 460.6 | 719.0 | hybrid | 368.68 | 26.5% | layer_fixed_latency |
| MiMo-V2.6-Flash | 3149 | 5,038,400 | 153.5 | 461.0 | 685.0 | hybrid | 445.46 | 30.5% | layer_fixed_latency |

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
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x105 | MiMo-V2.6-Flash | 105 | pipeline | rom_package_ucie | rom_board_serdes | 47 | 1.58 us | 63,139.7 tok/s | 631,396.8 tok/s | 36 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.43 us; 11 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.15 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x64 | MiMo-V2.6-Flash | 64 | tensor | rom_package_ucie | rom_board_serdes | 192 | 66.95 us | 1,493.6 tok/s | 14,936.3 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 96 x all_reduce span 16 on rom_board_serdes (traversals 6.6) = 64.59 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x105 | MiMo-V2.6-Flash | 105 | hybrid | rom_package_ucie | rom_board_serdes | 122 | 5.08 us | 19,682.3 tok/s | 196,823.4 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 26 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.72 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x105 | MiMo-V2.6-Flash | 105 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | MiMo-V2.6-Flash | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 47 | 5.88 us | 17,021.2 tok/s | 170,212.3 tok/s | 47 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.88 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-tensor-x64 | MiMo-V2.6-Flash | 64 | tensor | nvlink5 | infiniband_ndr | 192 | 663.74 us | 150.7 tok/s | 1,506.6 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 431.05 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | MiMo-V2.6-Flash | 1 | tensor | on_wafer_n5 | rom_wafer_serdes | 96 | 184.80 us | 541.1 tok/s | 5,411.3 tok/s | 96 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 184.80 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hybrid-x70 | MiMo-V2.6-Flash | 70 | hybrid | nvlink5 | infiniband_ndr | 104 | 250.24 us | 399.6 tok/s | 3,996.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.55 us |
| MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | MiMo-V2.6-Flash | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 97 | 184.90 us | 540.8 tok/s | 5,408.3 tok/s | 96 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 184.80 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109 | MiMo-V2.6-Flash | 109 | pipeline | on_wafer_n5 | rom_wafer_serdes | 47 | 5.88 us | 17,021.2 tok/s | 170,212.3 tok/s | 47 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.88 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-tensor-x109 | MiMo-V2.6-Flash | 109 | tensor | on_wafer_n5 | rom_wafer_serdes | 192 | 396.39 us | 252.3 tok/s | 2,522.8 tok/s | 96 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 184.80 us; 96 x all_reduce span 109 on rom_wafer_serdes (traversals 22.0) = 211.59 us |
| MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | MiMo-V2.6-Flash | 109 | hybrid | on_wafer_n5 | rom_wafer_serdes | 143 | 189.56 us | 527.5 tok/s | 5,275.3 tok/s | 96 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 184.80 us; 47 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 4.76 us |
| MiMo-V2.6-Flash/b200_sxm-x13-pipeline | MiMo-V2.6-Flash | 13 | pipeline | nvlink5 | infiniband_ndr | 12 | 15.49 us | 6,454.1 tok/s | 64,541.3 tok/s | 11 x point_to_point span 2 on nvlink5 (traversals 1.0) = 13.30 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x13-tensor | MiMo-V2.6-Flash | 13 | tensor | nvlink5 | infiniband_ndr | 192 | 646.05 us | 154.8 tok/s | 1,547.9 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 413.35 us |
| MiMo-V2.6-Flash/b200_sxm-x13-hybrid | MiMo-V2.6-Flash | 13 | hybrid | nvlink5 | infiniband_ndr | 97 | 234.89 us | 425.7 tok/s | 4,257.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x13-nvl72-tensor | MiMo-V2.6-Flash | 13 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.82 us | 429.5 tok/s | 4,295.2 tok/s | 96 x all_reduce span 13 on nvlink5_nvl72 (traversals 2.0) = 232.82 us |
| MiMo-V2.6-Flash/b200_sxm-x13-expert | MiMo-V2.6-Flash | 13 | expert | nvlink5 | infiniband_ndr | 192 | 437.25 us | 228.7 tok/s | 2,287.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 204.56 us |
| MiMo-V2.6-Flash/b200_sxm-x13-nvl72-expert | MiMo-V2.6-Flash | 13 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.56 us | 286.9 tok/s | 2,869.0 tok/s | 96 x all_reduce span 13 on nvlink5_nvl72 (traversals 2.0) = 232.82 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.74 us |
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
| MiMo-V2.6-Flash/b200_sxm-x22-pipeline | MiMo-V2.6-Flash | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 27.36 us | 3,654.9 tok/s | 36,548.9 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 22.97 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x22-tensor | MiMo-V2.6-Flash | 22 | tensor | nvlink5 | infiniband_ndr | 192 | 653.91 us | 152.9 tok/s | 1,529.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 421.22 us |
| MiMo-V2.6-Flash/b200_sxm-x22-hybrid | MiMo-V2.6-Flash | 22 | hybrid | nvlink5 | infiniband_ndr | 98 | 237.08 us | 421.8 tok/s | 4,218.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| MiMo-V2.6-Flash/b200_sxm-x22-nvl72-tensor | MiMo-V2.6-Flash | 22 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.90 us | 429.4 tok/s | 4,293.6 tok/s | 96 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 232.90 us |
| MiMo-V2.6-Flash/b200_sxm-x22-expert | MiMo-V2.6-Flash | 22 | expert | nvlink5 | infiniband_ndr | 192 | 432.15 us | 231.4 tok/s | 2,314.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.55 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 200.60 us |
| MiMo-V2.6-Flash/b200_sxm-x22-nvl72-expert | MiMo-V2.6-Flash | 22 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.42 us | 287.0 tok/s | 2,870.1 tok/s | 96 x all_reduce span 22 on nvlink5_nvl72 (traversals 2.0) = 232.90 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.52 us |
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
| MiMo-V2.6-Flash/b200_sxm-x28-pipeline | MiMo-V2.6-Flash | 28 | pipeline | nvlink5 | infiniband_ndr | 27 | 35.60 us | 2,809.0 tok/s | 28,089.9 tok/s | 24 x point_to_point span 2 on nvlink5 (traversals 1.0) = 29.02 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x28-tensor | MiMo-V2.6-Flash | 28 | tensor | nvlink5 | infiniband_ndr | 192 | 657.84 us | 152.0 tok/s | 1,520.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/b200_sxm-x28-hybrid | MiMo-V2.6-Flash | 28 | hybrid | nvlink5 | infiniband_ndr | 99 | 239.28 us | 417.9 tok/s | 4,179.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x28-nvl72-tensor | MiMo-V2.6-Flash | 28 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.93 us | 429.3 tok/s | 4,293.2 tok/s | 96 x all_reduce span 28 on nvlink5_nvl72 (traversals 2.0) = 232.93 us |
| MiMo-V2.6-Flash/b200_sxm-x28-expert | MiMo-V2.6-Flash | 28 | expert | nvlink5 | infiniband_ndr | 192 | 430.54 us | 232.3 tok/s | 2,322.7 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.16 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 199.37 us |
| MiMo-V2.6-Flash/b200_sxm-x28-nvl72-expert | MiMo-V2.6-Flash | 28 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.38 us | 287.0 tok/s | 2,870.4 tok/s | 96 x all_reduce span 28 on nvlink5_nvl72 (traversals 2.0) = 232.93 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.45 us |
| MiMo-V2.6-Flash/b200_sxm-x29-pipeline | MiMo-V2.6-Flash | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x29-tensor | MiMo-V2.6-Flash | 29 | tensor | nvlink5 | infiniband_ndr | 192 | 657.84 us | 152.0 tok/s | 1,520.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 425.15 us |
| MiMo-V2.6-Flash/b200_sxm-x29-hybrid | MiMo-V2.6-Flash | 29 | hybrid | nvlink5 | infiniband_ndr | 99 | 239.28 us | 417.9 tok/s | 4,179.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| MiMo-V2.6-Flash/b200_sxm-x29-nvl72-tensor | MiMo-V2.6-Flash | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.93 us | 429.3 tok/s | 4,293.1 tok/s | 96 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 232.93 us |
| MiMo-V2.6-Flash/b200_sxm-x29-expert | MiMo-V2.6-Flash | 29 | expert | nvlink5 | infiniband_ndr | 192 | 430.38 us | 232.4 tok/s | 2,323.5 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 231.16 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 199.22 us |
| MiMo-V2.6-Flash/b200_sxm-x29-nvl72-expert | MiMo-V2.6-Flash | 29 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.37 us | 287.0 tok/s | 2,870.5 tok/s | 96 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 232.93 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.44 us |
| MiMo-V2.6-Flash/b200_sxm-x33-pipeline | MiMo-V2.6-Flash | 33 | pipeline | nvlink5 | infiniband_ndr | 32 | 42.63 us | 2,345.8 tok/s | 23,457.5 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.85 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| MiMo-V2.6-Flash/b200_sxm-x33-tensor | MiMo-V2.6-Flash | 33 | tensor | nvlink5 | infiniband_ndr | 192 | 660.20 us | 151.5 tok/s | 1,514.7 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 427.51 us |
| MiMo-V2.6-Flash/b200_sxm-x33-hybrid | MiMo-V2.6-Flash | 33 | hybrid | nvlink5 | infiniband_ndr | 100 | 241.47 us | 414.1 tok/s | 4,141.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| MiMo-V2.6-Flash/b200_sxm-x33-nvl72-tensor | MiMo-V2.6-Flash | 33 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.94 us | 429.3 tok/s | 4,292.9 tok/s | 96 x all_reduce span 33 on nvlink5_nvl72 (traversals 2.0) = 232.94 us |
| MiMo-V2.6-Flash/b200_sxm-x33-expert | MiMo-V2.6-Flash | 33 | expert | nvlink5 | infiniband_ndr | 192 | 429.67 us | 232.7 tok/s | 2,327.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.97 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 198.69 us |
| MiMo-V2.6-Flash/b200_sxm-x33-nvl72-expert | MiMo-V2.6-Flash | 33 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.35 us | 287.1 tok/s | 2,870.6 tok/s | 96 x all_reduce span 33 on nvlink5_nvl72 (traversals 2.0) = 232.94 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.41 us |
| MiMo-V2.6-Flash/b200_sxm-x36-pipeline | MiMo-V2.6-Flash | 36 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| MiMo-V2.6-Flash/b200_sxm-x36-tensor | MiMo-V2.6-Flash | 36 | tensor | nvlink5 | infiniband_ndr | 192 | 660.20 us | 151.5 tok/s | 1,514.7 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 427.51 us |
| MiMo-V2.6-Flash/b200_sxm-x36-hybrid | MiMo-V2.6-Flash | 36 | hybrid | nvlink5 | infiniband_ndr | 100 | 241.47 us | 414.1 tok/s | 4,141.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| MiMo-V2.6-Flash/b200_sxm-x36-nvl72-tensor | MiMo-V2.6-Flash | 36 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.95 us | 429.3 tok/s | 4,292.8 tok/s | 96 x all_reduce span 36 on nvlink5_nvl72 (traversals 2.0) = 232.95 us |
| MiMo-V2.6-Flash/b200_sxm-x36-expert | MiMo-V2.6-Flash | 36 | expert | nvlink5 | infiniband_ndr | 192 | 429.35 us | 232.9 tok/s | 2,329.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.97 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 198.38 us |
| MiMo-V2.6-Flash/b200_sxm-x36-nvl72-expert | MiMo-V2.6-Flash | 36 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.34 us | 287.1 tok/s | 2,870.7 tok/s | 96 x all_reduce span 36 on nvlink5_nvl72 (traversals 2.0) = 232.95 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.39 us |
| MiMo-V2.6-Flash/b200_sxm-x38-pipeline | MiMo-V2.6-Flash | 38 | pipeline | nvlink5 | infiniband_ndr | 37 | 48.68 us | 2,054.4 tok/s | 20,544.1 tok/s | 33 x point_to_point span 2 on nvlink5 (traversals 1.0) = 39.90 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| MiMo-V2.6-Flash/b200_sxm-x38-tensor | MiMo-V2.6-Flash | 38 | tensor | nvlink5 | infiniband_ndr | 192 | 660.20 us | 151.5 tok/s | 1,514.7 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 427.51 us |
| MiMo-V2.6-Flash/b200_sxm-x38-hybrid | MiMo-V2.6-Flash | 38 | hybrid | nvlink5 | infiniband_ndr | 100 | 241.47 us | 414.1 tok/s | 4,141.3 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| MiMo-V2.6-Flash/b200_sxm-x38-nvl72-tensor | MiMo-V2.6-Flash | 38 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.95 us | 429.3 tok/s | 4,292.7 tok/s | 96 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 232.95 us |
| MiMo-V2.6-Flash/b200_sxm-x38-expert | MiMo-V2.6-Flash | 38 | expert | nvlink5 | infiniband_ndr | 192 | 429.16 us | 233.0 tok/s | 2,330.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.97 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 198.19 us |
| MiMo-V2.6-Flash/b200_sxm-x38-nvl72-expert | MiMo-V2.6-Flash | 38 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.34 us | 287.1 tok/s | 2,870.8 tok/s | 96 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 232.95 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.38 us |
| MiMo-V2.6-Flash/b200_sxm-x51-pipeline | MiMo-V2.6-Flash | 51 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x51-tensor | MiMo-V2.6-Flash | 51 | tensor | nvlink5 | infiniband_ndr | 192 | 662.90 us | 150.9 tok/s | 1,508.5 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 430.21 us |
| MiMo-V2.6-Flash/b200_sxm-x51-hybrid | MiMo-V2.6-Flash | 51 | hybrid | nvlink5 | infiniband_ndr | 102 | 245.86 us | 406.7 tok/s | 4,067.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| MiMo-V2.6-Flash/b200_sxm-x51-nvl72-tensor | MiMo-V2.6-Flash | 51 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.97 us | 429.2 tok/s | 4,292.4 tok/s | 96 x all_reduce span 51 on nvlink5_nvl72 (traversals 2.0) = 232.97 us |
| MiMo-V2.6-Flash/b200_sxm-x51-expert | MiMo-V2.6-Flash | 51 | expert | nvlink5 | infiniband_ndr | 192 | 428.13 us | 233.6 tok/s | 2,335.7 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.78 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 197.35 us |
| MiMo-V2.6-Flash/b200_sxm-x51-nvl72-expert | MiMo-V2.6-Flash | 51 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.31 us | 287.1 tok/s | 2,871.0 tok/s | 96 x all_reduce span 51 on nvlink5_nvl72 (traversals 2.0) = 232.97 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.34 us |
| MiMo-V2.6-Flash/b200_sxm-x53-pipeline | MiMo-V2.6-Flash | 53 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x53-tensor | MiMo-V2.6-Flash | 53 | tensor | nvlink5 | infiniband_ndr | 192 | 662.90 us | 150.9 tok/s | 1,508.5 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 430.21 us |
| MiMo-V2.6-Flash/b200_sxm-x53-hybrid | MiMo-V2.6-Flash | 53 | hybrid | nvlink5 | infiniband_ndr | 102 | 245.86 us | 406.7 tok/s | 4,067.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.16 us |
| MiMo-V2.6-Flash/b200_sxm-x53-nvl72-tensor | MiMo-V2.6-Flash | 53 | tensor | nvlink5_nvl72 | infiniband_ndr | 96 | 232.97 us | 429.2 tok/s | 4,292.4 tok/s | 96 x all_reduce span 53 on nvlink5_nvl72 (traversals 2.0) = 232.97 us |
| MiMo-V2.6-Flash/b200_sxm-x53-expert | MiMo-V2.6-Flash | 53 | expert | nvlink5 | infiniband_ndr | 192 | 428.04 us | 233.6 tok/s | 2,336.2 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.78 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 197.25 us |
| MiMo-V2.6-Flash/b200_sxm-x53-nvl72-expert | MiMo-V2.6-Flash | 53 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 348.30 us | 287.1 tok/s | 2,871.1 tok/s | 96 x all_reduce span 53 on nvlink5_nvl72 (traversals 2.0) = 232.97 us; 96 x point_to_point span 2 on nvlink5_nvl72 (traversals 1.0) = 115.33 us |
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
| MiMo-V2.6-Flash/b200_sxm-x75-pipeline | MiMo-V2.6-Flash | 75 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x75-tensor | MiMo-V2.6-Flash | 75 | tensor | nvlink5 | infiniband_ndr | 192 | 664.92 us | 150.4 tok/s | 1,503.9 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 432.23 us |
| MiMo-V2.6-Flash/b200_sxm-x75-hybrid | MiMo-V2.6-Flash | 75 | hybrid | nvlink5 | infiniband_ndr | 105 | 252.44 us | 396.1 tok/s | 3,961.4 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.74 us |
| MiMo-V2.6-Flash/b200_sxm-x75-nvl72-tensor | MiMo-V2.6-Flash | 75 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 646.34 us | 154.7 tok/s | 1,547.2 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 413.35 us |
| MiMo-V2.6-Flash/b200_sxm-x75-nvl72-hybrid | MiMo-V2.6-Flash | 75 | hybrid | nvlink5_nvl72 | infiniband_ndr | 97 | 235.18 us | 425.2 tok/s | 4,252.1 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| MiMo-V2.6-Flash/b200_sxm-x75-expert | MiMo-V2.6-Flash | 75 | expert | nvlink5 | infiniband_ndr | 192 | 427.21 us | 234.1 tok/s | 2,340.8 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.65 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 196.56 us |
| MiMo-V2.6-Flash/b200_sxm-x75-nvl72-expert | MiMo-V2.6-Flash | 75 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 429.54 us | 232.8 tok/s | 2,328.1 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 196.56 us |
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
| MiMo-V2.6-Flash/b200_sxm-x585-pipeline | MiMo-V2.6-Flash | 585 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x585-tensor | MiMo-V2.6-Flash | 585 | tensor | nvlink5 | infiniband_ndr | 192 | 1,058.76 us | 94.4 tok/s | 944.5 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 74 on infiniband_ndr (traversals 4.0) = 826.07 us |
| MiMo-V2.6-Flash/b200_sxm-x585-hybrid | MiMo-V2.6-Flash | 585 | hybrid | nvlink5 | infiniband_ndr | 143 | 335.80 us | 297.8 tok/s | 2,977.9 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 47 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 103.11 us |
| MiMo-V2.6-Flash/b200_sxm-x585-nvl72-tensor | MiMo-V2.6-Flash | 585 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 664.69 us | 150.4 tok/s | 1,504.5 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 431.70 us |
| MiMo-V2.6-Flash/b200_sxm-x585-nvl72-hybrid | MiMo-V2.6-Flash | 585 | hybrid | nvlink5_nvl72 | infiniband_ndr | 104 | 250.54 us | 399.1 tok/s | 3,991.4 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.55 us |
| MiMo-V2.6-Flash/b200_sxm-x585-expert | MiMo-V2.6-Flash | 585 | expert | nvlink5 | infiniband_ndr | 192 | 425.53 us | 235.0 tok/s | 2,350.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.43 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.10 us |
| MiMo-V2.6-Flash/b200_sxm-x585-nvl72-expert | MiMo-V2.6-Flash | 585 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 425.82 us | 234.8 tok/s | 2,348.4 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 230.72 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.10 us |
| MiMo-V2.6-Flash/b200_sxm-x3149-pipeline | MiMo-V2.6-Flash | 3149 | pipeline | nvlink5 | infiniband_ndr | 47 | 61.75 us | 1,619.4 tok/s | 16,193.9 tok/s | 42 x point_to_point span 2 on nvlink5 (traversals 1.0) = 50.78 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| MiMo-V2.6-Flash/b200_sxm-x3149-tensor | MiMo-V2.6-Flash | 3149 | tensor | nvlink5 | infiniband_ndr | 192 | 1,059.28 us | 94.4 tok/s | 944.0 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 96 x all_reduce span 394 on infiniband_ndr (traversals 4.0) = 826.59 us |
| MiMo-V2.6-Flash/b200_sxm-x3149-hybrid | MiMo-V2.6-Flash | 3149 | hybrid | nvlink5 | infiniband_ndr | 143 | 335.80 us | 297.8 tok/s | 2,977.9 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 232.69 us; 47 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 103.11 us |
| MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-tensor | MiMo-V2.6-Flash | 3149 | tensor | nvlink5_nvl72 | infiniband_ndr | 192 | 668.86 us | 149.5 tok/s | 1,495.1 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 96 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 435.87 us |
| MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-hybrid | MiMo-V2.6-Flash | 3149 | hybrid | nvlink5_nvl72 | infiniband_ndr | 139 | 327.32 us | 305.5 tok/s | 3,055.1 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 232.99 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 94.34 us |
| MiMo-V2.6-Flash/b200_sxm-x3149-expert | MiMo-V2.6-Flash | 3149 | expert | nvlink5 | infiniband_ndr | 192 | 425.33 us | 235.1 tok/s | 2,351.1 tok/s | 96 x all_reduce span 8 on nvlink5 (traversals 2.0) = 230.41 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 194.92 us |
| MiMo-V2.6-Flash/b200_sxm-x3149-nvl72-expert | MiMo-V2.6-Flash | 3149 | expert | nvlink5_nvl72 | infiniband_ndr | 192 | 425.38 us | 235.1 tok/s | 2,350.8 tok/s | 96 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 230.46 us; 96 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 194.92 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Flash | 1 | array | array | MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x105 | 85,575 | 4,383.4 | 0.051 | 4,383.4 (85,575) | 3,406.7 (92,450) | 0.78x | layer_fixed_latency |
| MiMo-V2.6-Flash | 2 | wafer | wafer | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1,382.5 | 0.000 | — (—) | 1,382.5 (5,038,525) | — | link_latency |
| MiMo-V2.6-Flash | 4 | wafer | wafer | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1,382.5 | 0.000 | — (—) | 1,382.5 (5,038,525) | — | link_latency |
| MiMo-V2.6-Flash | 8 | wafer | wafer | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1,382.5 | 0.000 | — (—) | 1,382.5 (5,038,525) | — | link_latency |
| MiMo-V2.6-Flash | 16 | wafer | wafer | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1,382.5 | 0.000 | — (—) | 1,382.5 (5,038,525) | — | link_latency |
| MiMo-V2.6-Flash | 32 | wafer | wafer | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1,332.1 | 0.000 | — (—) | 1,332.1 (5,038,525) | — | link_latency |
| MiMo-V2.6-Flash | 64 | wafer | wafer | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1,073.9 | 0.000 | — (—) | 1,073.9 (5,038,525) | — | link_latency |
| MiMo-V2.6-Flash | 256 | wafer | wafer | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 543.8 | 0.000 | — (—) | 543.8 (5,038,525) | — | kv_read |
| MiMo-V2.6-Flash | 1024 | wafer | wafer | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 156.3 | 0.000 | — (—) | 156.3 (5,038,525) | — | kv_read |
| MiMo-V2.6-Flash | 4096 | wafer | wafer | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 40.0 | 0.000 | — (—) | 40.0 (5,038,525) | — | kv_read |

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
| MiMo-V2.6-Flash | 1 | sram | 109,221.5 | 17,365.7 | 17,365.7 | 6.29x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 2 | sram | 109,221.5 | 17,365.7 | 17,365.7 | 6.29x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 4 | sram | 109,221.5 | 17,365.7 | 17,365.7 | 6.29x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 8 | sram | 109,221.5 | 17,365.7 | 17,365.7 | 6.29x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 16 | sram | 109,221.5 | 17,365.7 | 17,365.7 | 6.29x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 32 | sram | 109,221.5 | 18,010.0 | 21,489.5 | 6.06x | 1.19x | kv_read | weight_read | link_latency |
| MiMo-V2.6-Flash | 64 | sram | 109,221.5 | 21,412.9 | 32,702.8 | 5.10x | 1.53x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 256 | sram | 139,220.6 | 25,381.4 | 79,036.1 | 5.49x | 3.11x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 1024 | sram | 160,009.0 | 25,992.5 | 148,024.2 | 6.16x | 5.69x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 4096 | sram | 163,819.3 | 26,090.8 | 161,916.2 | 6.28x | 6.21x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 1 | rom | 109,192.2 | 109,147.8 | 109,147.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 2 | rom | 109,192.2 | 109,147.8 | 109,147.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 4 | rom | 109,192.2 | 109,147.8 | 109,147.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 8 | rom | 109,192.2 | 109,147.8 | 109,147.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 16 | rom | 109,192.2 | 109,147.8 | 109,147.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 32 | rom | 109,192.2 | 109,147.8 | 109,147.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 64 | rom | 109,192.2 | 109,147.8 | 109,147.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 256 | rom | 137,459.5 | 138,508.2 | 138,340.2 | 0.99x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 1024 | rom | 159,691.2 | 159,800.2 | 159,796.3 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 4096 | rom | 163,749.4 | 163,693.4 | 163,689.2 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| MiMo-V2.6-Flash | 1 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109 | 5,038,525 | 1.00 | 1.00 | 109,221.5 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-romfill | 5,038,525 | 128.23 | 1.00 | 109,192.2 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream | 5,038,525 | 1.00 | 1.00 | 17,365.7 | 0.003 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 1 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perregion | 5,038,525 | 1.00 | 1.00 | 17,365.7 | 0.003 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 1 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perregion-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 2 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109 | 5,038,525 | 1.00 | 1.00 | 109,221.5 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 2 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-romfill | 5,038,525 | 128.23 | 1.00 | 109,192.2 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 2 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream | 5,038,525 | 1.00 | 1.00 | 17,365.7 | 0.003 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 2 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 2 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perregion | 5,038,525 | 1.00 | 1.00 | 17,365.7 | 0.003 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 2 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perregion-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109 | 5,038,525 | 1.00 | 1.00 | 109,221.5 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-romfill | 5,038,525 | 128.23 | 1.00 | 109,192.2 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream | 5,038,525 | 1.00 | 1.00 | 17,365.7 | 0.003 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 4 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perregion | 5,038,525 | 1.00 | 1.00 | 17,365.7 | 0.003 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 4 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perregion-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 8 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109 | 5,038,525 | 1.00 | 1.00 | 109,221.5 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 8 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-romfill | 5,038,525 | 128.23 | 1.00 | 109,192.2 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 8 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream | 5,038,525 | 1.00 | 1.00 | 17,365.7 | 0.003 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 8 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 8 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perregion | 5,038,525 | 1.00 | 1.00 | 17,365.7 | 0.003 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 8 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perregion-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 16 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109 | 5,038,525 | 1.00 | 1.00 | 109,221.5 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 16 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-romfill | 5,038,525 | 128.23 | 1.00 | 109,192.2 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 16 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream | 5,038,525 | 1.00 | 1.00 | 17,365.7 | 0.003 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 16 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 16 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perregion | 5,038,525 | 1.00 | 1.00 | 17,365.7 | 0.003 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 16 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perregion-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 32 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109 | 5,038,525 | 1.00 | 1.00 | 109,221.5 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 32 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-romfill | 5,038,525 | 128.23 | 1.00 | 109,192.2 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 32 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perstream | 5,038,525 | 1.00 | 1.14 | 18,010.0 | 0.004 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 32 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 32 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-tensor-x109-perregion | 5,038,525 | 1.00 | 4.64 | 21,489.5 | 0.004 | link_latency | 0.20x |
| MiMo-V2.6-Flash | 32 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perregion-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 64 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109 | 5,038,525 | 1.00 | 1.00 | 109,221.5 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 64 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-romfill | 5,038,525 | 128.23 | 1.00 | 109,192.2 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 64 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perstream | 5,038,525 | 1.00 | 1.16 | 21,412.9 | 0.004 | weight_read | 0.20x |
| MiMo-V2.6-Flash | 64 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perstream-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 64 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perregion | 5,038,525 | 1.00 | 1.31 | 32,702.8 | 0.006 | weight_read | 0.30x |
| MiMo-V2.6-Flash | 64 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x109-perregion-romfill | 5,038,525 | 430.91 | 1.00 | 109,147.8 | 0.022 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 256 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1.00 | 1.00 | 139,220.6 | 0.028 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 256 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-romfill | 5,038,525 | 128.23 | 1.00 | 137,459.5 | 0.027 | kv_read | 0.99x |
| MiMo-V2.6-Flash | 256 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perstream | 5,038,525 | 1.00 | 1.32 | 25,381.4 | 0.005 | weight_read | 0.18x |
| MiMo-V2.6-Flash | 256 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perstream-romfill | 5,038,525 | 430.91 | 1.32 | 138,508.2 | 0.027 | kv_read | 0.99x |
| MiMo-V2.6-Flash | 256 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perregion | 5,038,525 | 1.00 | 2.48 | 79,036.1 | 0.016 | weight_read | 0.57x |
| MiMo-V2.6-Flash | 256 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perregion-romfill | 5,038,525 | 430.91 | 1.07 | 138,340.2 | 0.027 | kv_read | 0.99x |
| MiMo-V2.6-Flash | 1024 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1.00 | 1.00 | 160,009.0 | 0.032 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1024 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-romfill | 5,038,525 | 128.23 | 1.00 | 159,691.2 | 0.032 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1024 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perstream | 5,038,525 | 1.00 | 1.32 | 25,992.5 | 0.005 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 1024 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perstream-romfill | 5,038,525 | 430.91 | 1.32 | 159,800.2 | 0.032 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1024 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perregion | 5,038,525 | 1.00 | 4.98 | 148,024.2 | 0.029 | kv_read | 0.93x |
| MiMo-V2.6-Flash | 1024 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perregion-romfill | 5,038,525 | 430.91 | 1.07 | 159,796.3 | 0.032 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4096 | batched | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109 | 5,038,525 | 1.00 | 1.00 | 163,819.3 | 0.033 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4096 | batched | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-romfill | 5,038,525 | 128.23 | 1.00 | 163,749.4 | 0.032 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4096 | per_stream | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perstream | 5,038,525 | 1.00 | 1.32 | 26,090.8 | 0.005 | weight_read | 0.16x |
| MiMo-V2.6-Flash | 4096 | per_stream | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perstream-romfill | 5,038,525 | 430.91 | 1.32 | 163,693.4 | 0.032 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4096 | per_region | sram | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perregion | 5,038,525 | 1.00 | 5.06 | 161,916.2 | 0.032 | kv_read | 0.99x |
| MiMo-V2.6-Flash | 4096 | per_region | rom | MiMo-V2.6-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x109-perregion-romfill | 5,038,525 | 430.91 | 1.07 | 163,689.2 | 0.032 | kv_read | 1.00x |

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
| MiMo-V2.6-Flash | 1 | 26 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 4 | 6,183 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 8 | 6,183 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 16 | 6,183 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 32 | 6,183 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 64 | 6,183 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 256 | 6,183 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 1024 | 6,183 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 4096 | 6,183 | 1.00 | 1.000 | 1.000 | 1.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Flash | 1 | 13 | 6.15 | 3.88 | 1.58x |
| MiMo-V2.6-Flash | 2 | 13 | 9.31 | 4.94 | 1.88x |
| MiMo-V2.6-Flash | 4 | 13 | 11.87 | 6.07 | 1.96x |
| MiMo-V2.6-Flash | 8 | 13 | 12.87 | 7.15 | 1.80x |
| MiMo-V2.6-Flash | 16 | 13 | 13.00 | 8.10 | 1.60x |
| MiMo-V2.6-Flash | 32 | 13 | 13.00 | 8.82 | 1.47x |
| MiMo-V2.6-Flash | 64 | 13 | 13.00 | 9.27 | 1.40x |
| MiMo-V2.6-Flash | 1 | 16 | 6.45 | 4.14 | 1.56x |
| MiMo-V2.6-Flash | 2 | 16 | 10.21 | 5.38 | 1.90x |
| MiMo-V2.6-Flash | 4 | 16 | 13.77 | 6.72 | 2.05x |
| MiMo-V2.6-Flash | 8 | 16 | 15.61 | 8.07 | 1.93x |
| MiMo-V2.6-Flash | 16 | 16 | 15.98 | 9.28 | 1.72x |
| MiMo-V2.6-Flash | 32 | 16 | 16.00 | 10.22 | 1.57x |
| MiMo-V2.6-Flash | 64 | 16 | 16.00 | 10.80 | 1.48x |
| MiMo-V2.6-Flash | 1 | 17 | 6.53 | 4.22 | 1.55x |
| MiMo-V2.6-Flash | 2 | 17 | 10.46 | 5.50 | 1.90x |
| MiMo-V2.6-Flash | 4 | 17 | 14.33 | 6.92 | 2.07x |
| MiMo-V2.6-Flash | 8 | 17 | 16.48 | 8.35 | 1.97x |
| MiMo-V2.6-Flash | 16 | 17 | 16.96 | 9.64 | 1.76x |
| MiMo-V2.6-Flash | 32 | 17 | 17.00 | 10.65 | 1.60x |
| MiMo-V2.6-Flash | 64 | 17 | 17.00 | 11.28 | 1.51x |
| MiMo-V2.6-Flash | 1 | 22 | 6.84 | 4.54 | 1.51x |
| MiMo-V2.6-Flash | 2 | 22 | 11.43 | 6.05 | 1.89x |
| MiMo-V2.6-Flash | 4 | 22 | 16.68 | 7.78 | 2.14x |
| MiMo-V2.6-Flash | 8 | 22 | 20.48 | 9.60 | 2.13x |
| MiMo-V2.6-Flash | 16 | 22 | 21.81 | 11.29 | 1.93x |
| MiMo-V2.6-Flash | 32 | 22 | 21.99 | 12.66 | 1.74x |
| MiMo-V2.6-Flash | 64 | 22 | 22.00 | 13.53 | 1.63x |
| MiMo-V2.6-Flash | 1 | 23 | 6.88 | 4.60 | 1.50x |
| MiMo-V2.6-Flash | 2 | 23 | 11.58 | 6.14 | 1.88x |
| MiMo-V2.6-Flash | 4 | 23 | 17.08 | 7.94 | 2.15x |
| MiMo-V2.6-Flash | 8 | 23 | 21.21 | 9.82 | 2.16x |
| MiMo-V2.6-Flash | 16 | 23 | 22.75 | 11.60 | 1.96x |
| MiMo-V2.6-Flash | 32 | 23 | 22.98 | 13.04 | 1.76x |
| MiMo-V2.6-Flash | 64 | 23 | 23.00 | 13.95 | 1.65x |
| MiMo-V2.6-Flash | 1 | 24 | 6.93 | 4.65 | 1.49x |
| MiMo-V2.6-Flash | 2 | 24 | 11.72 | 6.23 | 1.88x |
| MiMo-V2.6-Flash | 4 | 24 | 17.46 | 8.08 | 2.16x |
| MiMo-V2.6-Flash | 8 | 24 | 21.92 | 10.04 | 2.18x |
| MiMo-V2.6-Flash | 16 | 24 | 23.69 | 11.89 | 1.99x |
| MiMo-V2.6-Flash | 32 | 24 | 23.98 | 13.40 | 1.79x |
| MiMo-V2.6-Flash | 64 | 24 | 24.00 | 14.36 | 1.67x |
| MiMo-V2.6-Flash | 1 | 28 | 7.07 | 4.85 | 1.46x |
| MiMo-V2.6-Flash | 2 | 28 | 12.21 | 6.56 | 1.86x |
| MiMo-V2.6-Flash | 4 | 28 | 18.78 | 8.62 | 2.18x |
| MiMo-V2.6-Flash | 8 | 28 | 24.53 | 10.85 | 2.26x |
| MiMo-V2.6-Flash | 16 | 28 | 27.31 | 12.99 | 2.10x |
| MiMo-V2.6-Flash | 32 | 28 | 27.93 | 14.77 | 1.89x |
| MiMo-V2.6-Flash | 64 | 28 | 27.99 | 15.92 | 1.76x |
| MiMo-V2.6-Flash | 1 | 29 | 7.10 | 4.90 | 1.45x |
| MiMo-V2.6-Flash | 2 | 29 | 12.31 | 6.63 | 1.86x |
| MiMo-V2.6-Flash | 4 | 29 | 19.07 | 8.74 | 2.18x |
| MiMo-V2.6-Flash | 8 | 29 | 25.13 | 11.03 | 2.28x |
| MiMo-V2.6-Flash | 16 | 29 | 28.19 | 13.25 | 2.13x |
| MiMo-V2.6-Flash | 32 | 29 | 28.91 | 15.10 | 1.91x |
| MiMo-V2.6-Flash | 64 | 29 | 28.99 | 16.29 | 1.78x |
| MiMo-V2.6-Flash | 1 | 33 | 7.20 | 5.07 | 1.42x |
| MiMo-V2.6-Flash | 2 | 33 | 12.67 | 6.90 | 1.84x |
| MiMo-V2.6-Flash | 4 | 33 | 20.10 | 9.20 | 2.18x |
| MiMo-V2.6-Flash | 8 | 33 | 27.36 | 11.74 | 2.33x |
| MiMo-V2.6-Flash | 16 | 33 | 31.57 | 14.23 | 2.22x |
| MiMo-V2.6-Flash | 32 | 33 | 32.78 | 16.34 | 2.01x |
| MiMo-V2.6-Flash | 64 | 33 | 32.96 | 17.71 | 1.86x |
| MiMo-V2.6-Flash | 1 | 36 | 7.26 | 5.18 | 1.40x |
| MiMo-V2.6-Flash | 2 | 36 | 12.90 | 7.08 | 1.82x |
| MiMo-V2.6-Flash | 4 | 36 | 20.77 | 9.52 | 2.18x |
| MiMo-V2.6-Flash | 8 | 36 | 28.86 | 12.22 | 2.36x |
| MiMo-V2.6-Flash | 16 | 36 | 33.96 | 14.92 | 2.28x |
| MiMo-V2.6-Flash | 32 | 36 | 35.64 | 17.21 | 2.07x |
| MiMo-V2.6-Flash | 64 | 36 | 35.93 | 18.72 | 1.92x |
| MiMo-V2.6-Flash | 1 | 38 | 7.30 | 5.25 | 1.39x |
| MiMo-V2.6-Flash | 2 | 38 | 13.03 | 7.19 | 1.81x |
| MiMo-V2.6-Flash | 4 | 38 | 21.17 | 9.71 | 2.18x |
| MiMo-V2.6-Flash | 8 | 38 | 29.78 | 12.53 | 2.38x |
| MiMo-V2.6-Flash | 16 | 38 | 35.49 | 15.35 | 2.31x |
| MiMo-V2.6-Flash | 32 | 38 | 37.51 | 17.76 | 2.11x |
| MiMo-V2.6-Flash | 64 | 38 | 37.90 | 19.36 | 1.96x |
| MiMo-V2.6-Flash | 256 | 38 | 37.96 | 20.08 | 1.89x |
| MiMo-V2.6-Flash | 1 | 51 | 7.47 | 5.64 | 1.33x |
| MiMo-V2.6-Flash | 2 | 51 | 13.66 | 7.78 | 1.76x |
| MiMo-V2.6-Flash | 4 | 51 | 23.14 | 10.81 | 2.14x |
| MiMo-V2.6-Flash | 8 | 51 | 34.64 | 14.24 | 2.43x |
| MiMo-V2.6-Flash | 16 | 51 | 44.23 | 17.81 | 2.48x |
| MiMo-V2.6-Flash | 32 | 51 | 48.99 | 20.97 | 2.34x |
| MiMo-V2.6-Flash | 64 | 51 | 50.38 | 23.11 | 2.18x |
| MiMo-V2.6-Flash | 256 | 51 | 50.68 | 24.08 | 2.10x |
| MiMo-V2.6-Flash | 1 | 53 | 7.49 | 5.69 | 1.32x |
| MiMo-V2.6-Flash | 2 | 53 | 13.74 | 7.86 | 1.75x |
| MiMo-V2.6-Flash | 4 | 53 | 23.37 | 10.96 | 2.13x |
| MiMo-V2.6-Flash | 8 | 53 | 35.25 | 14.47 | 2.44x |
| MiMo-V2.6-Flash | 16 | 53 | 45.40 | 18.15 | 2.50x |
| MiMo-V2.6-Flash | 32 | 53 | 50.64 | 21.42 | 2.36x |
| MiMo-V2.6-Flash | 64 | 53 | 52.23 | 23.63 | 2.21x |
| MiMo-V2.6-Flash | 256 | 53 | 52.60 | 24.64 | 2.13x |
| MiMo-V2.6-Flash | 1 | 57 | 7.53 | 5.78 | 1.30x |
| MiMo-V2.6-Flash | 2 | 57 | 13.87 | 8.01 | 1.73x |
| MiMo-V2.6-Flash | 4 | 57 | 23.80 | 11.24 | 2.12x |
| MiMo-V2.6-Flash | 8 | 57 | 36.37 | 14.91 | 2.44x |
| MiMo-V2.6-Flash | 16 | 57 | 47.62 | 18.79 | 2.53x |
| MiMo-V2.6-Flash | 32 | 57 | 53.83 | 22.27 | 2.42x |
| MiMo-V2.6-Flash | 64 | 57 | 55.89 | 24.64 | 2.27x |
| MiMo-V2.6-Flash | 256 | 57 | 56.39 | 25.73 | 2.19x |
| MiMo-V2.6-Flash | 1 | 58 | 7.53 | 5.80 | 1.30x |
| MiMo-V2.6-Flash | 2 | 58 | 13.90 | 8.05 | 1.73x |
| MiMo-V2.6-Flash | 4 | 58 | 23.89 | 11.30 | 2.11x |
| MiMo-V2.6-Flash | 8 | 58 | 36.63 | 15.01 | 2.44x |
| MiMo-V2.6-Flash | 16 | 58 | 48.15 | 18.95 | 2.54x |
| MiMo-V2.6-Flash | 32 | 58 | 54.61 | 22.48 | 2.43x |
| MiMo-V2.6-Flash | 64 | 58 | 56.79 | 24.88 | 2.28x |
| MiMo-V2.6-Flash | 256 | 58 | 57.32 | 25.99 | 2.21x |
| MiMo-V2.6-Flash | 1 | 75 | 7.64 | 6.12 | 1.25x |
| MiMo-V2.6-Flash | 2 | 75 | 14.29 | 8.59 | 1.66x |
| MiMo-V2.6-Flash | 4 | 75 | 25.22 | 12.27 | 2.06x |
| MiMo-V2.6-Flash | 8 | 75 | 40.30 | 16.57 | 2.43x |
| MiMo-V2.6-Flash | 16 | 75 | 55.92 | 21.30 | 2.62x |
| MiMo-V2.6-Flash | 32 | 75 | 66.62 | 25.64 | 2.60x |
| MiMo-V2.6-Flash | 64 | 75 | 71.21 | 28.66 | 2.48x |
| MiMo-V2.6-Flash | 256 | 75 | 72.58 | 30.06 | 2.41x |
| MiMo-V2.6-Flash | 1 | 87 | 7.69 | 6.29 | 1.22x |
| MiMo-V2.6-Flash | 2 | 87 | 14.48 | 8.92 | 1.62x |
| MiMo-V2.6-Flash | 4 | 87 | 25.87 | 12.81 | 2.02x |
| MiMo-V2.6-Flash | 8 | 87 | 42.21 | 17.47 | 2.42x |
| MiMo-V2.6-Flash | 16 | 87 | 60.23 | 22.70 | 2.65x |
| MiMo-V2.6-Flash | 32 | 87 | 73.83 | 27.56 | 2.68x |
| MiMo-V2.6-Flash | 64 | 87 | 80.35 | 30.98 | 2.59x |
| MiMo-V2.6-Flash | 256 | 87 | 82.49 | 32.58 | 2.53x |
| MiMo-V2.6-Flash | 1 | 116 | 7.76 | 6.60 | 1.18x |
| MiMo-V2.6-Flash | 2 | 116 | 14.79 | 9.59 | 1.54x |
| MiMo-V2.6-Flash | 4 | 116 | 26.95 | 13.78 | 1.96x |
| MiMo-V2.6-Flash | 8 | 116 | 45.44 | 19.29 | 2.36x |
| MiMo-V2.6-Flash | 16 | 116 | 68.02 | 25.53 | 2.66x |
| MiMo-V2.6-Flash | 32 | 116 | 87.79 | 31.47 | 2.79x |
| MiMo-V2.6-Flash | 64 | 116 | 99.09 | 35.74 | 2.77x |
| MiMo-V2.6-Flash | 256 | 116 | 103.35 | 37.76 | 2.74x |
| MiMo-V2.6-Flash | 1 | 173 | 7.84 | 6.97 | 1.12x |
| MiMo-V2.6-Flash | 2 | 173 | 15.10 | 10.58 | 1.43x |
| MiMo-V2.6-Flash | 4 | 173 | 28.06 | 15.05 | 1.87x |
| MiMo-V2.6-Flash | 8 | 173 | 48.98 | 22.00 | 2.23x |
| MiMo-V2.6-Flash | 16 | 173 | 77.21 | 29.58 | 2.61x |
| MiMo-V2.6-Flash | 32 | 173 | 105.88 | 37.19 | 2.85x |
| MiMo-V2.6-Flash | 64 | 173 | 125.36 | 42.87 | 2.92x |
| MiMo-V2.6-Flash | 256 | 173 | 133.76 | 45.58 | 2.93x |
| MiMo-V2.6-Flash | 1024 | 173 | 133.78 | 45.59 | 2.93x |
| MiMo-V2.6-Flash | 1 | 231 | 7.88 | 7.19 | 1.10x |
| MiMo-V2.6-Flash | 2 | 231 | 15.26 | 11.30 | 1.35x |
| MiMo-V2.6-Flash | 4 | 231 | 28.66 | 16.00 | 1.79x |
| MiMo-V2.6-Flash | 8 | 231 | 50.94 | 23.91 | 2.13x |
| MiMo-V2.6-Flash | 16 | 231 | 82.58 | 32.43 | 2.55x |
| MiMo-V2.6-Flash | 32 | 231 | 117.26 | 41.58 | 2.82x |
| MiMo-V2.6-Flash | 64 | 231 | 143.00 | 48.35 | 2.96x |
| MiMo-V2.6-Flash | 256 | 231 | 154.89 | 51.66 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 231 | 154.92 | 51.66 | 3.00x |
| MiMo-V2.6-Flash | 1 | 347 | 7.92 | 7.43 | 1.07x |
| MiMo-V2.6-Flash | 2 | 347 | 15.42 | 12.28 | 1.26x |
| MiMo-V2.6-Flash | 4 | 347 | 29.27 | 17.53 | 1.67x |
| MiMo-V2.6-Flash | 8 | 347 | 52.99 | 26.19 | 2.02x |
| MiMo-V2.6-Flash | 16 | 347 | 88.46 | 36.85 | 2.40x |
| MiMo-V2.6-Flash | 32 | 347 | 130.41 | 47.91 | 2.72x |
| MiMo-V2.6-Flash | 64 | 347 | 164.39 | 56.35 | 2.92x |
| MiMo-V2.6-Flash | 256 | 347 | 181.21 | 60.46 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 347 | 181.25 | 60.47 | 3.00x |
| MiMo-V2.6-Flash | 1 | 585 | 7.95 | 7.65 | 1.04x |
| MiMo-V2.6-Flash | 2 | 585 | 15.55 | 13.36 | 1.16x |
| MiMo-V2.6-Flash | 4 | 585 | 29.77 | 19.85 | 1.50x |
| MiMo-V2.6-Flash | 8 | 585 | 54.74 | 28.62 | 1.91x |
| MiMo-V2.6-Flash | 16 | 585 | 93.64 | 42.92 | 2.18x |
| MiMo-V2.6-Flash | 32 | 585 | 142.60 | 55.69 | 2.56x |
| MiMo-V2.6-Flash | 64 | 585 | 185.17 | 67.02 | 2.76x |
| MiMo-V2.6-Flash | 256 | 585 | 207.43 | 72.82 | 2.85x |
| MiMo-V2.6-Flash | 1024 | 585 | 207.48 | 72.84 | 2.85x |
| MiMo-V2.6-Flash | 4096 | 585 | 207.48 | 72.84 | 2.85x |
| MiMo-V2.6-Flash | 1 | 3149 | 7.99 | 7.93 | 1.01x |
| MiMo-V2.6-Flash | 2 | 3149 | 15.71 | 15.20 | 1.03x |
| MiMo-V2.6-Flash | 4 | 3149 | 30.39 | 26.94 | 1.13x |
| MiMo-V2.6-Flash | 8 | 3149 | 56.91 | 40.97 | 1.39x |
| MiMo-V2.6-Flash | 16 | 3149 | 100.34 | 56.17 | 1.79x |
| MiMo-V2.6-Flash | 32 | 3149 | 159.18 | 79.64 | 2.00x |
| MiMo-V2.6-Flash | 64 | 3149 | 214.80 | 102.91 | 2.09x |
| MiMo-V2.6-Flash | 256 | 3149 | 245.84 | 114.46 | 2.15x |
| MiMo-V2.6-Flash | 1024 | 3149 | 245.91 | 114.49 | 2.15x |
| MiMo-V2.6-Flash | 4096 | 3149 | 245.91 | 114.49 | 2.15x |

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
| gpu | MiMo-V2.6-Flash | 1 | 937.30 | 68.1% |
| rom | MiMo-V2.6-Flash | 1 | 125.41 | 55.0% |

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
| MiMo-V2.6-Flash | 1 | 26 | 96.35% | 232.33 | 9.27 |
| MiMo-V2.6-Flash | 2 | 1 | 26.84% | 141.89 | 9.27 |

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
| MiMo-V2.6-Flash | 1 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 26.5 | 109,221.5 |
| MiMo-V2.6-Flash | 2 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 26.5 | 109,221.5 |
| MiMo-V2.6-Flash | 4 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 26.5 | 109,221.5 |
| MiMo-V2.6-Flash | 8 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 26.5 | 109,221.5 |
| MiMo-V2.6-Flash | 16 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 26.5 | 109,221.5 |
| MiMo-V2.6-Flash | 32 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 26.5 | 109,221.5 |
| MiMo-V2.6-Flash | 64 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 26.5 | 109,221.5 |
| MiMo-V2.6-Flash | 256 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 26.5 | 109,221.5 |
| MiMo-V2.6-Flash | 1024 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 26.5 | 109,221.5 |
| MiMo-V2.6-Flash | 4096 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 26.5 | 109,221.5 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 304 |
| gpu | kv_read | 396 |
| gpu | layer_fixed_latency | 320 |
| gpu | link_latency | 406 |
| gpu | thermal | 34 |
| rom | compute | 3 |
| rom | infeasible | 2642 |
| rom | kv_read | 79 |
| rom | layer_fixed_latency | 179 |
| rom | link_latency | 168 |
| rom | weight_read | 49 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 304 |
| rom | CAPACITY | 2642 |

## Mechanical consistency audit

**FAIL** over 58,385 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x47', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x56', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x64', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x70', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x74', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x105', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x111', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x148', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x47', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x56', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x64', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x70', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x74', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x105', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x111', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x148', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x47', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x56', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x64', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x70', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x74', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x105', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x111', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x148', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x47', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x56', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x64', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x70', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x74', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x105', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x111', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x148', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-pipeline-x170', 'MiMo-V2.6-Flash', 1)

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

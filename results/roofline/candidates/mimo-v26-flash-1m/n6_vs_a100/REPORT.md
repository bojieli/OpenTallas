# Area-constrained roofline: n6_vs_a100-mimo-v26-flash-1m

> CANDIDATE MODEL under n6_vs_a100: MiMo-V2.6-Flash at 1,000,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 6,042x (ROM-N6-native-HBMKV-wafer-pipeline-x153-perstream, 8,678 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 33 devices. On the GPU side the correction reaches 166x (a100_sxm_80gb-x8562-pipeline, 8,562 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 141 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Flash takes 64 x 815 mm2 (52,160 mm2, array, KV in SRAM) at 7,472 tok/s per user and 143 tok/s per 1,000 mm2, holding 1 session, against 63 copies of one unified HBM die at the same silicon: 9.8x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Flash on 76,610 mm2 of ROM silicon at 8,386 tok/s per user against 76,818 mm2 of a100_sxm_80gb-x93-tensor at 829 tok/s: **10.1x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 282. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 20.25x to it.** At 185,005 mm2 on MiMo-V2.6-Flash the pipeline-only GPU delivers 45.94 tok/s and the same silicon running tensor delivers 930 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.10x (MiMo-V2.6-Flash, ROM binding on `kv_read`) to 0.20x (MiMo-V2.6-Flash, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Flash engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 11 to 44,462 tok/s, and its rate with every slot occupied from 44,581 to 44,581. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 8,678 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,361 us over NVLink, capping per-user decode at 735 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 438.6 us and cap it at 2,280 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 9 of 10 operating points and an array 1; on tokens per second per square millimetre the same points go 1 to the array and 9 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 763 of 1475 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 3.6x of aggregate throughput (MiMo-V2.6-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 3.60x, on MiMo-V2.6-Flash at batch 4096, where the busiest region carries 3.01x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 9 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 81% of its cooling budget. The companion study at the other node does have power-limited points.


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

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x64`** -- 64 x 815 mm2 reticle dies, 52,160 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **7,471.8 tok/s per user** (0.13 ms/token), binding on `link_latency`
- **143.2 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 7,472 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 4,245 W at 0.081 W/mm2, 568.2 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 63 copies of one unified HBM die -- `a100_sxm_80gb-x63-tensor`, 52,038 mm2, area ratio 1.0023 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 52,160 | 52,038 | 1.0023 |
| user tok/s | 7,471.8 | 761.3 | 9.81x |
| aggregate tok/s | 7,472 | 761 | 2.58x |
| resident sessions | 1 | 189 | -- |
| J/token | 0.5682 | 15.8274 | 27.9x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 189 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x224-tensor` at 185,024 mm2 and 930.2 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-array-hw-tensor-x94` | 76,610 | 8,385.5 | 109.5 | 1 | 10.12x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-array-hw-tensor-x94` | 76,610 | 8,385.5 | 109.5 | 1 | 10.12x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,525.5 | 76.3 | 1 | 4.78x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x64` | 52,160 | 7,471.8 | 143.2 | 1 | 9.81x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x64` | 52,160 | 7,471.8 | 143.2 | -- | 143.2 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x75` | 61,125 | 7,518.9 | 123.0 | 5.3 | 143.2 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x78-romfill` | 63,570 | 7,695.6 | 121.1 | 19.6 | 143.2 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x94` | 76,610 | 8,385.5 | 109.5 | 37.4 | 143.2 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x64` **<-- recommended** | 52,160 | 64 | 7,471.8 | 7,472 | 143.2 | 1 | `link_latency` | 4,245 | 568.2 | `a100_sxm_80gb-x63-tensor` | 9.81x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x75` | 61,125 | 75 | 7,518.9 | 7,519 | 123.0 | 1 | `link_latency` | 5,549 | 738.0 | `a100_sxm_80gb-x74-tensor` | 9.51x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x78-romfill` | 63,570 | 78 | 7,695.6 | 7,696 | 121.1 | 1 | `link_latency` | 5,899 | 766.5 | `a100_sxm_80gb-x77-tensor` | 9.65x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x94` | 76,610 | 94 | 8,385.5 | 8,386 | 109.5 | 1 | `link_latency` | 7,868 | 938.3 | `a100_sxm_80gb-x93-tensor` | 10.12x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 192 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x64` | 52,160 | 7,471.8 | 143.2 | 1 |
| array | 192 | fastest | `ROM-N6-native-SRAMKV-array-hw-tensor-x94` | 76,610 | 8,385.5 | 109.5 | 1 |
| array | 192 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x57` | 46,455 | 5,786.1 | 124.6 | 1 |
| wafer | 46 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,525.5 | 76.3 | 1 |
| wafer | 46 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,454.4 | 48.2 | 1 |
| wafer | 46 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 3,525.5 | 76.3 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-tensor-x94` | 76,610 | 8,385.5 | 8,386 | 1 | 7,868 | 938.3 | `link_latency` | `a100_sxm_80gb-x93-tensor` | 828.7 | 282 | 20,082.0 | 0.997 | 10.12x | 21.4x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,454.4 | 4,454 | 1 | 9,831 | 2,207.1 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 855.9 | 342 | 22,772.1 | 0.999 | 5.20x | 10.3x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-tensor-x119` | 96,985 | 7,500.0 | 7,500 | 1 | 10,747 | 1,433.0 | `link_latency` | `a100_sxm_80gb-x117-tensor` | 861.7 | 357 | 23,483.6 | 1.004 | 8.70x | 16.4x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,454.4 | -- | 1 | -- | 2,207.1 | -- | -- | -- | -- | -- | 1.049 | 0.59x wafer/array | -- |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 7,072,425 | 2,122.8 | 4,246 | 4,107 | 1,051,317 | 247,628.7 | `link_latency` | `a100_sxm_80gb-x8562-tensor` | 677.0 | 26,719 | 916,530.4 | 1.000 | 3.14x | 3.7x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 7,072,425 | 2,028.0 | 8,112 | 4,107 | 1,060,757 | 130,762.7 | `link_latency` | `a100_sxm_80gb-x8562-expert` | 598.5 | 26,364 | 519,615.8 | 1.000 | 3.39x | 4.0x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 7,072,425 | 1,861.8 | 14,895 | 4,107 | 1,077,315 | 72,329.6 | `link_latency` | `a100_sxm_80gb-x8562-expert` | 580.2 | 26,364 | 269,439.7 | 1.000 | 3.21x | 3.7x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 7,072,425 | 1,599.6 | 25,594 | 4,107 | 1,103,432 | 43,113.0 | `link_latency` | `a100_sxm_80gb-x8562-expert` | 542.6 | 26,364 | 145,423.5 | 1.000 | 2.95x | 3.4x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 7,072,425 | 1,248.1 | 39,939 | 4,107 | 1,138,441 | 28,504.5 | `link_latency` | `a100_sxm_80gb-x8562-expert` | 500.1 | 26,364 | 80,157.2 | 1.000 | 2.50x | 2.8x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 7,072,425 | 867.0 | 55,489 | 4,107 | 1,176,381 | 21,200.1 | `kv_read` | `a100_sxm_80gb-x8562-expert` | 472.0 | 26,364 | 43,708.9 | 1.000 | 1.84x | 2.1x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 7,072,425 | 342.7 | 87,743 | 4,107 | 1,255,300 | 14,306.5 | `kv_read` | `a100_sxm_80gb-x8562-expert` | 407.1 | 26,364 | 14,479.6 | 1.000 | 0.84x | 1.0x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 7,072,425 | 90.3 | 92,507 | 4,107 | 1,266,829 | 13,694.4 | `kv_read` | `a100_sxm_80gb-x8562-hybrid` | 301.6 | 26,719 | 7,881.6 | 1.000 | 0.30x | 0.5x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 7,072,425 | 22.9 | 93,780 | 4,107 | 1,269,878 | 13,541.0 | `kv_read` | `a100_sxm_80gb-x8562-expert` | 112.9 | 26,364 | 5,225.2 | 1.000 | 0.20x | 0.4x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x64` | 52,160 | array | SRAM | 1 |
| 2-64 | `ROM-N6-native-HBMKV-wafer-tensor-x153` | 7,072,425 | wafer | HBM | 4,107 |
| 256-4096 | `ROM-N6-native-HBMKV-wafer-hybrid-x153` | 7,072,425 | wafer | HBM | 4,107 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Flash | SRAM | rom | 57, 59, 64, 71, 73, 78, 94, 113, 140, 141, 143, 145, 170, 188, 227, 340 |
| MiMo-V2.6-Flash | SRAM | sram | 57, 59, 64, 71, 75, 94, 113, 119, 134, 135, 136, 141, 170, 188, 227, 340 |

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
(4.327e+11 B/s/mm2).

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

**The thermal limit can bind now, and this is the first version of this
study in which it could -- in this one it does not, and the companion
study at the other node is where it does.**
Static power is charged per mm2 per second whether or not a byte moves,
so the coolable step time solves
`t >= E_dynamic / (cooling_limit - P_static)` rather than dividing the
total energy by the total limit. Under the old rule stretching a step
always reduced modelled power, so every design was coolable at some speed
and `thermal_scale` was exactly 1.0 at all 11,747 feasible points across
both studies.

- **0 of 1,475 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 81% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 84 | 0 | 74.6% | 81.0% | 0.392 | 49% |
| gpu | wafer (>=40,000 mm2) | 895 | 0 | 72.7% | 81.1% | 0.393 | 50% |
| rom | large array (5,000-40,000 mm2) | 48 | 0 | 13.5% | 19.5% | 0.097 | 95% |
| rom | wafer (>=40,000 mm2) | 448 | 0 | 17.4% | 35.9% | 0.180 | 97% |

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
| MiMo-V2.6-Flash | 1 | 76,610 | `MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x94` | 0.938265 | 7,867.8 | link_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x93-tensor` | 20.081967 | 16,642.7 | link_latency | 21.40x |
| MiMo-V2.6-Flash | 2 | 7,072,425 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153` | 247.628683 | 1,051,317.5 | link_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x8562-tensor` | 916.530378 | 1,240,914.0 | link_latency | 3.70x |
| MiMo-V2.6-Flash | 4 | 7,072,425 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153` | 130.762693 | 1,060,757.1 | link_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert` | 519.615763 | 1,244,003.4 | weight_read | 3.97x |
| MiMo-V2.6-Flash | 8 | 7,072,425 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153` | 72.329633 | 1,077,314.6 | link_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert` | 269.439725 | 1,250,708.6 | weight_read | 3.73x |
| MiMo-V2.6-Flash | 16 | 7,072,425 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153` | 43.112991 | 1,103,431.6 | link_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert` | 145.423487 | 1,262,421.2 | weight_read | 3.37x |
| MiMo-V2.6-Flash | 32 | 7,072,425 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153` | 28.504500 | 1,138,440.5 | link_latency | `MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert` | 80.157223 | 1,282,781.2 | weight_read | 2.81x |
| MiMo-V2.6-Flash | 64 | 7,072,425 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153` | 21.200062 | 1,176,380.8 | kv_read | `MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert` | 43.708943 | 1,320,493.8 | weight_read | 2.06x |
| MiMo-V2.6-Flash | 256 | 7,072,425 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153` | 14.306522 | 1,255,299.7 | kv_read | `MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert` | 14.479573 | 1,508,895.5 | weight_read | 1.01x |
| MiMo-V2.6-Flash | 1024 | 7,072,425 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153` | 13.694398 | 1,266,828.7 | kv_read | `MiMo-V2.6-Flash/a100_sxm_80gb-x8562-hybrid` | 7.881641 | 2,489,491.8 | kv_read | 0.52x |
| MiMo-V2.6-Flash | 4096 | 7,072,425 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153` | 13.541036 | 1,269,878.2 | kv_read | `MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert` | 5.225194 | 2,416,226.7 | kv_read | 0.39x |

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


## Derived technology at N6

These are outputs of the graded primitives, not inputs.

| Quantity | Value | Grade |
|---|---:|---|
| SRAM capacity density | 3.009 MB/mm2 | assumed |
| ROM capacity density | 7.295 MB/mm2 | derived |
| ROM read bandwidth density | 282.2 GB/s/mm2 | derived |
| SRAM read bandwidth density | 432.7 GB/s/mm2 | derived |
| Compute density, bf16 | 0.446 Tops/s/mm2 | derived |
| Compute density, fp8 | 0.891 Tops/s/mm2 | derived |
| Compute density, w4a8 | 1.261 Tops/s/mm2 | derived |
| Compute density, fp4 | 1.783 Tops/s/mm2 | derived |
| Compute density, fp32 | 0.028 Tops/s/mm2 | derived |
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
| MiMo-V2.6-Flash | 1 | 46,225 | 9,549.3 | wafer-pipeline | 3,525.5 | wafer-tensor | 2.71x | 1,941.1 | pipeline | 738.1 | tensor | 2.63x | 4.92x | 4.78x | 0.97x |
| MiMo-V2.6-Flash | 2 | 92,450 | 32,164.4 | wafer-pipeline | 4,454.4 | wafer-hybrid | 7.22x | 3,105.9 | pipeline | 855.9 | tensor | 3.63x | 10.36x | 5.20x | 0.50x |
| MiMo-V2.6-Flash | 3 | 138,675 | 37,020.1 | wafer-pipeline | 4,410.2 | wafer-hybrid | 8.39x | 3,882.5 | pipeline | 904.0 | tensor | 4.29x | 9.54x | 4.88x | 0.51x |
| MiMo-V2.6-Flash | 4 | 184,900 | 37,020.1 | wafer-pipeline | 4,398.5 | wafer-tensor | 8.42x | 4,437.2 | pipeline | 930.2 | tensor | 4.77x | 8.34x | 4.73x | 0.57x |
| MiMo-V2.6-Flash | 6 | 277,350 | 37,020.1 | wafer-pipeline | 4,024.1 | wafer-tensor | 9.20x | 5,176.8 | pipeline | 697.5 | tensor | 7.42x | 7.15x | 5.77x | 0.81x |
| MiMo-V2.6-Flash | 8 | 369,800 | 37,020.1 | wafer-pipeline | 4,023.8 | wafer-tensor | 9.20x | 5,647.5 | pipeline | 705.1 | tensor | 8.01x | 6.56x | 5.71x | 0.87x |
| MiMo-V2.6-Flash | 12 | 554,700 | 37,020.1 | wafer-pipeline | 3,708.4 | wafer-tensor | 9.98x | 6,212.4 | pipeline | 712.9 | tensor | 8.71x | 5.96x | 5.20x | 0.87x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.50x to 0.97x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Flash | 1 | fastest | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x94 | 76,610 | 8,385.5 | 8,385.5 | link_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x93-tensor | 76,818 | 1.00x | tensor | 963.15 | 828.7 | 828.7 | link_latency | 10.12x | 1.96x | 182.53x | 10.12x |
| MiMo-V2.6-Flash | 1 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | 46,225 | 3,525.5 | 3,525.5 | link_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 957.53 | 738.1 | 738.1 | link_latency | 4.78x | 1.37x | 76.74x | 4.78x |
| MiMo-V2.6-Flash | 2 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | 7,072,425 | 2,122.8 | 4,245.5 | link_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x8562-tensor | 7,072,212 | 1.00x | tensor | 1,461.85 | 677.0 | 1,353.9 | link_latency | 3.14x | 0.01x | 46.21x | 3.14x |
| MiMo-V2.6-Flash | 4 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | 7,072,425 | 2,028.0 | 8,112.1 | link_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert | 7,072,212 | 1.00x | expert | 675.02 | 598.5 | 2,394.1 | weight_read | 3.39x | 0.02x | 44.14x | 3.39x |
| MiMo-V2.6-Flash | 8 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | 7,072,425 | 1,861.8 | 14,894.5 | link_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert | 7,072,212 | 1.00x | expert | 675.17 | 580.2 | 4,641.9 | weight_read | 3.21x | 0.04x | 40.53x | 3.21x |
| MiMo-V2.6-Flash | 16 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | 7,072,425 | 1,599.6 | 25,593.9 | link_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert | 7,072,212 | 1.00x | expert | 675.45 | 542.6 | 8,681.0 | weight_read | 2.95x | 0.07x | 34.82x | 2.95x |
| MiMo-V2.6-Flash | 32 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | 7,072,425 | 1,248.1 | 39,939.0 | link_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert | 7,072,212 | 1.00x | expert | 676.03 | 500.1 | 16,003.3 | weight_read | 2.50x | 0.10x | 27.17x | 2.50x |
| MiMo-V2.6-Flash | 64 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | 7,072,425 | 867.0 | 55,489.5 | kv_read | MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert | 7,072,212 | 1.00x | expert | 677.17 | 472.0 | 30,211.1 | weight_read | 1.84x | 0.14x | 18.87x | 1.84x |
| MiMo-V2.6-Flash | 256 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 342.7 | 87,743.2 | kv_read | MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert | 7,072,212 | 1.00x | expert | 684.05 | 407.1 | 104,208.6 | weight_read | 0.84x | 0.22x | 7.46x | 0.84x |
| MiMo-V2.6-Flash | 1024 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 90.3 | 92,507.1 | kv_read | MiMo-V2.6-Flash/a100_sxm_80gb-x8562-hybrid | 7,072,212 | 1.00x | hybrid | 597.69 | 301.6 | 323,058.6 | kv_read | 0.30x | 0.24x | 1.97x | 0.52x |
| MiMo-V2.6-Flash | 4096 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 22.9 | 93,780.0 | kv_read | MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert | 7,072,212 | 1.00x | expert | 821.61 | 112.9 | 462,418.5 | kv_read | 0.20x | 0.20x | 0.50x | 0.20x |

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
| MiMo-V2.6-Flash | 33 | 27,258 | 46.0 | 617.8 | 264.2 | tensor | 952.14 | 58.8% | link_latency |
| MiMo-V2.6-Flash | 35 | 28,910 | 46.0 | 632.4 | 277.9 | tensor | 952.14 | 60.2% | link_latency |
| MiMo-V2.6-Flash | 47 | 38,822 | 45.9 | 701.0 | 305.6 | tensor | 955.28 | 67.0% | link_latency |
| MiMo-V2.6-Flash | 56 | 46,256 | 45.9 | 738.1 | 310.9 | tensor | 957.53 | 70.7% | link_latency |
| MiMo-V2.6-Flash | 58 | 47,908 | 45.9 | 744.5 | 285.8 | tensor | 959.22 | 71.4% | link_latency |
| MiMo-V2.6-Flash | 63 | 52,038 | 45.9 | 761.3 | 306.6 | tensor | 959.22 | 73.0% | link_latency |
| MiMo-V2.6-Flash | 70 | 57,820 | 45.9 | 781.0 | 303.2 | tensor | 960.53 | 75.0% | link_latency |
| MiMo-V2.6-Flash | 72 | 59,472 | 45.9 | 786.2 | 310.4 | tensor | 960.53 | 75.5% | link_latency |
| MiMo-V2.6-Flash | 74 | 61,124 | 45.9 | 790.6 | 290.4 | tensor | 961.58 | 76.0% | link_latency |
| MiMo-V2.6-Flash | 75 | 61,950 | 45.9 | 793.1 | 293.8 | tensor | 961.58 | 76.3% | link_latency |
| MiMo-V2.6-Flash | 77 | 63,602 | 45.9 | 797.8 | 300.4 | tensor | 961.58 | 76.7% | link_latency |
| MiMo-V2.6-Flash | 93 | 76,818 | 45.9 | 828.7 | 301.6 | tensor | 963.15 | 79.8% | link_latency |
| MiMo-V2.6-Flash | 111 | 91,686 | 45.9 | 854.7 | 307.0 | tensor | 964.27 | 82.4% | link_latency |
| MiMo-V2.6-Flash | 112 | 92,512 | 45.9 | 855.9 | 309.3 | tensor | 964.27 | 82.5% | link_latency |
| MiMo-V2.6-Flash | 117 | 96,642 | 45.9 | 861.7 | 302.6 | tensor | 964.72 | 83.1% | link_latency |
| MiMo-V2.6-Flash | 132 | 109,032 | 45.9 | 877.0 | 301.0 | tensor | 965.46 | 84.7% | link_latency |
| MiMo-V2.6-Flash | 133 | 109,858 | 45.9 | 878.0 | 302.9 | tensor | 965.46 | 84.8% | link_latency |
| MiMo-V2.6-Flash | 134 | 110,684 | 45.9 | 878.9 | 304.8 | tensor | 965.46 | 84.9% | link_latency |
| MiMo-V2.6-Flash | 138 | 113,988 | 45.9 | 882.3 | 297.6 | tensor | 965.77 | 85.2% | link_latency |
| MiMo-V2.6-Flash | 139 | 114,814 | 45.9 | 883.2 | 299.4 | tensor | 965.77 | 85.3% | link_latency |
| MiMo-V2.6-Flash | 141 | 116,466 | 45.9 | 884.9 | 303.0 | tensor | 965.77 | 85.5% | link_latency |
| MiMo-V2.6-Flash | 143 | 118,118 | 45.9 | 886.6 | 306.6 | tensor | 965.77 | 85.6% | link_latency |
| MiMo-V2.6-Flash | 168 | 138,768 | 45.9 | 904.0 | 307.7 | tensor | 966.52 | 87.4% | link_latency |
| MiMo-V2.6-Flash | 185 | 152,810 | 45.9 | 913.3 | 297.7 | tensor | 967.08 | 88.3% | link_latency |
| MiMo-V2.6-Flash | 224 | 185,024 | 45.9 | 930.2 | 306.2 | tensor | 967.64 | 90.0% | link_latency |
| MiMo-V2.6-Flash | 335 | 276,710 | 45.9 | 697.4 | 302.4 | tensor | 1,358.53 | 94.7% | link_latency |
| MiMo-V2.6-Flash | 336 | 277,536 | 45.9 | 697.5 | 303.1 | tensor | 1,358.53 | 94.8% | link_latency |
| MiMo-V2.6-Flash | 448 | 370,048 | 45.9 | 705.1 | 301.8 | tensor | 1,359.09 | 95.8% | link_latency |
| MiMo-V2.6-Flash | 672 | 555,072 | 45.9 | 712.9 | 301.8 | tensor | 1,359.65 | 96.9% | link_latency |
| MiMo-V2.6-Flash | 1315 | 1,086,190 | 45.9 | 720.7 | 300.9 | tensor | 1,360.20 | 98.0% | link_latency |
| MiMo-V2.6-Flash | 8562 | 7,072,212 | 45.9 | 727.8 | 301.6 | tensor | 1,360.69 | 99.0% | link_latency |

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
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x135 | MiMo-V2.6-Flash | 135 | pipeline | rom_package_ucie | rom_board_serdes | 47 | 1.58 us | 63,139.7 tok/s | 631,396.8 tok/s | 36 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.43 us; 11 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.15 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x64 | MiMo-V2.6-Flash | 64 | tensor | rom_package_ucie | rom_board_serdes | 192 | 66.95 us | 1,493.6 tok/s | 14,936.3 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 96 x all_reduce span 16 on rom_board_serdes (traversals 6.6) = 64.59 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x136 | MiMo-V2.6-Flash | 136 | hybrid | rom_package_ucie | rom_board_serdes | 129 | 5.81 us | 17,204.1 tok/s | 172,041.4 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 33 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 3.45 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x134 | MiMo-V2.6-Flash | 134 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2 | MiMo-V2.6-Flash | 2 | pipeline | on_wafer | rom_wafer_serdes | 47 | 5.88 us | 17,021.2 tok/s | 170,212.3 tok/s | 47 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.88 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-tensor-x75 | MiMo-V2.6-Flash | 75 | tensor | nvlink3 | infiniband_hdr | 192 | 961.58 us | 104.0 tok/s | 1,040.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 474.69 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x2 | MiMo-V2.6-Flash | 2 | tensor | on_wafer | rom_wafer_serdes | 192 | 206.12 us | 485.2 tok/s | 4,851.6 tok/s | 96 x all_reduce span 57 on on_wafer (traversals 15.4) = 184.80 us; 96 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 21.32 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hybrid-x119 | MiMo-V2.6-Flash | 119 | hybrid | nvlink3 | infiniband_hdr | 110 | 519.89 us | 192.3 tok/s | 1,923.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.01 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | MiMo-V2.6-Flash | 2 | hybrid | on_wafer | rom_wafer_serdes | 97 | 184.90 us | 540.8 tok/s | 5,408.3 tok/s | 96 x all_reduce span 57 on on_wafer (traversals 15.4) = 184.80 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x153 | MiMo-V2.6-Flash | 153 | pipeline | on_wafer | rom_wafer_serdes | 47 | 5.88 us | 17,021.2 tok/s | 170,212.3 tok/s | 47 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.88 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | MiMo-V2.6-Flash | 153 | tensor | on_wafer | rom_wafer_serdes | 192 | 438.63 us | 228.0 tok/s | 2,279.8 tok/s | 96 x all_reduce span 57 on on_wafer (traversals 15.4) = 184.80 us; 96 x all_reduce span 153 on rom_wafer_serdes (traversals 26.4) = 253.83 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | MiMo-V2.6-Flash | 153 | hybrid | on_wafer | rom_wafer_serdes | 143 | 189.56 us | 527.5 tok/s | 5,275.3 tok/s | 96 x all_reduce span 57 on on_wafer (traversals 15.4) = 184.80 us; 47 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 4.76 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x33-pipeline | MiMo-V2.6-Flash | 33 | pipeline | nvlink3 | infiniband_hdr | 32 | 80.20 us | 1,247.0 tok/s | 12,469.6 tok/s | 28 x point_to_point span 2 on nvlink3 (traversals 1.0) = 70.76 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x33-tensor | MiMo-V2.6-Flash | 33 | tensor | nvlink3 | infiniband_hdr | 192 | 952.14 us | 105.0 tok/s | 1,050.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 465.26 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x33-hybrid | MiMo-V2.6-Flash | 33 | hybrid | nvlink3 | infiniband_hdr | 100 | 496.31 us | 201.5 tok/s | 2,014.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x33-expert | MiMo-V2.6-Flash | 33 | expert | nvlink3 | infiniband_hdr | 192 | 684.23 us | 146.2 tok/s | 1,461.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.72 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 202.51 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x35-pipeline | MiMo-V2.6-Flash | 35 | pipeline | nvlink3 | infiniband_hdr | 34 | 85.25 us | 1,173.0 tok/s | 11,730.2 tok/s | 30 x point_to_point span 2 on nvlink3 (traversals 1.0) = 75.82 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x35-tensor | MiMo-V2.6-Flash | 35 | tensor | nvlink3 | infiniband_hdr | 192 | 952.14 us | 105.0 tok/s | 1,050.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 465.26 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x35-hybrid | MiMo-V2.6-Flash | 35 | hybrid | nvlink3 | infiniband_hdr | 100 | 496.31 us | 201.5 tok/s | 2,014.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x35-expert | MiMo-V2.6-Flash | 35 | expert | nvlink3 | infiniband_hdr | 192 | 683.79 us | 146.2 tok/s | 1,462.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.72 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 202.07 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x47-pipeline | MiMo-V2.6-Flash | 47 | pipeline | nvlink3 | infiniband_hdr | 46 | 115.41 us | 866.5 tok/s | 8,664.9 tok/s | 41 x point_to_point span 2 on nvlink3 (traversals 1.0) = 103.62 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x47-tensor | MiMo-V2.6-Flash | 47 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x47-hybrid | MiMo-V2.6-Flash | 47 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x47-expert | MiMo-V2.6-Flash | 47 | expert | nvlink3 | infiniband_hdr | 192 | 681.61 us | 146.7 tok/s | 1,467.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.38 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 200.23 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x56-pipeline | MiMo-V2.6-Flash | 56 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x56-tensor | MiMo-V2.6-Flash | 56 | tensor | nvlink3 | infiniband_hdr | 192 | 957.53 us | 104.4 tok/s | 1,044.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 470.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x56-hybrid | MiMo-V2.6-Flash | 56 | hybrid | nvlink3 | infiniband_hdr | 102 | 501.03 us | 199.6 tok/s | 1,995.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x56-expert | MiMo-V2.6-Flash | 56 | expert | nvlink3 | infiniband_hdr | 192 | 680.36 us | 147.0 tok/s | 1,469.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.98 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 199.37 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x58-pipeline | MiMo-V2.6-Flash | 58 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x58-tensor | MiMo-V2.6-Flash | 58 | tensor | nvlink3 | infiniband_hdr | 192 | 959.22 us | 104.3 tok/s | 1,042.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 472.34 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x58-hybrid | MiMo-V2.6-Flash | 58 | hybrid | nvlink3 | infiniband_hdr | 103 | 503.39 us | 198.7 tok/s | 1,986.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x58-expert | MiMo-V2.6-Flash | 58 | expert | nvlink3 | infiniband_hdr | 192 | 680.20 us | 147.0 tok/s | 1,470.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.98 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 199.22 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x63-pipeline | MiMo-V2.6-Flash | 63 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x63-tensor | MiMo-V2.6-Flash | 63 | tensor | nvlink3 | infiniband_hdr | 192 | 959.22 us | 104.3 tok/s | 1,042.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 472.34 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x63-hybrid | MiMo-V2.6-Flash | 63 | hybrid | nvlink3 | infiniband_hdr | 103 | 503.39 us | 198.7 tok/s | 1,986.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x63-expert | MiMo-V2.6-Flash | 63 | expert | nvlink3 | infiniband_hdr | 192 | 679.86 us | 147.1 tok/s | 1,470.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.98 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.87 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x70-pipeline | MiMo-V2.6-Flash | 70 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x70-tensor | MiMo-V2.6-Flash | 70 | tensor | nvlink3 | infiniband_hdr | 192 | 960.53 us | 104.1 tok/s | 1,041.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 473.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x70-hybrid | MiMo-V2.6-Flash | 70 | hybrid | nvlink3 | infiniband_hdr | 104 | 505.74 us | 197.7 tok/s | 1,977.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x70-expert | MiMo-V2.6-Flash | 70 | expert | nvlink3 | infiniband_hdr | 192 | 679.34 us | 147.2 tok/s | 1,472.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.86 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.48 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x72-pipeline | MiMo-V2.6-Flash | 72 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x72-tensor | MiMo-V2.6-Flash | 72 | tensor | nvlink3 | infiniband_hdr | 192 | 960.53 us | 104.1 tok/s | 1,041.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 473.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x72-hybrid | MiMo-V2.6-Flash | 72 | hybrid | nvlink3 | infiniband_hdr | 104 | 505.74 us | 197.7 tok/s | 1,977.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x72-expert | MiMo-V2.6-Flash | 72 | expert | nvlink3 | infiniband_hdr | 192 | 679.14 us | 147.2 tok/s | 1,472.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.76 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.38 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x74-pipeline | MiMo-V2.6-Flash | 74 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x74-tensor | MiMo-V2.6-Flash | 74 | tensor | nvlink3 | infiniband_hdr | 192 | 961.58 us | 104.0 tok/s | 1,040.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 474.69 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x74-hybrid | MiMo-V2.6-Flash | 74 | hybrid | nvlink3 | infiniband_hdr | 105 | 508.10 us | 196.8 tok/s | 1,968.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x74-expert | MiMo-V2.6-Flash | 74 | expert | nvlink3 | infiniband_hdr | 192 | 679.05 us | 147.3 tok/s | 1,472.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.76 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.28 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x75-pipeline | MiMo-V2.6-Flash | 75 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x75-tensor | MiMo-V2.6-Flash | 75 | tensor | nvlink3 | infiniband_hdr | 192 | 961.58 us | 104.0 tok/s | 1,040.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 474.69 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x75-hybrid | MiMo-V2.6-Flash | 75 | hybrid | nvlink3 | infiniband_hdr | 105 | 508.10 us | 196.8 tok/s | 1,968.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x75-expert | MiMo-V2.6-Flash | 75 | expert | nvlink3 | infiniband_hdr | 192 | 679.00 us | 147.3 tok/s | 1,472.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.76 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.24 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x77-pipeline | MiMo-V2.6-Flash | 77 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x77-tensor | MiMo-V2.6-Flash | 77 | tensor | nvlink3 | infiniband_hdr | 192 | 961.58 us | 104.0 tok/s | 1,040.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 474.69 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x77-hybrid | MiMo-V2.6-Flash | 77 | hybrid | nvlink3 | infiniband_hdr | 105 | 508.10 us | 196.8 tok/s | 1,968.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x77-expert | MiMo-V2.6-Flash | 77 | expert | nvlink3 | infiniband_hdr | 192 | 678.91 us | 147.3 tok/s | 1,472.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.76 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x93-pipeline | MiMo-V2.6-Flash | 93 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x93-tensor | MiMo-V2.6-Flash | 93 | tensor | nvlink3 | infiniband_hdr | 192 | 963.15 us | 103.8 tok/s | 1,038.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 476.27 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x93-hybrid | MiMo-V2.6-Flash | 93 | hybrid | nvlink3 | infiniband_hdr | 107 | 512.82 us | 195.0 tok/s | 1,950.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.93 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x93-expert | MiMo-V2.6-Flash | 93 | expert | nvlink3 | infiniband_hdr | 192 | 678.21 us | 147.4 tok/s | 1,474.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.63 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.59 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x111-pipeline | MiMo-V2.6-Flash | 111 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x111-tensor | MiMo-V2.6-Flash | 111 | tensor | nvlink3 | infiniband_hdr | 192 | 964.27 us | 103.7 tok/s | 1,037.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 477.39 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x111-hybrid | MiMo-V2.6-Flash | 111 | hybrid | nvlink3 | infiniband_hdr | 109 | 517.53 us | 193.2 tok/s | 1,932.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x111-expert | MiMo-V2.6-Flash | 111 | expert | nvlink3 | infiniband_hdr | 192 | 677.68 us | 147.6 tok/s | 1,475.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.53 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x112-pipeline | MiMo-V2.6-Flash | 112 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x112-tensor | MiMo-V2.6-Flash | 112 | tensor | nvlink3 | infiniband_hdr | 192 | 964.27 us | 103.7 tok/s | 1,037.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 477.39 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x112-hybrid | MiMo-V2.6-Flash | 112 | hybrid | nvlink3 | infiniband_hdr | 109 | 517.53 us | 193.2 tok/s | 1,932.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x112-expert | MiMo-V2.6-Flash | 112 | expert | nvlink3 | infiniband_hdr | 192 | 677.62 us | 147.6 tok/s | 1,475.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.49 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.13 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x117-pipeline | MiMo-V2.6-Flash | 117 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x117-tensor | MiMo-V2.6-Flash | 117 | tensor | nvlink3 | infiniband_hdr | 192 | 964.72 us | 103.7 tok/s | 1,036.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 477.84 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x117-hybrid | MiMo-V2.6-Flash | 117 | hybrid | nvlink3 | infiniband_hdr | 110 | 519.89 us | 192.3 tok/s | 1,923.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.01 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x117-expert | MiMo-V2.6-Flash | 117 | expert | nvlink3 | infiniband_hdr | 192 | 677.52 us | 147.6 tok/s | 1,476.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.49 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.03 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x132-pipeline | MiMo-V2.6-Flash | 132 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x132-tensor | MiMo-V2.6-Flash | 132 | tensor | nvlink3 | infiniband_hdr | 192 | 965.46 us | 103.6 tok/s | 1,035.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 478.58 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x132-hybrid | MiMo-V2.6-Flash | 132 | hybrid | nvlink3 | infiniband_hdr | 112 | 524.60 us | 190.6 tok/s | 1,906.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 37.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x132-expert | MiMo-V2.6-Flash | 132 | expert | nvlink3 | infiniband_hdr | 192 | 677.22 us | 147.7 tok/s | 1,476.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.43 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x133-pipeline | MiMo-V2.6-Flash | 133 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x133-tensor | MiMo-V2.6-Flash | 133 | tensor | nvlink3 | infiniband_hdr | 192 | 965.46 us | 103.6 tok/s | 1,035.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 478.58 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x133-hybrid | MiMo-V2.6-Flash | 133 | hybrid | nvlink3 | infiniband_hdr | 112 | 524.60 us | 190.6 tok/s | 1,906.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 37.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x133-expert | MiMo-V2.6-Flash | 133 | expert | nvlink3 | infiniband_hdr | 192 | 677.20 us | 147.7 tok/s | 1,476.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.43 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.77 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x134-pipeline | MiMo-V2.6-Flash | 134 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x134-tensor | MiMo-V2.6-Flash | 134 | tensor | nvlink3 | infiniband_hdr | 192 | 965.46 us | 103.6 tok/s | 1,035.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 478.58 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x134-hybrid | MiMo-V2.6-Flash | 134 | hybrid | nvlink3 | infiniband_hdr | 112 | 524.60 us | 190.6 tok/s | 1,906.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 37.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x134-expert | MiMo-V2.6-Flash | 134 | expert | nvlink3 | infiniband_hdr | 192 | 677.19 us | 147.7 tok/s | 1,476.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.43 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.76 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x138-pipeline | MiMo-V2.6-Flash | 138 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x138-tensor | MiMo-V2.6-Flash | 138 | tensor | nvlink3 | infiniband_hdr | 192 | 965.77 us | 103.5 tok/s | 1,035.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 478.89 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x138-hybrid | MiMo-V2.6-Flash | 138 | hybrid | nvlink3 | infiniband_hdr | 113 | 526.96 us | 189.8 tok/s | 1,897.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x138-expert | MiMo-V2.6-Flash | 138 | expert | nvlink3 | infiniband_hdr | 192 | 677.11 us | 147.7 tok/s | 1,476.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.40 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.70 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x139-pipeline | MiMo-V2.6-Flash | 139 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x139-tensor | MiMo-V2.6-Flash | 139 | tensor | nvlink3 | infiniband_hdr | 192 | 965.77 us | 103.5 tok/s | 1,035.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 478.89 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x139-hybrid | MiMo-V2.6-Flash | 139 | hybrid | nvlink3 | infiniband_hdr | 113 | 526.96 us | 189.8 tok/s | 1,897.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x139-expert | MiMo-V2.6-Flash | 139 | expert | nvlink3 | infiniband_hdr | 192 | 677.10 us | 147.7 tok/s | 1,476.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.40 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.69 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x141-pipeline | MiMo-V2.6-Flash | 141 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x141-tensor | MiMo-V2.6-Flash | 141 | tensor | nvlink3 | infiniband_hdr | 192 | 965.77 us | 103.5 tok/s | 1,035.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 478.89 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x141-hybrid | MiMo-V2.6-Flash | 141 | hybrid | nvlink3 | infiniband_hdr | 113 | 526.96 us | 189.8 tok/s | 1,897.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x141-expert | MiMo-V2.6-Flash | 141 | expert | nvlink3 | infiniband_hdr | 192 | 677.07 us | 147.7 tok/s | 1,477.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.40 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.66 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x143-pipeline | MiMo-V2.6-Flash | 143 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x143-tensor | MiMo-V2.6-Flash | 143 | tensor | nvlink3 | infiniband_hdr | 192 | 965.77 us | 103.5 tok/s | 1,035.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 478.89 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x143-hybrid | MiMo-V2.6-Flash | 143 | hybrid | nvlink3 | infiniband_hdr | 113 | 526.96 us | 189.8 tok/s | 1,897.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x143-expert | MiMo-V2.6-Flash | 143 | expert | nvlink3 | infiniband_hdr | 192 | 677.04 us | 147.7 tok/s | 1,477.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.40 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.64 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x168-pipeline | MiMo-V2.6-Flash | 168 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x168-tensor | MiMo-V2.6-Flash | 168 | tensor | nvlink3 | infiniband_hdr | 192 | 966.52 us | 103.5 tok/s | 1,034.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 479.64 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x168-hybrid | MiMo-V2.6-Flash | 168 | hybrid | nvlink3 | infiniband_hdr | 116 | 534.03 us | 187.3 tok/s | 1,872.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x168-expert | MiMo-V2.6-Flash | 168 | expert | nvlink3 | infiniband_hdr | 192 | 676.71 us | 147.8 tok/s | 1,477.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.33 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.38 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x185-pipeline | MiMo-V2.6-Flash | 185 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x185-tensor | MiMo-V2.6-Flash | 185 | tensor | nvlink3 | infiniband_hdr | 192 | 967.08 us | 103.4 tok/s | 1,034.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 480.20 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x185-hybrid | MiMo-V2.6-Flash | 185 | hybrid | nvlink3 | infiniband_hdr | 119 | 541.11 us | 184.8 tok/s | 1,848.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 54.23 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x185-expert | MiMo-V2.6-Flash | 185 | expert | nvlink3 | infiniband_hdr | 192 | 676.54 us | 147.8 tok/s | 1,478.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.30 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.24 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x224-pipeline | MiMo-V2.6-Flash | 224 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x224-tensor | MiMo-V2.6-Flash | 224 | tensor | nvlink3 | infiniband_hdr | 192 | 967.64 us | 103.3 tok/s | 1,033.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 480.76 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x224-hybrid | MiMo-V2.6-Flash | 224 | hybrid | nvlink3 | infiniband_hdr | 123 | 550.54 us | 181.6 tok/s | 1,816.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.66 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x224-expert | MiMo-V2.6-Flash | 224 | expert | nvlink3 | infiniband_hdr | 192 | 676.25 us | 147.9 tok/s | 1,478.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.25 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.00 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x335-pipeline | MiMo-V2.6-Flash | 335 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x335-tensor | MiMo-V2.6-Flash | 335 | tensor | nvlink3 | infiniband_hdr | 192 | 1,358.53 us | 73.6 tok/s | 736.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 871.64 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x335-hybrid | MiMo-V2.6-Flash | 335 | hybrid | nvlink3 | infiniband_hdr | 137 | 583.55 us | 171.4 tok/s | 1,713.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x335-expert | MiMo-V2.6-Flash | 335 | expert | nvlink3 | infiniband_hdr | 192 | 675.80 us | 148.0 tok/s | 1,479.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.17 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.63 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x336-pipeline | MiMo-V2.6-Flash | 336 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x336-tensor | MiMo-V2.6-Flash | 336 | tensor | nvlink3 | infiniband_hdr | 192 | 1,358.53 us | 73.6 tok/s | 736.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 871.64 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x336-hybrid | MiMo-V2.6-Flash | 336 | hybrid | nvlink3 | infiniband_hdr | 137 | 583.55 us | 171.4 tok/s | 1,713.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x336-expert | MiMo-V2.6-Flash | 336 | expert | nvlink3 | infiniband_hdr | 192 | 675.79 us | 148.0 tok/s | 1,479.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.16 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.63 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x448-pipeline | MiMo-V2.6-Flash | 448 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x448-tensor | MiMo-V2.6-Flash | 448 | tensor | nvlink3 | infiniband_hdr | 192 | 1,359.09 us | 73.6 tok/s | 735.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 872.21 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x448-hybrid | MiMo-V2.6-Flash | 448 | hybrid | nvlink3 | infiniband_hdr | 143 | 597.69 us | 167.3 tok/s | 1,673.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 110.81 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x448-expert | MiMo-V2.6-Flash | 448 | expert | nvlink3 | infiniband_hdr | 192 | 675.56 us | 148.0 tok/s | 1,480.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.12 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.44 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x672-pipeline | MiMo-V2.6-Flash | 672 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x672-tensor | MiMo-V2.6-Flash | 672 | tensor | nvlink3 | infiniband_hdr | 192 | 1,359.65 us | 73.5 tok/s | 735.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 872.77 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x672-hybrid | MiMo-V2.6-Flash | 672 | hybrid | nvlink3 | infiniband_hdr | 143 | 597.69 us | 167.3 tok/s | 1,673.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 110.81 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x672-expert | MiMo-V2.6-Flash | 672 | expert | nvlink3 | infiniband_hdr | 192 | 675.34 us | 148.1 tok/s | 1,480.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.08 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.25 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x1315-pipeline | MiMo-V2.6-Flash | 1315 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x1315-tensor | MiMo-V2.6-Flash | 1315 | tensor | nvlink3 | infiniband_hdr | 192 | 1,360.20 us | 73.5 tok/s | 735.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 165 on infiniband_hdr (traversals 4.0) = 873.32 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x1315-hybrid | MiMo-V2.6-Flash | 1315 | hybrid | nvlink3 | infiniband_hdr | 143 | 597.69 us | 167.3 tok/s | 1,673.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 110.81 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x1315-expert | MiMo-V2.6-Flash | 1315 | expert | nvlink3 | infiniband_hdr | 192 | 675.11 us | 148.1 tok/s | 1,481.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.04 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.07 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x8562-pipeline | MiMo-V2.6-Flash | 8562 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x8562-tensor | MiMo-V2.6-Flash | 8562 | tensor | nvlink3 | infiniband_hdr | 192 | 1,360.69 us | 73.5 tok/s | 734.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 1071 on infiniband_hdr (traversals 4.0) = 873.80 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x8562-hybrid | MiMo-V2.6-Flash | 8562 | hybrid | nvlink3 | infiniband_hdr | 143 | 597.69 us | 167.3 tok/s | 1,673.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 110.81 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x8562-expert | MiMo-V2.6-Flash | 8562 | expert | nvlink3 | infiniband_hdr | 192 | 674.92 us | 148.2 tok/s | 1,481.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.01 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 194.91 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Flash | 1 | array | array | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x94 | 76,610 | 8,385.5 | 0.109 | 8,385.5 (76,610) | 4,454.4 (92,450) | 0.53x | link_latency |
| MiMo-V2.6-Flash | 2 | wafer | wafer | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | 7,072,425 | 2,122.8 | 0.000 | — (—) | 2,122.8 (7,072,425) | — | link_latency |
| MiMo-V2.6-Flash | 4 | wafer | wafer | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | 7,072,425 | 2,028.0 | 0.000 | — (—) | 2,028.0 (7,072,425) | — | link_latency |
| MiMo-V2.6-Flash | 8 | wafer | wafer | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | 7,072,425 | 1,861.8 | 0.000 | — (—) | 1,861.8 (7,072,425) | — | link_latency |
| MiMo-V2.6-Flash | 16 | wafer | wafer | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | 7,072,425 | 1,599.6 | 0.000 | — (—) | 1,599.6 (7,072,425) | — | link_latency |
| MiMo-V2.6-Flash | 32 | wafer | wafer | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | 7,072,425 | 1,248.1 | 0.000 | — (—) | 1,248.1 (7,072,425) | — | link_latency |
| MiMo-V2.6-Flash | 64 | wafer | wafer | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153 | 7,072,425 | 867.0 | 0.000 | — (—) | 867.0 (7,072,425) | — | kv_read |
| MiMo-V2.6-Flash | 256 | wafer | wafer | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 342.7 | 0.000 | — (—) | 342.7 (7,072,425) | — | kv_read |
| MiMo-V2.6-Flash | 1024 | wafer | wafer | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 90.3 | 0.000 | — (—) | 90.3 (7,072,425) | — | kv_read |
| MiMo-V2.6-Flash | 4096 | wafer | wafer | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 22.9 | 0.000 | — (—) | 22.9 (7,072,425) | — | kv_read |

## The two ROM floorplans on one die

This probe requests 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. Both machines hold the requested weights. They are different floorplans, not one floorplan with two arithmetics.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 481.6 mm2 | 256.8 mm2 |
| weight capacity | 3.51 GB (100.0%) | 3.51 GB (100.0%) |
| capacity-feasible | yes | yes |
| compute block | 186.7 mm2 | 146.7 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 264.8 mm2 |
| sustained fp8 compute roof | 9.154e+13 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 4.577e+13 | n/a |
| weight bytes/s the array supplies | 1.019e+14 | 1.019e+14 |
| **can the compute block be fed?** | **2.23x** | there is nothing to feed |
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

The ROM-plus-MAC machine is not bandwidth-starved at this point:
its array supplies 2.23x the bytes its MAC
roof demands, so the fp8 compute block can be fully fed and the
remaining array bandwidth is unused.

## Sizing one expert region

The per-region machine's cost is not arithmetic; it is a
pre-compute block and an activation distribution network per
region. The block is small against the array it serves. The
distribution network is the real cost and this model does not
price it.

| Model | Experts | Routed bytes/expert | One region | Pre-compute/region | All regions | All pre-compute | Whole checkpoint |
|---|---:|---:|---:|---:|---:|---:|---:|
| MiMo-V2.6-Flash | 256 | 628.4 MB | 137.8 mm2 | 24.81 mm2 (18.0%) | 35,280 mm2 | 6,350 mm2 | 37,926 mm2 = 46.5 reticles |

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
| MiMo-V2.6-Flash | 1 | sram | 83,866.5 | 25,249.6 | 25,249.6 | 3.32x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 2 | sram | 83,866.5 | 25,249.6 | 25,249.6 | 3.32x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 4 | sram | 83,866.5 | 25,249.6 | 25,249.6 | 3.32x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 8 | sram | 83,866.5 | 25,249.6 | 25,249.6 | 3.32x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 16 | sram | 83,866.5 | 25,249.6 | 25,593.9 | 3.32x | 1.01x | kv_read | weight_read | link_latency |
| MiMo-V2.6-Flash | 32 | sram | 83,866.5 | 25,249.6 | 39,939.0 | 3.32x | 1.58x | kv_read | weight_read | link_latency |
| MiMo-V2.6-Flash | 64 | sram | 83,866.5 | 25,249.6 | 55,489.5 | 3.32x | 2.20x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 256 | sram | 87,743.2 | 25,589.9 | 78,377.0 | 3.43x | 3.06x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 1024 | sram | 92,507.1 | 25,980.1 | 87,388.1 | 3.56x | 3.36x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 4096 | sram | 93,780.0 | 26,079.6 | 93,780.0 | 3.60x | 3.60x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 1 | rom | 83,866.5 | 83,866.5 | 83,866.5 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 2 | rom | 83,866.5 | 83,866.5 | 83,866.5 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 4 | rom | 83,866.5 | 83,866.5 | 83,866.5 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 8 | rom | 83,866.5 | 83,866.5 | 83,866.5 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 16 | rom | 83,866.5 | 83,866.5 | 83,866.5 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 32 | rom | 83,866.5 | 83,866.5 | 83,866.5 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 64 | rom | 83,866.5 | 83,866.5 | 83,866.5 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 256 | rom | 87,743.2 | 87,743.2 | 87,743.2 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 1024 | rom | 92,507.1 | 92,507.1 | 92,507.1 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 4096 | rom | 93,780.0 | 93,780.0 | 93,780.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| MiMo-V2.6-Flash | 1 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 1.00 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-romfill | 7,072,425 | 129.81 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream | 7,072,425 | 1.00 | 1.00 | 25,249.6 | 0.004 | weight_read | 0.30x |
| MiMo-V2.6-Flash | 1 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion | 7,072,425 | 1.00 | 1.00 | 25,249.6 | 0.004 | weight_read | 0.30x |
| MiMo-V2.6-Flash | 1 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 2 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 1.00 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 2 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-romfill | 7,072,425 | 129.81 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 2 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream | 7,072,425 | 1.00 | 1.00 | 25,249.6 | 0.004 | weight_read | 0.30x |
| MiMo-V2.6-Flash | 2 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 2 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion | 7,072,425 | 1.00 | 1.00 | 25,249.6 | 0.004 | weight_read | 0.30x |
| MiMo-V2.6-Flash | 2 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 1.00 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-romfill | 7,072,425 | 129.81 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream | 7,072,425 | 1.00 | 1.00 | 25,249.6 | 0.004 | weight_read | 0.30x |
| MiMo-V2.6-Flash | 4 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion | 7,072,425 | 1.00 | 1.00 | 25,249.6 | 0.004 | weight_read | 0.30x |
| MiMo-V2.6-Flash | 4 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 8 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 1.00 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 8 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-romfill | 7,072,425 | 129.81 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 8 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream | 7,072,425 | 1.00 | 1.00 | 25,249.6 | 0.004 | weight_read | 0.30x |
| MiMo-V2.6-Flash | 8 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 8 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion | 7,072,425 | 1.00 | 1.00 | 25,249.6 | 0.004 | weight_read | 0.30x |
| MiMo-V2.6-Flash | 8 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 16 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 1.00 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 16 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-romfill | 7,072,425 | 129.81 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 16 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream | 7,072,425 | 1.00 | 1.00 | 25,249.6 | 0.004 | weight_read | 0.30x |
| MiMo-V2.6-Flash | 16 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 16 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153-perregion | 7,072,425 | 1.00 | 3.27 | 25,593.9 | 0.004 | link_latency | 0.31x |
| MiMo-V2.6-Flash | 16 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 32 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 1.00 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 32 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-romfill | 7,072,425 | 129.81 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 32 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream | 7,072,425 | 1.00 | 1.00 | 25,249.6 | 0.004 | weight_read | 0.30x |
| MiMo-V2.6-Flash | 32 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 32 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153-perregion | 7,072,425 | 1.00 | 4.64 | 39,939.0 | 0.006 | link_latency | 0.48x |
| MiMo-V2.6-Flash | 32 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 64 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 1.00 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 64 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-romfill | 7,072,425 | 129.81 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 64 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream | 7,072,425 | 1.00 | 1.00 | 25,249.6 | 0.004 | weight_read | 0.30x |
| MiMo-V2.6-Flash | 64 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 64 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153-perregion | 7,072,425 | 1.00 | 6.85 | 55,489.5 | 0.008 | kv_read | 0.66x |
| MiMo-V2.6-Flash | 64 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion-romfill | 7,072,425 | 470.45 | 1.00 | 83,866.5 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 256 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 1.00 | 1.00 | 87,743.2 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 256 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-romfill | 7,072,425 | 129.81 | 1.00 | 87,743.2 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 256 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream | 7,072,425 | 1.00 | 1.67 | 25,589.9 | 0.004 | weight_read | 0.29x |
| MiMo-V2.6-Flash | 256 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream-romfill | 7,072,425 | 470.45 | 1.67 | 87,743.2 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 256 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153-perregion | 7,072,425 | 1.00 | 16.87 | 78,377.0 | 0.011 | kv_read | 0.89x |
| MiMo-V2.6-Flash | 256 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion-romfill | 7,072,425 | 470.45 | 1.15 | 87,743.2 | 0.012 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1024 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 1.00 | 1.00 | 92,507.1 | 0.013 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1024 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-romfill | 7,072,425 | 129.81 | 1.00 | 92,507.1 | 0.013 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1024 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream | 7,072,425 | 1.00 | 6.69 | 25,980.1 | 0.004 | weight_read | 0.28x |
| MiMo-V2.6-Flash | 1024 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream-romfill | 7,072,425 | 470.45 | 6.69 | 92,507.1 | 0.013 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1024 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x153-perregion | 7,072,425 | 1.00 | 48.79 | 87,388.1 | 0.012 | kv_read | 0.94x |
| MiMo-V2.6-Flash | 1024 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion-romfill | 7,072,425 | 470.45 | 2.19 | 92,507.1 | 0.013 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4096 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153 | 7,072,425 | 1.00 | 1.00 | 93,780.0 | 0.013 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4096 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-romfill | 7,072,425 | 129.81 | 1.00 | 93,780.0 | 0.013 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4096 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream | 7,072,425 | 1.00 | 26.77 | 26,079.6 | 0.004 | weight_read | 0.28x |
| MiMo-V2.6-Flash | 4096 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perstream-romfill | 7,072,425 | 470.45 | 26.77 | 93,780.0 | 0.013 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4096 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion | 7,072,425 | 1.00 | 4.23 | 93,780.0 | 0.013 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4096 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x153-perregion-romfill | 7,072,425 | 470.45 | 4.23 | 93,780.0 | 0.013 | kv_read | 1.00x |

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
| MiMo-V2.6-Flash | 1 | 33 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 4 | 8,678 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 8 | 8,678 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 16 | 8,678 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 32 | 8,678 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 64 | 8,678 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 256 | 8,678 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 1024 | 8,678 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 4096 | 8,678 | 1.00 | 1.000 | 1.000 | 1.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Flash | 1 | 33 | 7.20 | 5.07 | 1.42x |
| MiMo-V2.6-Flash | 2 | 33 | 12.67 | 6.90 | 1.84x |
| MiMo-V2.6-Flash | 4 | 33 | 20.10 | 9.20 | 2.18x |
| MiMo-V2.6-Flash | 8 | 33 | 27.36 | 11.74 | 2.33x |
| MiMo-V2.6-Flash | 16 | 33 | 31.57 | 14.23 | 2.22x |
| MiMo-V2.6-Flash | 32 | 33 | 32.78 | 16.34 | 2.01x |
| MiMo-V2.6-Flash | 64 | 33 | 32.96 | 17.71 | 1.86x |
| MiMo-V2.6-Flash | 1 | 35 | 7.24 | 5.14 | 1.41x |
| MiMo-V2.6-Flash | 2 | 35 | 12.83 | 7.02 | 1.83x |
| MiMo-V2.6-Flash | 4 | 35 | 20.56 | 9.41 | 2.18x |
| MiMo-V2.6-Flash | 8 | 35 | 28.37 | 12.06 | 2.35x |
| MiMo-V2.6-Flash | 16 | 35 | 33.18 | 14.69 | 2.26x |
| MiMo-V2.6-Flash | 32 | 35 | 34.69 | 16.92 | 2.05x |
| MiMo-V2.6-Flash | 64 | 35 | 34.94 | 18.39 | 1.90x |
| MiMo-V2.6-Flash | 1 | 47 | 7.43 | 5.53 | 1.34x |
| MiMo-V2.6-Flash | 2 | 47 | 13.50 | 7.62 | 1.77x |
| MiMo-V2.6-Flash | 4 | 47 | 22.63 | 10.50 | 2.15x |
| MiMo-V2.6-Flash | 8 | 47 | 33.33 | 13.76 | 2.42x |
| MiMo-V2.6-Flash | 16 | 47 | 41.75 | 17.11 | 2.44x |
| MiMo-V2.6-Flash | 32 | 47 | 45.60 | 20.05 | 2.27x |
| MiMo-V2.6-Flash | 64 | 47 | 46.61 | 22.02 | 2.12x |
| MiMo-V2.6-Flash | 1 | 56 | 7.52 | 5.76 | 1.31x |
| MiMo-V2.6-Flash | 2 | 56 | 13.84 | 7.98 | 1.73x |
| MiMo-V2.6-Flash | 4 | 56 | 23.69 | 11.17 | 2.12x |
| MiMo-V2.6-Flash | 8 | 56 | 36.10 | 14.80 | 2.44x |
| MiMo-V2.6-Flash | 16 | 56 | 47.08 | 18.63 | 2.53x |
| MiMo-V2.6-Flash | 32 | 56 | 53.05 | 22.06 | 2.40x |
| MiMo-V2.6-Flash | 64 | 56 | 54.98 | 24.39 | 2.25x |
| MiMo-V2.6-Flash | 1 | 58 | 7.53 | 5.80 | 1.30x |
| MiMo-V2.6-Flash | 2 | 58 | 13.90 | 8.05 | 1.73x |
| MiMo-V2.6-Flash | 4 | 58 | 23.89 | 11.30 | 2.11x |
| MiMo-V2.6-Flash | 8 | 58 | 36.63 | 15.01 | 2.44x |
| MiMo-V2.6-Flash | 16 | 58 | 48.15 | 18.95 | 2.54x |
| MiMo-V2.6-Flash | 32 | 58 | 54.61 | 22.48 | 2.43x |
| MiMo-V2.6-Flash | 64 | 58 | 56.79 | 24.88 | 2.28x |
| MiMo-V2.6-Flash | 1 | 63 | 7.57 | 5.90 | 1.28x |
| MiMo-V2.6-Flash | 2 | 63 | 14.03 | 8.22 | 1.71x |
| MiMo-V2.6-Flash | 4 | 63 | 24.35 | 11.62 | 2.10x |
| MiMo-V2.6-Flash | 8 | 63 | 37.86 | 15.51 | 2.44x |
| MiMo-V2.6-Flash | 16 | 63 | 50.67 | 19.69 | 2.57x |
| MiMo-V2.6-Flash | 32 | 63 | 58.38 | 23.47 | 2.49x |
| MiMo-V2.6-Flash | 64 | 63 | 61.21 | 26.06 | 2.35x |
| MiMo-V2.6-Flash | 1 | 70 | 7.61 | 6.03 | 1.26x |
| MiMo-V2.6-Flash | 2 | 70 | 14.19 | 8.44 | 1.68x |
| MiMo-V2.6-Flash | 4 | 70 | 24.89 | 12.01 | 2.07x |
| MiMo-V2.6-Flash | 8 | 70 | 39.36 | 16.15 | 2.44x |
| MiMo-V2.6-Flash | 16 | 70 | 53.86 | 20.66 | 2.61x |
| MiMo-V2.6-Flash | 32 | 70 | 63.32 | 24.77 | 2.56x |
| MiMo-V2.6-Flash | 64 | 70 | 67.15 | 27.62 | 2.43x |
| MiMo-V2.6-Flash | 1 | 72 | 7.62 | 6.07 | 1.26x |
| MiMo-V2.6-Flash | 2 | 72 | 14.24 | 8.51 | 1.67x |
| MiMo-V2.6-Flash | 4 | 72 | 25.02 | 12.12 | 2.06x |
| MiMo-V2.6-Flash | 8 | 72 | 39.75 | 16.32 | 2.44x |
| MiMo-V2.6-Flash | 16 | 72 | 54.70 | 20.92 | 2.61x |
| MiMo-V2.6-Flash | 32 | 72 | 64.67 | 25.12 | 2.57x |
| MiMo-V2.6-Flash | 64 | 72 | 68.79 | 28.04 | 2.45x |
| MiMo-V2.6-Flash | 1 | 74 | 7.63 | 6.10 | 1.25x |
| MiMo-V2.6-Flash | 2 | 74 | 14.27 | 8.56 | 1.67x |
| MiMo-V2.6-Flash | 4 | 74 | 25.15 | 12.22 | 2.06x |
| MiMo-V2.6-Flash | 8 | 74 | 40.12 | 16.49 | 2.43x |
| MiMo-V2.6-Flash | 16 | 74 | 55.52 | 21.18 | 2.62x |
| MiMo-V2.6-Flash | 32 | 74 | 65.98 | 25.47 | 2.59x |
| MiMo-V2.6-Flash | 64 | 74 | 70.41 | 28.46 | 2.47x |
| MiMo-V2.6-Flash | 1 | 75 | 7.64 | 6.12 | 1.25x |
| MiMo-V2.6-Flash | 2 | 75 | 14.29 | 8.59 | 1.66x |
| MiMo-V2.6-Flash | 4 | 75 | 25.22 | 12.27 | 2.06x |
| MiMo-V2.6-Flash | 8 | 75 | 40.30 | 16.57 | 2.43x |
| MiMo-V2.6-Flash | 16 | 75 | 55.92 | 21.30 | 2.62x |
| MiMo-V2.6-Flash | 32 | 75 | 66.62 | 25.64 | 2.60x |
| MiMo-V2.6-Flash | 64 | 75 | 71.21 | 28.66 | 2.48x |
| MiMo-V2.6-Flash | 1 | 77 | 7.65 | 6.15 | 1.24x |
| MiMo-V2.6-Flash | 2 | 77 | 14.33 | 8.65 | 1.66x |
| MiMo-V2.6-Flash | 4 | 77 | 25.34 | 12.37 | 2.05x |
| MiMo-V2.6-Flash | 8 | 77 | 40.65 | 16.73 | 2.43x |
| MiMo-V2.6-Flash | 16 | 77 | 56.69 | 21.55 | 2.63x |
| MiMo-V2.6-Flash | 32 | 77 | 67.89 | 25.98 | 2.61x |
| MiMo-V2.6-Flash | 64 | 77 | 72.80 | 29.07 | 2.50x |
| MiMo-V2.6-Flash | 1 | 93 | 7.71 | 6.37 | 1.21x |
| MiMo-V2.6-Flash | 2 | 93 | 14.56 | 9.07 | 1.60x |
| MiMo-V2.6-Flash | 4 | 93 | 26.14 | 13.04 | 2.01x |
| MiMo-V2.6-Flash | 8 | 93 | 43.01 | 17.88 | 2.40x |
| MiMo-V2.6-Flash | 16 | 93 | 62.11 | 23.34 | 2.66x |
| MiMo-V2.6-Flash | 32 | 93 | 77.09 | 28.45 | 2.71x |
| MiMo-V2.6-Flash | 64 | 93 | 84.60 | 32.05 | 2.64x |
| MiMo-V2.6-Flash | 256 | 93 | 87.15 | 33.74 | 2.58x |
| MiMo-V2.6-Flash | 1 | 111 | 7.75 | 6.56 | 1.18x |
| MiMo-V2.6-Flash | 2 | 111 | 14.75 | 9.49 | 1.55x |
| MiMo-V2.6-Flash | 4 | 111 | 26.80 | 13.64 | 1.97x |
| MiMo-V2.6-Flash | 8 | 111 | 44.99 | 19.00 | 2.37x |
| MiMo-V2.6-Flash | 16 | 111 | 66.89 | 25.09 | 2.67x |
| MiMo-V2.6-Flash | 32 | 111 | 85.68 | 30.85 | 2.78x |
| MiMo-V2.6-Flash | 64 | 111 | 96.17 | 34.99 | 2.75x |
| MiMo-V2.6-Flash | 256 | 111 | 100.05 | 36.94 | 2.71x |
| MiMo-V2.6-Flash | 1 | 112 | 7.75 | 6.57 | 1.18x |
| MiMo-V2.6-Flash | 2 | 112 | 14.75 | 9.51 | 1.55x |
| MiMo-V2.6-Flash | 4 | 112 | 26.83 | 13.67 | 1.96x |
| MiMo-V2.6-Flash | 8 | 112 | 45.08 | 19.06 | 2.37x |
| MiMo-V2.6-Flash | 16 | 112 | 67.12 | 25.18 | 2.67x |
| MiMo-V2.6-Flash | 32 | 112 | 86.11 | 30.98 | 2.78x |
| MiMo-V2.6-Flash | 64 | 112 | 96.77 | 35.14 | 2.75x |
| MiMo-V2.6-Flash | 256 | 112 | 100.72 | 37.11 | 2.71x |
| MiMo-V2.6-Flash | 1 | 117 | 7.76 | 6.61 | 1.17x |
| MiMo-V2.6-Flash | 2 | 117 | 14.80 | 9.61 | 1.54x |
| MiMo-V2.6-Flash | 4 | 117 | 26.97 | 13.81 | 1.95x |
| MiMo-V2.6-Flash | 8 | 117 | 45.53 | 19.34 | 2.35x |
| MiMo-V2.6-Flash | 16 | 117 | 68.24 | 25.62 | 2.66x |
| MiMo-V2.6-Flash | 32 | 117 | 88.20 | 31.59 | 2.79x |
| MiMo-V2.6-Flash | 64 | 117 | 99.66 | 35.89 | 2.78x |
| MiMo-V2.6-Flash | 256 | 117 | 103.99 | 37.92 | 2.74x |
| MiMo-V2.6-Flash | 1 | 132 | 7.79 | 6.73 | 1.16x |
| MiMo-V2.6-Flash | 2 | 132 | 14.90 | 9.91 | 1.50x |
| MiMo-V2.6-Flash | 4 | 132 | 27.35 | 14.19 | 1.93x |
| MiMo-V2.6-Flash | 8 | 132 | 46.70 | 20.15 | 2.32x |
| MiMo-V2.6-Flash | 16 | 132 | 71.21 | 26.85 | 2.65x |
| MiMo-V2.6-Flash | 32 | 132 | 93.88 | 33.30 | 2.82x |
| MiMo-V2.6-Flash | 64 | 132 | 107.68 | 37.99 | 2.83x |
| MiMo-V2.6-Flash | 256 | 132 | 113.15 | 40.22 | 2.81x |
| MiMo-V2.6-Flash | 1 | 133 | 7.79 | 6.74 | 1.16x |
| MiMo-V2.6-Flash | 2 | 133 | 14.91 | 9.93 | 1.50x |
| MiMo-V2.6-Flash | 4 | 133 | 27.37 | 14.22 | 1.93x |
| MiMo-V2.6-Flash | 8 | 133 | 46.77 | 20.20 | 2.32x |
| MiMo-V2.6-Flash | 16 | 133 | 71.39 | 26.92 | 2.65x |
| MiMo-V2.6-Flash | 32 | 133 | 94.22 | 33.41 | 2.82x |
| MiMo-V2.6-Flash | 64 | 133 | 108.18 | 38.12 | 2.84x |
| MiMo-V2.6-Flash | 256 | 133 | 113.72 | 40.37 | 2.82x |
| MiMo-V2.6-Flash | 1 | 134 | 7.79 | 6.74 | 1.16x |
| MiMo-V2.6-Flash | 2 | 134 | 14.91 | 9.94 | 1.50x |
| MiMo-V2.6-Flash | 4 | 134 | 27.39 | 14.24 | 1.92x |
| MiMo-V2.6-Flash | 8 | 134 | 46.84 | 20.25 | 2.31x |
| MiMo-V2.6-Flash | 16 | 134 | 71.57 | 27.00 | 2.65x |
| MiMo-V2.6-Flash | 32 | 134 | 94.57 | 33.51 | 2.82x |
| MiMo-V2.6-Flash | 64 | 134 | 108.68 | 38.25 | 2.84x |
| MiMo-V2.6-Flash | 256 | 134 | 114.30 | 40.51 | 2.82x |
| MiMo-V2.6-Flash | 1 | 138 | 7.80 | 6.77 | 1.15x |
| MiMo-V2.6-Flash | 2 | 138 | 14.94 | 10.02 | 1.49x |
| MiMo-V2.6-Flash | 4 | 138 | 27.48 | 14.33 | 1.92x |
| MiMo-V2.6-Flash | 8 | 138 | 47.11 | 20.45 | 2.30x |
| MiMo-V2.6-Flash | 16 | 138 | 72.26 | 27.30 | 2.65x |
| MiMo-V2.6-Flash | 32 | 138 | 95.92 | 33.93 | 2.83x |
| MiMo-V2.6-Flash | 64 | 138 | 110.63 | 38.77 | 2.85x |
| MiMo-V2.6-Flash | 256 | 138 | 116.54 | 41.08 | 2.84x |
| MiMo-V2.6-Flash | 1 | 139 | 7.80 | 6.78 | 1.15x |
| MiMo-V2.6-Flash | 2 | 139 | 14.94 | 10.03 | 1.49x |
| MiMo-V2.6-Flash | 4 | 139 | 27.50 | 14.36 | 1.92x |
| MiMo-V2.6-Flash | 8 | 139 | 47.18 | 20.49 | 2.30x |
| MiMo-V2.6-Flash | 16 | 139 | 72.43 | 27.37 | 2.65x |
| MiMo-V2.6-Flash | 32 | 139 | 96.25 | 34.04 | 2.83x |
| MiMo-V2.6-Flash | 64 | 139 | 111.11 | 38.90 | 2.86x |
| MiMo-V2.6-Flash | 256 | 139 | 117.10 | 41.23 | 2.84x |
| MiMo-V2.6-Flash | 1 | 141 | 7.80 | 6.79 | 1.15x |
| MiMo-V2.6-Flash | 2 | 141 | 14.95 | 10.07 | 1.48x |
| MiMo-V2.6-Flash | 4 | 141 | 27.54 | 14.40 | 1.91x |
| MiMo-V2.6-Flash | 8 | 141 | 47.30 | 20.59 | 2.30x |
| MiMo-V2.6-Flash | 16 | 141 | 72.76 | 27.52 | 2.64x |
| MiMo-V2.6-Flash | 32 | 141 | 96.90 | 34.24 | 2.83x |
| MiMo-V2.6-Flash | 64 | 141 | 112.05 | 39.15 | 2.86x |
| MiMo-V2.6-Flash | 256 | 141 | 118.19 | 41.51 | 2.85x |
| MiMo-V2.6-Flash | 1 | 143 | 7.81 | 6.80 | 1.15x |
| MiMo-V2.6-Flash | 2 | 143 | 14.96 | 10.10 | 1.48x |
| MiMo-V2.6-Flash | 4 | 143 | 27.58 | 14.45 | 1.91x |
| MiMo-V2.6-Flash | 8 | 143 | 47.43 | 20.69 | 2.29x |
| MiMo-V2.6-Flash | 16 | 143 | 73.08 | 27.66 | 2.64x |
| MiMo-V2.6-Flash | 32 | 143 | 97.54 | 34.44 | 2.83x |
| MiMo-V2.6-Flash | 64 | 143 | 112.98 | 39.40 | 2.87x |
| MiMo-V2.6-Flash | 256 | 143 | 119.27 | 41.78 | 2.85x |
| MiMo-V2.6-Flash | 1 | 168 | 7.84 | 6.95 | 1.13x |
| MiMo-V2.6-Flash | 2 | 168 | 15.08 | 10.51 | 1.43x |
| MiMo-V2.6-Flash | 4 | 168 | 27.99 | 14.95 | 1.87x |
| MiMo-V2.6-Flash | 8 | 168 | 48.76 | 21.79 | 2.24x |
| MiMo-V2.6-Flash | 16 | 168 | 76.60 | 29.28 | 2.62x |
| MiMo-V2.6-Flash | 32 | 168 | 104.63 | 36.76 | 2.85x |
| MiMo-V2.6-Flash | 64 | 168 | 123.48 | 42.32 | 2.92x |
| MiMo-V2.6-Flash | 256 | 168 | 131.55 | 44.99 | 2.92x |
| MiMo-V2.6-Flash | 1 | 185 | 7.85 | 7.02 | 1.12x |
| MiMo-V2.6-Flash | 2 | 185 | 15.14 | 10.75 | 1.41x |
| MiMo-V2.6-Flash | 4 | 185 | 28.21 | 15.26 | 1.85x |
| MiMo-V2.6-Flash | 8 | 185 | 49.48 | 22.45 | 2.20x |
| MiMo-V2.6-Flash | 16 | 185 | 78.55 | 30.24 | 2.60x |
| MiMo-V2.6-Flash | 32 | 185 | 108.66 | 38.18 | 2.85x |
| MiMo-V2.6-Flash | 64 | 185 | 129.59 | 44.13 | 2.94x |
| MiMo-V2.6-Flash | 256 | 185 | 138.79 | 46.95 | 2.96x |
| MiMo-V2.6-Flash | 1 | 224 | 7.88 | 7.17 | 1.10x |
| MiMo-V2.6-Flash | 2 | 224 | 15.24 | 11.23 | 1.36x |
| MiMo-V2.6-Flash | 4 | 224 | 28.60 | 15.89 | 1.80x |
| MiMo-V2.6-Flash | 8 | 224 | 50.75 | 23.72 | 2.14x |
| MiMo-V2.6-Flash | 16 | 224 | 82.06 | 32.12 | 2.55x |
| MiMo-V2.6-Flash | 32 | 224 | 116.13 | 41.10 | 2.83x |
| MiMo-V2.6-Flash | 64 | 224 | 141.20 | 47.76 | 2.96x |
| MiMo-V2.6-Flash | 256 | 224 | 152.72 | 50.99 | 3.00x |
| MiMo-V2.6-Flash | 1 | 335 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Flash | 2 | 335 | 15.41 | 12.20 | 1.26x |
| MiMo-V2.6-Flash | 4 | 335 | 29.22 | 17.38 | 1.68x |
| MiMo-V2.6-Flash | 8 | 335 | 52.84 | 26.01 | 2.03x |
| MiMo-V2.6-Flash | 16 | 335 | 88.02 | 36.44 | 2.42x |
| MiMo-V2.6-Flash | 32 | 335 | 129.41 | 47.38 | 2.73x |
| MiMo-V2.6-Flash | 64 | 335 | 162.72 | 55.62 | 2.93x |
| MiMo-V2.6-Flash | 256 | 335 | 179.13 | 59.69 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 335 | 179.16 | 59.70 | 3.00x |
| MiMo-V2.6-Flash | 1 | 336 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Flash | 2 | 336 | 15.41 | 12.20 | 1.26x |
| MiMo-V2.6-Flash | 4 | 336 | 29.23 | 17.40 | 1.68x |
| MiMo-V2.6-Flash | 8 | 336 | 52.85 | 26.03 | 2.03x |
| MiMo-V2.6-Flash | 16 | 336 | 88.06 | 36.47 | 2.41x |
| MiMo-V2.6-Flash | 32 | 336 | 129.49 | 47.43 | 2.73x |
| MiMo-V2.6-Flash | 64 | 336 | 162.86 | 55.68 | 2.93x |
| MiMo-V2.6-Flash | 256 | 336 | 179.31 | 59.75 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 336 | 179.34 | 59.76 | 3.00x |
| MiMo-V2.6-Flash | 1 | 448 | 7.94 | 7.55 | 1.05x |
| MiMo-V2.6-Flash | 2 | 448 | 15.49 | 12.84 | 1.21x |
| MiMo-V2.6-Flash | 4 | 448 | 29.55 | 18.62 | 1.59x |
| MiMo-V2.6-Flash | 8 | 448 | 53.95 | 27.39 | 1.97x |
| MiMo-V2.6-Flash | 16 | 448 | 91.28 | 39.89 | 2.29x |
| MiMo-V2.6-Flash | 32 | 448 | 136.98 | 51.59 | 2.66x |
| MiMo-V2.6-Flash | 64 | 448 | 175.48 | 61.76 | 2.84x |
| MiMo-V2.6-Flash | 256 | 448 | 195.13 | 66.41 | 2.94x |
| MiMo-V2.6-Flash | 1024 | 448 | 195.17 | 66.42 | 2.94x |
| MiMo-V2.6-Flash | 1 | 672 | 7.96 | 7.69 | 1.03x |
| MiMo-V2.6-Flash | 2 | 672 | 15.58 | 13.60 | 1.15x |
| MiMo-V2.6-Flash | 4 | 672 | 29.87 | 20.51 | 1.46x |
| MiMo-V2.6-Flash | 8 | 672 | 55.08 | 29.30 | 1.88x |
| MiMo-V2.6-Flash | 16 | 672 | 94.67 | 44.33 | 2.14x |
| MiMo-V2.6-Flash | 32 | 672 | 145.08 | 58.07 | 2.50x |
| MiMo-V2.6-Flash | 64 | 672 | 189.49 | 69.57 | 2.72x |
| MiMo-V2.6-Flash | 256 | 672 | 212.96 | 75.92 | 2.81x |
| MiMo-V2.6-Flash | 1024 | 672 | 213.01 | 75.93 | 2.81x |
| MiMo-V2.6-Flash | 1 | 1315 | 7.98 | 7.84 | 1.02x |
| MiMo-V2.6-Flash | 2 | 1315 | 15.66 | 14.52 | 1.08x |
| MiMo-V2.6-Flash | 4 | 1315 | 30.19 | 23.68 | 1.27x |
| MiMo-V2.6-Flash | 8 | 1315 | 56.21 | 33.48 | 1.68x |
| MiMo-V2.6-Flash | 16 | 1315 | 98.15 | 49.32 | 1.99x |
| MiMo-V2.6-Flash | 32 | 1315 | 153.63 | 70.24 | 2.19x |
| MiMo-V2.6-Flash | 64 | 1315 | 204.72 | 84.20 | 2.43x |
| MiMo-V2.6-Flash | 256 | 1315 | 232.64 | 90.89 | 2.56x |
| MiMo-V2.6-Flash | 1024 | 1315 | 232.70 | 90.91 | 2.56x |
| MiMo-V2.6-Flash | 1 | 8562 | 8.00 | 7.98 | 1.00x |
| MiMo-V2.6-Flash | 2 | 8562 | 15.74 | 15.54 | 1.01x |
| MiMo-V2.6-Flash | 4 | 8562 | 30.48 | 29.04 | 1.05x |
| MiMo-V2.6-Flash | 8 | 8562 | 57.23 | 48.99 | 1.17x |
| MiMo-V2.6-Flash | 16 | 8562 | 101.36 | 70.24 | 1.44x |
| MiMo-V2.6-Flash | 32 | 8562 | 161.78 | 91.09 | 1.78x |
| MiMo-V2.6-Flash | 64 | 8562 | 219.59 | 113.20 | 1.94x |
| MiMo-V2.6-Flash | 256 | 8562 | 252.15 | 127.16 | 1.98x |
| MiMo-V2.6-Flash | 1024 | 8562 | 252.23 | 127.19 | 1.98x |
| MiMo-V2.6-Flash | 4096 | 8562 | 252.23 | 127.19 | 1.98x |

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
| gpu | MiMo-V2.6-Flash | 1 | 10.83 | 1.0% |
| rom | MiMo-V2.6-Flash | 1 | 10.83 | 11.9% |

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
| MiMo-V2.6-Flash | 1 | 33 | 99.14% | 303.40 | 9.27 |
| MiMo-V2.6-Flash | 2 | 1 | 38.13% | 201.55 | 9.27 |

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
| MiMo-V2.6-Flash | 1 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 10.9 | 44,581.0 |
| MiMo-V2.6-Flash | 2 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 10.9 | 44,581.0 |
| MiMo-V2.6-Flash | 4 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 10.9 | 44,581.0 |
| MiMo-V2.6-Flash | 8 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 10.9 | 44,581.0 |
| MiMo-V2.6-Flash | 16 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 10.9 | 44,581.0 |
| MiMo-V2.6-Flash | 32 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 10.9 | 44,581.0 |
| MiMo-V2.6-Flash | 64 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 10.9 | 44,581.0 |
| MiMo-V2.6-Flash | 256 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 10.9 | 44,581.0 |
| MiMo-V2.6-Flash | 1024 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 10.9 | 44,581.0 |
| MiMo-V2.6-Flash | 4096 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 10.9 | 44,581.0 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 261 |
| gpu | kv_read | 632 |
| gpu | link_latency | 196 |
| gpu | weight_read | 151 |
| rom | compute | 88 |
| rom | infeasible | 2804 |
| rom | kv_read | 131 |
| rom | link_latency | 190 |
| rom | weight_read | 87 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 261 |
| rom | CAPACITY | 2804 |

## Mechanical consistency audit

**FAIL** over 55,065 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x59', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x64', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x71', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x75', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x94', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x119', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x134', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x135', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x136', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x141', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x188', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x59', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x64', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x71', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x75', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x94', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x119', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x134', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x135', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x136', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x141', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x188', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x59', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x64', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x71', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x75', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x94', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x119', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x134', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x135', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x136', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x141', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x188', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x59', 'MiMo-V2.6-Flash', 1)

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

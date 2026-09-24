# Area-constrained roofline: n6_vs_a100-qwen3-8b-200k

> CANDIDATE MODEL under n6_vs_a100: Qwen3-8B at 200,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 3,857x (ROM-N6-native-HBMKV-wafer-pipeline-x196, 11,117 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 50 devices. On the GPU side the correction reaches 42x (a100_sxm_80gb-x10969-pipeline, 10,969 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 168 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Qwen3-8B takes 27 x 815 mm2 (22,005 mm2, array, KV in SRAM) at 5,558 tok/s per user and 253 tok/s per 1,000 mm2, holding 1 session, against 27 copies of one unified HBM die at the same silicon: 14.9x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Qwen3-8B on 26,080 mm2 of ROM silicon at 6,521 tok/s per user against 26,432 mm2 of a100_sxm_80gb-x32-tensor at 397 tok/s: **16.4x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 77. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 15.26x to it.** At 185,005 mm2 on Qwen3-8B the pipeline-only GPU delivers 36.13 tok/s and the same silicon running tensor delivers 551 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (Qwen3-8B, ROM binding on `weight_read`) to 0.20x (Qwen3-8B, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,021 us over NVLink, capping per-user decode at 980 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 344.8 us and cap it at 2,900 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 5.1x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
9. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 9 of 10 operating points and an array 1; on tokens per second per square millimetre the same points go 1 to the array and 9 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
10. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 416 of 937 feasible points.
11. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 3.6x of aggregate throughput (Qwen3-8B). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
12. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 1.00x, on Qwen3-8B at batch 1, where the busiest region carries 1.00x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
13. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
14. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 79% of its cooling budget. The companion study at the other node does have power-limited points.


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

### Qwen3-8B at 200,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x27`** -- 27 x 815 mm2 reticle dies, 22,005 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **5,557.8 tok/s per user** (0.18 ms/token), binding on `layer_fixed_latency`
- **252.6 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 5,558 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 2,179 W at 0.099 W/mm2, 392.1 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 27 copies of one unified HBM die -- `a100_sxm_80gb-x27-tensor`, 22,302 mm2, area ratio 0.9867 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 22,005 | 22,302 | 0.9867 |
| user tok/s | 5,557.8 | 374.0 | 14.86x |
| aggregate tok/s | 5,558 | 374 | 5.69x |
| resident sessions | 1 | 65 | -- |
| J/token | 0.3921 | 15.1182 | 38.6x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 65 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x224-tensor` at 185,024 mm2 and 551.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-array-hw-hybrid-x50-romfill` | 40,750 | 7,163.3 | 175.8 | 1 | 16.00x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 46,455 | 7,166.0 | 154.3 | 1 | 15.52x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x24-romfill` | 19,560 | 4,611.6 | 235.8 | 1 | 12.87x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x27` | 22,005 | 5,557.8 | 252.6 | 1 | 14.86x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x27` | 22,005 | 5,557.8 | 252.6 | -- | 252.6 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x32` | 26,080 | 6,520.9 | 250.0 | 236.3 | 252.6 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x50-romfill` | 40,750 | 7,163.3 | 175.8 | 85.6 | 252.6 | stop |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 46,455 | 7,166.0 | 154.3 | 65.8 | 252.6 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x27` **<-- recommended** | 22,005 | 27 | 5,557.8 | 5,558 | 252.6 | 1 | `layer_fixed_latency` | 2,179 | 392.1 | `a100_sxm_80gb-x27-tensor` | 14.86x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x32` | 26,080 | 32 | 6,520.9 | 6,521 | 250.0 | 1 | `layer_fixed_latency` | 2,860 | 438.6 | `a100_sxm_80gb-x32-tensor` | 16.41x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x50-romfill` | 40,750 | 50 | 7,163.3 | 7,163 | 175.8 | 1 | `layer_fixed_latency` | 3,738 | 521.8 | `a100_sxm_80gb-x49-tensor` | 16.00x |
| `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 46,455 | 57 | 7,166.0 | 7,166 | 154.3 | 1 | `layer_fixed_latency` | 4,250 | 593.1 | `a100_sxm_80gb-x56-tensor` | 15.52x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 144 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x27` | 22,005 | 5,557.8 | 252.6 | 1 |
| array | 144 | fastest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 46,455 | 7,166.0 | 154.3 | 1 |
| array | 144 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x24-romfill` | 19,560 | 4,611.6 | 235.8 | 1 |
| wafer | 46 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,894.8 | 105.9 | 1 |
| wafer | 46 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,071.3 | 54.9 | 1 |
| wafer | 46 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 46,225 | 4,894.8 | 105.9 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill` | 46,455 | 7,166.0 | 7,166 | 1 | 4,250 | 593.1 | `layer_fixed_latency` | `a100_sxm_80gb-x56-tensor` | 461.8 | 136 | 22,203.9 | 1.004 | 15.52x | 37.4x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,071.3 | 5,071 | 1 | 8,183 | 1,613.6 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 517.9 | 272 | 35,919.4 | 0.999 | 9.79x | 22.3x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-hybrid-x113-romfill` | 92,095 | 6,494.8 | 6,495 | 1 | 8,284 | 1,275.5 | `layer_fixed_latency` | `a100_sxm_80gb-x111-tensor` | 517.3 | 270 | 35,675.5 | 1.004 | 12.55x | 28.0x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,071.3 | -- | 1 | -- | 1,613.6 | -- | -- | -- | -- | -- | 0.996 | 0.78x wafer/array | -- |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 9,060,100 | 1,787.0 | 3,574 | 4,115 | 853,546 | 238,819.9 | `link_latency` | `a100_sxm_80gb-x10969-tensor` | 475.1 | 26,779 | 1,670,624.7 | 1.000 | 3.76x | 7.0x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 9,060,100 | 1,683.6 | 6,734 | 4,115 | 1,357,948 | 201,645.6 | `link_latency` | `a100_sxm_80gb-x10969-hybrid` | 456.0 | 26,779 | 872,898.0 | 1.000 | 3.69x | 4.3x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 9,060,100 | 1,484.4 | 11,875 | 4,115 | 1,373,909 | 115,693.5 | `link_latency` | `a100_sxm_80gb-x10969-hybrid` | 456.0 | 26,779 | 438,796.9 | 1.000 | 3.26x | 3.8x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 9,060,100 | 1,190.3 | 19,044 | 4,115 | 1,396,166 | 73,311.4 | `link_latency` | `a100_sxm_80gb-x10969-hybrid` | 456.0 | 26,779 | 221,746.4 | 1.000 | 2.61x | 3.0x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 9,060,100 | 1,160.4 | 56,860 | 4,115 | 1,019,247 | 25,796.8 | `kv_read` | `a100_sxm_80gb-x10969-hybrid` | 456.0 | 26,779 | 113,221.1 | 1.000 | 2.54x | 4.4x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 9,060,100 | 970.9 | 62,139 | 4,115 | 1,035,597 | 16,665.7 | `kv_read` | `a100_sxm_80gb-x10969-hybrid` | 456.0 | 26,779 | 58,958.5 | 1.000 | 2.13x | 3.5x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 9,060,100 | 342.6 | 87,702 | 4,115 | 1,115,054 | 12,714.2 | `kv_read` | `a100_sxm_80gb-x10969-hybrid` | 419.8 | 26,779 | 18,911.1 | 1.000 | 0.82x | 1.5x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 9,060,100 | 91.0 | 93,228 | 4,115 | 1,132,194 | 12,144.4 | `kv_read` | `a100_sxm_80gb-x10969-hybrid` | 256.3 | 26,779 | 9,671.9 | 1.000 | 0.36x | 0.8x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 9,060,100 | 23.0 | 94,205 | 4,115 | 1,135,231 | 12,050.7 | `kv_read` | `a100_sxm_80gb-x10969-hybrid` | 112.7 | 26,779 | 7,068.9 | 1.000 | 0.20x | 0.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x27` | 22,005 | array | SRAM | 1 |
| 2 | `ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 9,060,100 | wafer | HBM | 4,115 |
| 4-16 | `ROM-N6-native-HBMKV-wafer-tensor-x196` | 9,060,100 | wafer | HBM | 4,115 |
| 32-4096 | `ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 9,060,100 | wafer | HBM | 4,115 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Qwen3-8B | SRAM | rom | 24, 29, 31, 32, 38, 50, 57, 76, 113, 170, 227, 340 |
| Qwen3-8B | SRAM | sram | 24, 27, 29, 32, 33, 38, 57, 76, 113, 170, 227, 340 |

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
| Qwen3-8B | `ROM-N6-native-SRAMKV-array-hw-tensor-x27` | 1 | 27 | 2.03 | hierarchical | 113.81 | 36.91 | 35.39 | 41.11 | 5,557.8 |
| Qwen3-8B | `a100_sxm_80gb-x27-tensor` | 1 | 27 | 2.03 | hierarchical | 566.80 | 1,105.92 | 1,000.79 | 717.38 | 374.0 |
| Qwen3-8B | `a100_sxm_80gb-x27-tensor` | 64 | 27 | 2.03 | hierarchical | 566.80 | 6,432.05 | 42,665.58 | 4,386.83 | 20.1 |

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
(4.327e+11 B/s/mm2).

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

- **0 of 937 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 79% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 180 | 0 | 73.7% | 79.0% | 0.383 | 49% |
| gpu | wafer (>=40,000 mm2) | 321 | 0 | 59.4% | 79.0% | 0.383 | 61% |
| rom | large array (5,000-40,000 mm2) | 126 | 0 | 15.0% | 22.8% | 0.114 | 94% |
| rom | wafer (>=40,000 mm2) | 310 | 0 | 17.6% | 36.0% | 0.180 | 95% |

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
| Qwen3-8B | 1 | 40,750 | `Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x50-romfill` | 0.521809 | 3,737.9 | layer_fixed_latency | `Qwen3-8B/a100_sxm_80gb-x49-tensor` | 20.503053 | 9,176.5 | link_latency | 39.29x |
| Qwen3-8B | 2 | 9,060,100 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196-romfill` | 238.819856 | 853,546.2 | link_latency | `Qwen3-8B/a100_sxm_80gb-x10969-tensor` | 1,670.624721 | 1,587,455.4 | link_latency | 7.00x |
| Qwen3-8B | 4 | 9,060,100 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196` | 201.645630 | 1,357,947.8 | link_latency | `Qwen3-8B/a100_sxm_80gb-x10969-hybrid` | 872.897973 | 1,952,089.5 | link_latency | 4.33x |
| Qwen3-8B | 8 | 9,060,100 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196` | 115.693545 | 1,373,909.1 | link_latency | `Qwen3-8B/a100_sxm_80gb-x10969-hybrid` | 438.796917 | 1,952,089.5 | link_latency | 3.79x |
| Qwen3-8B | 16 | 9,060,100 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196` | 73.311438 | 1,396,165.9 | link_latency | `Qwen3-8B/a100_sxm_80gb-x10969-hybrid` | 221.746389 | 1,952,089.5 | link_latency | 3.02x |
| Qwen3-8B | 32 | 9,060,100 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 25.796806 | 1,019,247.0 | kv_read | `Qwen3-8B/a100_sxm_80gb-x10969-hybrid` | 113.221125 | 1,952,089.5 | link_latency | 4.39x |
| Qwen3-8B | 64 | 9,060,100 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 16.665695 | 1,035,596.7 | kv_read | `Qwen3-8B/a100_sxm_80gb-x10969-hybrid` | 58.958493 | 1,952,089.5 | link_latency | 3.54x |
| Qwen3-8B | 256 | 9,060,100 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 12.714200 | 1,115,054.5 | kv_read | `Qwen3-8B/a100_sxm_80gb-x10969-hybrid` | 18.911145 | 2,032,287.3 | link_latency | 1.49x |
| Qwen3-8B | 1024 | 9,060,100 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 12.144407 | 1,132,193.9 | kv_read | `Qwen3-8B/a100_sxm_80gb-x10969-hybrid` | 9.671851 | 2,538,542.3 | kv_read | 0.80x |
| Qwen3-8B | 4096 | 9,060,100 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill` | 12.050658 | 1,135,231.5 | kv_read | `Qwen3-8B/a100_sxm_80gb-x10969-hybrid` | 7.068909 | 3,262,869.5 | kv_read | 0.59x |

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
| Qwen3-8B | 200,000 | 8 B | 16.4 GB | 16.00 | 29.491 GB | 29.491 GB | 0.5 |

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
| Qwen3-8B | 1 | 46,225 | 9,831.9 | wafer-pipeline | 4,894.8 | wafer-tensor | 2.01x | 877.9 | pipeline | 461.8 | tensor | 1.90x | 11.20x | 10.60x | 0.95x |
| Qwen3-8B | 2 | 92,450 | 11,190.0 | wafer-pipeline | 5,071.3 | wafer-hybrid | 2.21x | 1,113.7 | pipeline | 517.9 | tensor | 2.15x | 10.05x | 9.79x | 0.97x |
| Qwen3-8B | 3 | 138,675 | 11,159.2 | wafer-pipeline | 4,588.4 | wafer-hybrid | 2.43x | 1,223.3 | pipeline | 539.8 | tensor | 2.27x | 9.12x | 8.50x | 0.93x |
| Qwen3-8B | 4 | 184,900 | 11,143.4 | wafer-pipeline | 4,236.9 | wafer-hybrid | 2.63x | 1,286.6 | pipeline | 551.4 | tensor | 2.33x | 8.66x | 7.68x | 0.89x |
| Qwen3-8B | 6 | 277,350 | 11,126.2 | wafer-pipeline | 3,894.0 | wafer-hybrid | 2.86x | 1,356.8 | pipeline | 482.9 | tensor | 2.81x | 8.20x | 8.06x | 0.98x |
| Qwen3-8B | 8 | 369,800 | 11,116.5 | wafer-pipeline | 3,602.2 | wafer-hybrid | 3.09x | 1,394.8 | pipeline | 487.5 | tensor | 2.86x | 7.97x | 7.39x | 0.93x |
| Qwen3-8B | 12 | 554,700 | 11,106.7 | wafer-pipeline | 3,132.5 | wafer-hybrid | 3.55x | 1,435.1 | pipeline | 492.2 | tensor | 2.92x | 7.74x | 6.36x | 0.82x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.82x to 0.98x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x57-romfill | 46,455 | 7,166.0 | 7,166.0 | layer_fixed_latency | Qwen3-8B/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 1,116.03 | 461.8 | 461.8 | link_latency | 15.52x | 3.54x | 198.34x | 15.52x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x24-romfill | 19,560 | 4,611.6 | 4,611.6 | layer_fixed_latency | Qwen3-8B/a100_sxm_80gb-x24-tensor | 19,824 | 0.99x | tensor | 1,098.06 | 358.3 | 358.3 | link_latency | 12.87x | 5.31x | 127.50x | 12.87x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196-romfill | 9,060,100 | 1,787.0 | 3,574.0 | link_latency | Qwen3-8B/a100_sxm_80gb-x10969-tensor | 9,060,394 | 1.00x | tensor | 1,533.89 | 475.1 | 950.2 | link_latency | 3.76x | 0.01x | 49.46x | 3.76x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196 | 9,060,100 | 1,683.6 | 6,734.3 | link_latency | Qwen3-8B/a100_sxm_80gb-x10969-hybrid | 9,060,394 | 1.00x | hybrid | 1,202.27 | 456.0 | 78,439.4 | link_latency | 3.69x | 0.02x | 46.60x | 4.23x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196 | 9,060,100 | 1,484.4 | 11,875.4 | link_latency | Qwen3-8B/a100_sxm_80gb-x10969-hybrid | 9,060,394 | 1.00x | hybrid | 1,202.27 | 456.0 | 78,439.4 | link_latency | 3.26x | 0.03x | 41.09x | 3.73x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196 | 9,060,100 | 1,190.3 | 19,044.3 | link_latency | Qwen3-8B/a100_sxm_80gb-x10969-hybrid | 9,060,394 | 1.00x | hybrid | 1,202.27 | 456.0 | 78,439.4 | link_latency | 2.61x | 0.05x | 32.94x | 2.99x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 1,160.4 | 56,859.5 | kv_read | Qwen3-8B/a100_sxm_80gb-x10969-hybrid | 9,060,394 | 1.00x | hybrid | 1,202.27 | 456.0 | 78,439.4 | link_latency | 2.54x | 0.14x | 32.12x | 2.92x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 970.9 | 62,139.4 | kv_read | Qwen3-8B/a100_sxm_80gb-x10969-hybrid | 9,060,394 | 1.00x | hybrid | 1,202.27 | 456.0 | 78,439.4 | link_latency | 2.13x | 0.16x | 26.87x | 2.44x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 342.6 | 87,701.5 | kv_read | Qwen3-8B/a100_sxm_80gb-x10969-hybrid | 9,060,394 | 1.00x | hybrid | 1,254.92 | 419.8 | 107,465.1 | link_latency | 0.82x | 0.22x | 9.48x | 0.93x |
| Qwen3-8B | 1024 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 91.0 | 93,227.6 | kv_read | Qwen3-8B/a100_sxm_80gb-x10969-hybrid | 9,060,394 | 1.00x | hybrid | 1,381.09 | 256.3 | 262,467.0 | kv_read | 0.36x | 0.24x | 2.52x | 0.44x |
| Qwen3-8B | 4096 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 23.0 | 94,204.9 | kv_read | Qwen3-8B/a100_sxm_80gb-x10969-hybrid | 9,060,394 | 1.00x | hybrid | 492.86 | 112.7 | 461,580.4 | kv_read | 0.20x | 0.20x | 0.64x | 0.30x |

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
| Qwen3-8B | 21 | 17,346 | 36.2 | 338.8 | 236.6 | tensor | 1,098.06 | 37.2% | link_latency |
| Qwen3-8B | 23 | 18,998 | 36.2 | 352.2 | 249.8 | tensor | 1,098.06 | 38.7% | link_latency |
| Qwen3-8B | 24 | 19,824 | 36.2 | 358.3 | 256.1 | tensor | 1,098.06 | 39.3% | link_latency |
| Qwen3-8B | 27 | 22,302 | 36.2 | 374.0 | 273.6 | tensor | 1,105.92 | 41.4% | link_latency |
| Qwen3-8B | 29 | 23,954 | 36.2 | 384.0 | 284.3 | tensor | 1,105.92 | 42.5% | link_latency |
| Qwen3-8B | 31 | 25,606 | 36.1 | 393.0 | 294.4 | tensor | 1,105.92 | 43.5% | link_latency |
| Qwen3-8B | 32 | 26,432 | 36.1 | 397.3 | 299.2 | tensor | 1,105.92 | 43.9% | link_latency |
| Qwen3-8B | 33 | 27,258 | 36.1 | 400.6 | 301.7 | tensor | 1,110.64 | 44.5% | link_latency |
| Qwen3-8B | 37 | 30,562 | 36.1 | 415.3 | 318.7 | tensor | 1,110.64 | 46.1% | link_latency |
| Qwen3-8B | 49 | 40,474 | 36.1 | 447.6 | 359.7 | tensor | 1,116.03 | 50.0% | link_latency |
| Qwen3-8B | 56 | 46,256 | 36.1 | 461.8 | 378.5 | tensor | 1,116.03 | 51.5% | link_latency |
| Qwen3-8B | 75 | 61,950 | 36.1 | 488.5 | 415.0 | tensor | 1,120.08 | 54.7% | link_latency |
| Qwen3-8B | 111 | 91,686 | 36.1 | 517.3 | 459.6 | tensor | 1,122.77 | 58.1% | link_latency |
| Qwen3-8B | 112 | 92,512 | 36.1 | 517.9 | 460.5 | tensor | 1,122.77 | 58.1% | link_latency |
| Qwen3-8B | 168 | 138,768 | 36.1 | 539.8 | 460.0 | tensor | 1,125.02 | 60.7% | link_latency |
| Qwen3-8B | 224 | 185,024 | 36.1 | 551.4 | 459.5 | tensor | 1,126.14 | 62.1% | link_latency |
| Qwen3-8B | 335 | 276,710 | 36.1 | 482.8 | 458.2 | tensor | 1,423.65 | 68.7% | link_latency |
| Qwen3-8B | 336 | 277,536 | 36.1 | 482.9 | 458.5 | tensor | 1,423.65 | 68.7% | link_latency |
| Qwen3-8B | 448 | 370,048 | 36.1 | 487.5 | 471.1 | tensor | 1,424.21 | 69.4% | link_latency |
| Qwen3-8B | 672 | 555,072 | 36.1 | 492.2 | 464.6 | tensor | 1,424.77 | 70.1% | link_latency |
| Qwen3-8B | 1678 | 1,386,028 | 36.1 | 497.9 | 458.2 | tensor | 1,425.45 | 71.0% | link_latency |
| Qwen3-8B | 10969 | 9,060,394 | 36.1 | 501.2 | 456.0 | tensor | 1,425.83 | 71.5% | link_latency |

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
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x27 | Qwen3-8B | 27 | pipeline | rom_package_ucie | rom_board_serdes | 26 | 0.87 us | 115,172.0 tok/s | 1,151,719.9 tok/s | 20 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.24 us; 6 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.63 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x32 | Qwen3-8B | 32 | tensor | rom_package_ucie | rom_board_serdes | 144 | 34.31 us | 2,914.4 tok/s | 29,144.4 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 72 x all_reduce span 8 on rom_board_serdes (traversals 4.4) = 32.54 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x33 | Qwen3-8B | 33 | hybrid | rom_package_ucie | rom_board_serdes | 80 | 2.61 us | 38,340.8 tok/s | 383,408.4 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 8 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.84 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x27 | Qwen3-8B | 27 | pipeline | nvlink3 | infiniband_hdr | 26 | 65.20 us | 1,533.7 tok/s | 15,337.2 tok/s | 23 x point_to_point span 2 on nvlink3 (traversals 1.0) = 58.13 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-tensor-x32 | Qwen3-8B | 32 | tensor | nvlink3 | infiniband_hdr | 144 | 710.57 us | 140.7 tok/s | 1,407.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 345.40 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | rom_wafer_serdes | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hybrid-x27 | Qwen3-8B | 27 | hybrid | nvlink3 | infiniband_hdr | 75 | 372.23 us | 268.6 tok/s | 2,686.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x196 | Qwen3-8B | 196 | pipeline | on_wafer | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196 | Qwen3-8B | 196 | tensor | on_wafer | rom_wafer_serdes | 144 | 344.81 us | 290.0 tok/s | 2,900.1 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us; 72 x all_reduce span 196 on rom_wafer_serdes (traversals 28.6) = 206.21 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196 | Qwen3-8B | 196 | hybrid | on_wafer | rom_wafer_serdes | 107 | 142.15 us | 703.5 tok/s | 7,034.9 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us; 35 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 3.55 us |
| Qwen3-8B/a100_sxm_80gb-x21-pipeline | Qwen3-8B | 21 | pipeline | nvlink3 | infiniband_hdr | 20 | 50.21 us | 1,991.8 tok/s | 19,917.6 tok/s | 18 x point_to_point span 2 on nvlink3 (traversals 1.0) = 45.49 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| Qwen3-8B/a100_sxm_80gb-x21-tensor | Qwen3-8B | 21 | tensor | nvlink3 | infiniband_hdr | 144 | 704.67 us | 141.9 tok/s | 1,419.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 339.51 us |
| Qwen3-8B/a100_sxm_80gb-x21-hybrid | Qwen3-8B | 21 | hybrid | nvlink3 | infiniband_hdr | 74 | 369.88 us | 270.4 tok/s | 2,703.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| Qwen3-8B/a100_sxm_80gb-x23-pipeline | Qwen3-8B | 23 | pipeline | nvlink3 | infiniband_hdr | 22 | 55.26 us | 1,809.6 tok/s | 18,095.8 tok/s | 20 x point_to_point span 2 on nvlink3 (traversals 1.0) = 50.55 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| Qwen3-8B/a100_sxm_80gb-x23-tensor | Qwen3-8B | 23 | tensor | nvlink3 | infiniband_hdr | 144 | 704.67 us | 141.9 tok/s | 1,419.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 339.51 us |
| Qwen3-8B/a100_sxm_80gb-x23-hybrid | Qwen3-8B | 23 | hybrid | nvlink3 | infiniband_hdr | 74 | 369.88 us | 270.4 tok/s | 2,703.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| Qwen3-8B/a100_sxm_80gb-x24-pipeline | Qwen3-8B | 24 | pipeline | nvlink3 | infiniband_hdr | 23 | 57.79 us | 1,730.4 tok/s | 17,304.4 tok/s | 21 x point_to_point span 2 on nvlink3 (traversals 1.0) = 53.07 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| Qwen3-8B/a100_sxm_80gb-x24-tensor | Qwen3-8B | 24 | tensor | nvlink3 | infiniband_hdr | 144 | 704.67 us | 141.9 tok/s | 1,419.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 339.51 us |
| Qwen3-8B/a100_sxm_80gb-x24-hybrid | Qwen3-8B | 24 | hybrid | nvlink3 | infiniband_hdr | 74 | 369.88 us | 270.4 tok/s | 2,703.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| Qwen3-8B/a100_sxm_80gb-x27-pipeline | Qwen3-8B | 27 | pipeline | nvlink3 | infiniband_hdr | 26 | 65.20 us | 1,533.7 tok/s | 15,337.2 tok/s | 23 x point_to_point span 2 on nvlink3 (traversals 1.0) = 58.13 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| Qwen3-8B/a100_sxm_80gb-x27-tensor | Qwen3-8B | 27 | tensor | nvlink3 | infiniband_hdr | 144 | 710.57 us | 140.7 tok/s | 1,407.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 345.40 us |
| Qwen3-8B/a100_sxm_80gb-x27-hybrid | Qwen3-8B | 27 | hybrid | nvlink3 | infiniband_hdr | 75 | 372.23 us | 268.6 tok/s | 2,686.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| Qwen3-8B/a100_sxm_80gb-x29-pipeline | Qwen3-8B | 29 | pipeline | nvlink3 | infiniband_hdr | 28 | 70.26 us | 1,423.4 tok/s | 14,233.7 tok/s | 25 x point_to_point span 2 on nvlink3 (traversals 1.0) = 63.18 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| Qwen3-8B/a100_sxm_80gb-x29-tensor | Qwen3-8B | 29 | tensor | nvlink3 | infiniband_hdr | 144 | 710.57 us | 140.7 tok/s | 1,407.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 345.40 us |
| Qwen3-8B/a100_sxm_80gb-x29-hybrid | Qwen3-8B | 29 | hybrid | nvlink3 | infiniband_hdr | 75 | 372.23 us | 268.6 tok/s | 2,686.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| Qwen3-8B/a100_sxm_80gb-x31-pipeline | Qwen3-8B | 31 | pipeline | nvlink3 | infiniband_hdr | 30 | 75.31 us | 1,327.8 tok/s | 13,278.4 tok/s | 27 x point_to_point span 2 on nvlink3 (traversals 1.0) = 68.24 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| Qwen3-8B/a100_sxm_80gb-x31-tensor | Qwen3-8B | 31 | tensor | nvlink3 | infiniband_hdr | 144 | 710.57 us | 140.7 tok/s | 1,407.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 345.40 us |
| Qwen3-8B/a100_sxm_80gb-x31-hybrid | Qwen3-8B | 31 | hybrid | nvlink3 | infiniband_hdr | 75 | 372.23 us | 268.6 tok/s | 2,686.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| Qwen3-8B/a100_sxm_80gb-x32-pipeline | Qwen3-8B | 32 | pipeline | nvlink3 | infiniband_hdr | 31 | 77.84 us | 1,284.7 tok/s | 12,847.3 tok/s | 28 x point_to_point span 2 on nvlink3 (traversals 1.0) = 70.76 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| Qwen3-8B/a100_sxm_80gb-x32-tensor | Qwen3-8B | 32 | tensor | nvlink3 | infiniband_hdr | 144 | 710.57 us | 140.7 tok/s | 1,407.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 345.40 us |
| Qwen3-8B/a100_sxm_80gb-x32-hybrid | Qwen3-8B | 32 | hybrid | nvlink3 | infiniband_hdr | 75 | 372.23 us | 268.6 tok/s | 2,686.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 7.07 us |
| Qwen3-8B/a100_sxm_80gb-x33-pipeline | Qwen3-8B | 33 | pipeline | nvlink3 | infiniband_hdr | 32 | 80.20 us | 1,247.0 tok/s | 12,469.6 tok/s | 28 x point_to_point span 2 on nvlink3 (traversals 1.0) = 70.76 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x33-tensor | Qwen3-8B | 33 | tensor | nvlink3 | infiniband_hdr | 144 | 714.10 us | 140.0 tok/s | 1,400.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 348.94 us |
| Qwen3-8B/a100_sxm_80gb-x33-hybrid | Qwen3-8B | 33 | hybrid | nvlink3 | infiniband_hdr | 76 | 374.59 us | 267.0 tok/s | 2,669.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x37-pipeline | Qwen3-8B | 37 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x37-tensor | Qwen3-8B | 37 | tensor | nvlink3 | infiniband_hdr | 144 | 714.10 us | 140.0 tok/s | 1,400.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 348.94 us |
| Qwen3-8B/a100_sxm_80gb-x37-hybrid | Qwen3-8B | 37 | hybrid | nvlink3 | infiniband_hdr | 76 | 374.59 us | 267.0 tok/s | 2,669.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x49-pipeline | Qwen3-8B | 49 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x49-tensor | Qwen3-8B | 49 | tensor | nvlink3 | infiniband_hdr | 144 | 718.15 us | 139.2 tok/s | 1,392.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 352.99 us |
| Qwen3-8B/a100_sxm_80gb-x49-hybrid | Qwen3-8B | 49 | hybrid | nvlink3 | infiniband_hdr | 78 | 379.31 us | 263.6 tok/s | 2,636.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| Qwen3-8B/a100_sxm_80gb-x56-pipeline | Qwen3-8B | 56 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x56-tensor | Qwen3-8B | 56 | tensor | nvlink3 | infiniband_hdr | 144 | 718.15 us | 139.2 tok/s | 1,392.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 352.99 us |
| Qwen3-8B/a100_sxm_80gb-x56-hybrid | Qwen3-8B | 56 | hybrid | nvlink3 | infiniband_hdr | 78 | 379.31 us | 263.6 tok/s | 2,636.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| Qwen3-8B/a100_sxm_80gb-x75-pipeline | Qwen3-8B | 75 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x75-tensor | Qwen3-8B | 75 | tensor | nvlink3 | infiniband_hdr | 144 | 721.18 us | 138.7 tok/s | 1,386.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 356.02 us |
| Qwen3-8B/a100_sxm_80gb-x75-hybrid | Qwen3-8B | 75 | hybrid | nvlink3 | infiniband_hdr | 81 | 386.38 us | 258.8 tok/s | 2,588.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| Qwen3-8B/a100_sxm_80gb-x111-pipeline | Qwen3-8B | 111 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x111-tensor | Qwen3-8B | 111 | tensor | nvlink3 | infiniband_hdr | 144 | 723.20 us | 138.3 tok/s | 1,382.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 358.04 us |
| Qwen3-8B/a100_sxm_80gb-x111-hybrid | Qwen3-8B | 111 | hybrid | nvlink3 | infiniband_hdr | 85 | 395.81 us | 252.6 tok/s | 2,526.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| Qwen3-8B/a100_sxm_80gb-x112-pipeline | Qwen3-8B | 112 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x112-tensor | Qwen3-8B | 112 | tensor | nvlink3 | infiniband_hdr | 144 | 723.20 us | 138.3 tok/s | 1,382.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 358.04 us |
| Qwen3-8B/a100_sxm_80gb-x112-hybrid | Qwen3-8B | 112 | hybrid | nvlink3 | infiniband_hdr | 85 | 395.81 us | 252.6 tok/s | 2,526.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| Qwen3-8B/a100_sxm_80gb-x168-pipeline | Qwen3-8B | 168 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x168-tensor | Qwen3-8B | 168 | tensor | nvlink3 | infiniband_hdr | 144 | 724.89 us | 138.0 tok/s | 1,379.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 359.73 us |
| Qwen3-8B/a100_sxm_80gb-x168-hybrid | Qwen3-8B | 168 | hybrid | nvlink3 | infiniband_hdr | 92 | 412.31 us | 242.5 tok/s | 2,425.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.15 us |
| Qwen3-8B/a100_sxm_80gb-x224-pipeline | Qwen3-8B | 224 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x224-tensor | Qwen3-8B | 224 | tensor | nvlink3 | infiniband_hdr | 144 | 725.73 us | 137.8 tok/s | 1,377.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 360.57 us |
| Qwen3-8B/a100_sxm_80gb-x224-hybrid | Qwen3-8B | 224 | hybrid | nvlink3 | infiniband_hdr | 99 | 428.82 us | 233.2 tok/s | 2,332.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.66 us |
| Qwen3-8B/a100_sxm_80gb-x335-pipeline | Qwen3-8B | 335 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x335-tensor | Qwen3-8B | 335 | tensor | nvlink3 | infiniband_hdr | 144 | 1,018.89 us | 98.1 tok/s | 981.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 653.73 us |
| Qwen3-8B/a100_sxm_80gb-x335-hybrid | Qwen3-8B | 335 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x336-pipeline | Qwen3-8B | 336 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x336-tensor | Qwen3-8B | 336 | tensor | nvlink3 | infiniband_hdr | 144 | 1,018.89 us | 98.1 tok/s | 981.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 653.73 us |
| Qwen3-8B/a100_sxm_80gb-x336-hybrid | Qwen3-8B | 336 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x448-pipeline | Qwen3-8B | 448 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x448-tensor | Qwen3-8B | 448 | tensor | nvlink3 | infiniband_hdr | 144 | 1,019.32 us | 98.1 tok/s | 981.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 654.15 us |
| Qwen3-8B/a100_sxm_80gb-x448-hybrid | Qwen3-8B | 448 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x672-pipeline | Qwen3-8B | 672 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x672-tensor | Qwen3-8B | 672 | tensor | nvlink3 | infiniband_hdr | 144 | 1,019.74 us | 98.1 tok/s | 980.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 654.58 us |
| Qwen3-8B/a100_sxm_80gb-x672-hybrid | Qwen3-8B | 672 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x1678-pipeline | Qwen3-8B | 1678 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x1678-tensor | Qwen3-8B | 1678 | tensor | nvlink3 | infiniband_hdr | 144 | 1,020.24 us | 98.0 tok/s | 980.2 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 210 on infiniband_hdr (traversals 4.0) = 655.08 us |
| Qwen3-8B/a100_sxm_80gb-x1678-hybrid | Qwen3-8B | 1678 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x10969-pipeline | Qwen3-8B | 10969 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x10969-tensor | Qwen3-8B | 10969 | tensor | nvlink3 | infiniband_hdr | 144 | 1,020.53 us | 98.0 tok/s | 979.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 1372 on infiniband_hdr (traversals 4.0) = 655.37 us |
| Qwen3-8B/a100_sxm_80gb-x10969-hybrid | Qwen3-8B | 10969 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | array | array | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x50-romfill | 40,750 | 7,163.3 | 0.176 | 7,163.3 (40,750) | 4,894.8 (46,225) | 0.68x | layer_fixed_latency |
| Qwen3-8B | 2 | wafer | wafer | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196-romfill | 9,060,100 | 1,787.0 | 0.000 | — (—) | 1,787.0 (9,060,100) | — | link_latency |
| Qwen3-8B | 4 | wafer | wafer | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196 | 9,060,100 | 1,683.6 | 0.000 | — (—) | 1,683.6 (9,060,100) | — | link_latency |
| Qwen3-8B | 8 | wafer | wafer | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196 | 9,060,100 | 1,484.4 | 0.000 | — (—) | 1,484.4 (9,060,100) | — | link_latency |
| Qwen3-8B | 16 | wafer | wafer | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196 | 9,060,100 | 1,190.3 | 0.000 | — (—) | 1,190.3 (9,060,100) | — | link_latency |
| Qwen3-8B | 32 | wafer | wafer | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 1,160.4 | 0.000 | — (—) | 1,160.4 (9,060,100) | — | kv_read |
| Qwen3-8B | 64 | wafer | wafer | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 970.9 | 0.000 | — (—) | 970.9 (9,060,100) | — | kv_read |
| Qwen3-8B | 256 | wafer | wafer | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 342.6 | 0.000 | — (—) | 342.6 (9,060,100) | — | kv_read |
| Qwen3-8B | 1024 | wafer | wafer | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 91.0 | 0.000 | — (—) | 91.0 (9,060,100) | — | kv_read |
| Qwen3-8B | 4096 | wafer | wafer | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 23.0 | 0.000 | — (—) | 23.0 (9,060,100) | — | kv_read |

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
| Qwen3-8B | 1 | sram | 23,687.2 | 22,160.2 | 22,160.2 | 1.07x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 23,687.2 | 22,160.2 | 22,160.2 | 1.07x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 23,687.2 | 22,160.2 | 22,160.2 | 1.07x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 23,687.2 | 22,160.2 | 22,160.2 | 1.07x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 23,687.2 | 22,160.2 | 22,160.2 | 1.07x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 27,149.3 | 22,160.2 | 22,160.2 | 1.23x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 34,399.0 | 22,972.2 | 22,972.2 | 1.50x | 1.00x | layer_fixed_latency | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 83,909.5 | 25,609.1 | 25,609.1 | 3.28x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 1024 | sram | 92,736.8 | 26,027.3 | 26,027.3 | 3.56x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 4096 | sram | 94,115.5 | 26,098.0 | 26,098.0 | 3.61x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 1 | rom | 56,859.5 | 56,812.9 | 56,812.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 56,859.5 | 56,812.9 | 56,812.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 56,859.5 | 56,812.9 | 56,812.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 56,859.5 | 56,812.9 | 56,812.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 56,859.5 | 56,812.9 | 56,812.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 56,859.5 | 56,812.9 | 56,812.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 62,139.4 | 62,096.9 | 62,096.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 87,701.5 | 87,632.1 | 87,632.1 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 1024 | rom | 93,227.6 | 93,181.8 | 93,181.8 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4096 | rom | 94,204.9 | 94,191.2 | 94,191.2 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196 | 9,060,100 | 1.00 | 1.00 | 23,687.2 | 0.003 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 1,755.33 | 1.00 | 56,859.5 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream | 9,060,100 | 1.00 | 1.00 | 22,160.2 | 0.002 | weight_read | 0.94x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream-romfill | 9,060,100 | 6,361.76 | 1.00 | 56,812.9 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion | 9,060,100 | 1.00 | 1.00 | 22,160.2 | 0.002 | weight_read | 0.94x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion-romfill | 9,060,100 | 6,361.76 | 1.00 | 56,812.9 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196 | 9,060,100 | 1.00 | 1.00 | 23,687.2 | 0.003 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 1,755.33 | 1.00 | 56,859.5 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream | 9,060,100 | 1.00 | 1.00 | 22,160.2 | 0.002 | weight_read | 0.94x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream-romfill | 9,060,100 | 6,361.76 | 1.00 | 56,812.9 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion | 9,060,100 | 1.00 | 1.00 | 22,160.2 | 0.002 | weight_read | 0.94x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion-romfill | 9,060,100 | 6,361.76 | 1.00 | 56,812.9 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196 | 9,060,100 | 1.00 | 1.00 | 23,687.2 | 0.003 | weight_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 1,755.33 | 1.00 | 56,859.5 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream | 9,060,100 | 1.00 | 1.00 | 22,160.2 | 0.002 | weight_read | 0.94x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream-romfill | 9,060,100 | 6,361.76 | 1.00 | 56,812.9 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion | 9,060,100 | 1.00 | 1.00 | 22,160.2 | 0.002 | weight_read | 0.94x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion-romfill | 9,060,100 | 6,361.76 | 1.00 | 56,812.9 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196 | 9,060,100 | 1.00 | 1.00 | 23,687.2 | 0.003 | weight_read | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 1,755.33 | 1.00 | 56,859.5 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream | 9,060,100 | 1.00 | 1.00 | 22,160.2 | 0.002 | weight_read | 0.94x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream-romfill | 9,060,100 | 6,361.76 | 1.00 | 56,812.9 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion | 9,060,100 | 1.00 | 1.00 | 22,160.2 | 0.002 | weight_read | 0.94x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion-romfill | 9,060,100 | 6,361.76 | 1.00 | 56,812.9 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196 | 9,060,100 | 1.00 | 1.00 | 23,687.2 | 0.003 | weight_read | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 1,755.33 | 1.00 | 56,859.5 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream | 9,060,100 | 1.00 | 1.00 | 22,160.2 | 0.002 | weight_read | 0.94x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream-romfill | 9,060,100 | 6,361.76 | 1.00 | 56,812.9 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion | 9,060,100 | 1.00 | 1.00 | 22,160.2 | 0.002 | weight_read | 0.94x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion-romfill | 9,060,100 | 6,361.76 | 1.00 | 56,812.9 | 0.006 | kv_read | 2.40x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196 | 9,060,100 | 1.00 | 1.00 | 27,149.3 | 0.003 | link_latency | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 1,755.33 | 1.00 | 56,859.5 | 0.006 | kv_read | 2.09x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream | 9,060,100 | 1.00 | 1.00 | 22,160.2 | 0.002 | weight_read | 0.82x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream-romfill | 9,060,100 | 6,361.76 | 1.00 | 56,812.9 | 0.006 | kv_read | 2.09x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion | 9,060,100 | 1.00 | 1.00 | 22,160.2 | 0.002 | weight_read | 0.82x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion-romfill | 9,060,100 | 6,361.76 | 1.00 | 56,812.9 | 0.006 | kv_read | 2.09x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x196 | 9,060,100 | 1.00 | 1.00 | 34,399.0 | 0.004 | layer_fixed_latency | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 1,755.33 | 1.00 | 62,139.4 | 0.007 | kv_read | 1.81x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream | 9,060,100 | 1.00 | 1.31 | 22,972.2 | 0.003 | weight_read | 0.67x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream-romfill | 9,060,100 | 6,361.76 | 1.31 | 62,096.9 | 0.007 | kv_read | 1.81x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion | 9,060,100 | 1.00 | 1.31 | 22,972.2 | 0.003 | weight_read | 0.67x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion-romfill | 9,060,100 | 6,361.76 | 1.31 | 62,096.9 | 0.007 | kv_read | 1.81x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196 | 9,060,100 | 1.00 | 1.00 | 83,909.5 | 0.009 | kv_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 1,755.33 | 1.00 | 87,701.5 | 0.010 | kv_read | 1.05x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream | 9,060,100 | 1.00 | 1.31 | 25,609.1 | 0.003 | weight_read | 0.31x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream-romfill | 9,060,100 | 6,361.76 | 1.31 | 87,632.1 | 0.010 | kv_read | 1.04x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion | 9,060,100 | 1.00 | 1.31 | 25,609.1 | 0.003 | weight_read | 0.31x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion-romfill | 9,060,100 | 6,361.76 | 1.31 | 87,632.1 | 0.010 | kv_read | 1.04x |
| Qwen3-8B | 1024 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196 | 9,060,100 | 1.00 | 1.00 | 92,736.8 | 0.010 | kv_read | 1.00x |
| Qwen3-8B | 1024 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 1,755.33 | 1.00 | 93,227.6 | 0.010 | kv_read | 1.01x |
| Qwen3-8B | 1024 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream | 9,060,100 | 1.00 | 1.47 | 26,027.3 | 0.003 | weight_read | 0.28x |
| Qwen3-8B | 1024 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream-romfill | 9,060,100 | 6,361.76 | 1.47 | 93,181.8 | 0.010 | kv_read | 1.00x |
| Qwen3-8B | 1024 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion | 9,060,100 | 1.00 | 1.47 | 26,027.3 | 0.003 | weight_read | 0.28x |
| Qwen3-8B | 1024 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion-romfill | 9,060,100 | 6,361.76 | 1.47 | 93,181.8 | 0.010 | kv_read | 1.00x |
| Qwen3-8B | 4096 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196 | 9,060,100 | 1.00 | 1.00 | 94,115.5 | 0.010 | kv_read | 1.00x |
| Qwen3-8B | 4096 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-romfill | 9,060,100 | 1,755.33 | 1.00 | 94,204.9 | 0.010 | kv_read | 1.00x |
| Qwen3-8B | 4096 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream | 9,060,100 | 1.00 | 1.47 | 26,098.0 | 0.003 | weight_read | 0.28x |
| Qwen3-8B | 4096 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perstream-romfill | 9,060,100 | 6,361.76 | 1.47 | 94,191.2 | 0.010 | kv_read | 1.00x |
| Qwen3-8B | 4096 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion | 9,060,100 | 1.00 | 1.47 | 26,098.0 | 0.003 | weight_read | 0.28x |
| Qwen3-8B | 4096 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x196-perregion-romfill | 9,060,100 | 6,361.76 | 1.47 | 94,191.2 | 0.010 | kv_read | 1.00x |

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
| Qwen3-8B | 1 | 21 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4 | 11,117 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 8 | 11,117 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 16 | 11,117 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 32 | 11,117 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 64 | 11,117 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 256 | 11,117 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 1024 | 11,117 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4096 | 11,117 | 1.00 | 1.000 | 1.000 | 1.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|

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
| gpu | Qwen3-8B | 1 | 566.80 | 31.3% |
| rom | Qwen3-8B | 1 | 91.03 | 65.2% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| Qwen3-8B | sram | interleaved | 128 B | 1.00x |
| Qwen3-8B | hbm | interleaved | 32 B | 1.00x |

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
| Qwen3-8B | 1 | 21 | 97.46% | 189.80 | 9.27 |
| Qwen3-8B | 2 | 1 | 34.16% | 180.59 | 9.27 |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 2.5 | 10,458.9 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 2.5 | 10,458.9 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 2.5 | 10,458.9 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 2.5 | 10,458.9 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 2.5 | 10,458.9 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 2.5 | 10,458.9 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 2.5 | 10,458.9 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 2.5 | 10,458.9 |
| Qwen3-8B | 1024 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 2.5 | 10,458.9 |
| Qwen3-8B | 4096 | 100.00% | 15.1 GB | 100.00% | 475.30 TB/s | 475.30 TB/s | 2.5 | 10,458.9 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 159 |
| gpu | kv_read | 326 |
| gpu | link_latency | 175 |
| rom | infeasible | 2264 |
| rom | kv_read | 90 |
| rom | layer_fixed_latency | 106 |
| rom | link_latency | 137 |
| rom | weight_read | 103 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 159 |
| rom | CAPACITY | 2264 |

## Mechanical consistency audit

**FAIL** over 37,789 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x24', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x27', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x29', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x32', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x33', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x38', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x76', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x24', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x27', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x29', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x32', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x33', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x38', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x76', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x24', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x27', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x29', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x32', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x33', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x38', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x76', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x24', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x27', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x29', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x32', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x33', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x38', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x57', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x76', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x2', 'Qwen3-8B', 1)

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

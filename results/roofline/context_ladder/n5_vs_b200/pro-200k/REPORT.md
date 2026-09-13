# Area-constrained roofline: n5_vs_b200-pro-200k

> CONTEXT-LADDER RUNG of n5_vs_b200: DeepSeek-V4-Pro-0813 at 200,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 382x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 3 devices. On the GPU side the correction reaches 272x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 92 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Pro-0813 takes 3 x 46,225 mm2 (138,675 mm2, wafer, KV in HBM) at 2,649 tok/s per user and 19 tok/s per 1,000 mm2, holding 1,320 sessions, against 87 copies of one unified HBM die at the same silicon: 3.5x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Pro-0813 on 138,675 mm2 of ROM silicon at 2,649 tok/s per user against 139,200 mm2 of b200_sxm-x87-tensor at 749 tok/s: **3.5x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 6,675. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 97.32x to it.** At 554,700 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 8.10 tok/s and the same silicon running tensor delivers 788 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.48x (DeepSeek-V4-Pro-0813, ROM binding on `link_latency`) to 44.42x (DeepSeek-V4-Pro-0813, ROM binding on `link_latency`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Pro-0813 engages 4.4% of its ROM array at batch 1 and 5.3% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 121 to 19,396 tok/s, and its rate with every slot occupied from 19,311 to 19,396. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 159 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 896 us over NVLink, capping per-user decode at 1,116 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 1,478.2 us and cap it at 677 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 8 of 8 operating points and an array 0; on tokens per second per square millimetre the same points go 0 to the array and 8 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 6 of 1428 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 13.8x of aggregate throughput (DeepSeek-V4-Pro-0813). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 8.04x, on DeepSeek-V4-Pro-0813 at batch 256, where the busiest region carries 2.95x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 16 of 16 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 90% of its cooling budget. The companion study at the other node does have power-limited points.


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

**Recommended: `ROM-N5-native-HBMKV-wafer-hybrid-x3`** -- 3 x 46,225 mm2 wafers, 138,675 mm2 total, `hybrid`-parallel, KV in HBM, spare silicon to `sram`.

- **2,648.8 tok/s per user** (0.38 ms/token), binding on `link_latency`
- **19.1 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 7,946 tok/s aggregate with every slot full, over 1,320 resident sessions (fill limited by `pipeline_slots`)
- 9,059 W at 0.065 W/mm2, 1,140.0 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 87 copies of one unified HBM die -- `b200_sxm-x87-tensor`, 139,200 mm2, area ratio 0.9962 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 138,675 | 139,200 | 0.9962 |
| user tok/s | 2,648.8 | 748.5 | 3.54x |
| aggregate tok/s | 7,946 | 749 | 10.62x |
| resident sessions | 1,320 | 6,675 | -- |
| J/token | 1.1400 | 44.9593 | 39.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1,320 sessions against one that holds 6,675 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x347-tensor` at 555,200 mm2 and 788.0 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 19.1 | 1 | 3.54x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 19.1 | 1 | 3.54x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-tensor-x148` | 120,620 | 1,041.6 | 8.6 | 1 | 1.41x |
| **after -- this report's rule** | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 19.1 | 1,320 | 3.54x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-HBMKV-wafer-hybrid-x3` **<-- recommended** | 138,675 | 3 | 2,648.8 | 7,946 | 19.1 | 1,320 | `link_latency` | 9,059 | 1,140.0 | `b200_sxm-x87-tensor` | 3.54x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 96 | densest | `ROM-N5-native-SRAMKV-array-tensor-x148` | 120,620 | 1,041.6 | 8.6 | 1 |
| array | 96 | fastest | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 277,100 | 1,062.6 | 3.8 | 1 |
| array | 96 | smallest | `ROM-N5-native-SRAMKV-array-tensor-x148` | 120,620 | 1,041.6 | 8.6 | 1 |
| wafer | 60 | densest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 19.1 | 1 |
| wafer | 60 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 19.1 | 1 |
| wafer | 60 | smallest | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 19.1 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-tensor-x340-romfill` | 277,100 | 1,062.6 | 1,063 | 1 | 23,661 | 22,267.4 | `link_latency` | `b200_sxm-x173-tensor` | 773.9 | 13,720 | 82,566.5 | 1.001 | 1.37x | 3.7x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 2,649 | 1 | 8,145 | 3,074.9 | `link_latency` | `b200_sxm-x87-tensor` | 748.5 | 6,675 | 44,959.3 | 0.996 | 3.54x | 14.6x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-tensor-x170` | 138,550 | 1,053.4 | 1,053 | 1 | 8,521 | 8,088.5 | `link_latency` | `b200_sxm-x87-tensor` | 748.5 | 6,675 | 44,959.3 | 0.995 | 1.41x | 5.6x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | -- | 1 | -- | 3,074.9 | -- | -- | -- | -- | -- | 0.999 | 2.51x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-tensor-x340-romfill` | 277,100 | 951.6 | 1,903 | 17,407 | 29,785 | 15,650.1 | `link_latency` | `b200_sxm-x173-tensor` | 678.4 | 13,720 | 47,487.8 | 1.001 | 1.40x | 3.0x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 7,946 | 1,320 | 9,059 | 1,140.0 | `link_latency` | `b200_sxm-x87-tensor` | 640.8 | 6,675 | 26,596.1 | 0.996 | 4.13x | 23.3x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-tensor-x170` | 138,550 | 948.3 | 1,897 | 8,703 | 10,641 | 5,610.7 | `link_latency` | `b200_sxm-x87-tensor` | 640.8 | 6,675 | 26,596.1 | 0.995 | 1.48x | 4.7x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | -- | 1,320 | -- | 1,140.0 | -- | -- | -- | -- | -- | 0.999 | 2.79x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hybrid-x161` | 131,215 | 857.6 | 18,010 | 8,242 | 10,553 | 585.9 | `weight_read` | `b200_sxm-x82-tensor` | 506.4 | 6,265 | 16,267.6 | 1.000 | 1.69x | 27.8x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,648.3 | 10,593 | 1,320 | 9,216 | 870.0 | `link_latency` | `b200_sxm-x87-tensor` | 509.8 | 6,675 | 17,031.3 | 0.996 | 5.19x | 19.6x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x170` | 138,550 | 828.7 | 18,232 | 8,703 | 11,757 | 644.9 | `weight_read` | `b200_sxm-x87-tensor` | 509.8 | 6,675 | 17,031.3 | 0.995 | 1.63x | 26.4x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,648.3 | -- | 1,320 | -- | 870.0 | -- | -- | -- | -- | -- | 0.999 | 3.20x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hybrid-x161` | 131,215 | 857.6 | 18,010 | 8,242 | 10,553 | 585.9 | `weight_read` | `b200_sxm-x82-tensor` | 377.7 | 6,265 | 11,199.8 | 1.000 | 2.27x | 19.1x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,646.5 | 21,172 | 1,320 | 9,845 | 465.0 | `link_latency` | `b200_sxm-x87-tensor` | 381.0 | 6,675 | 11,691.3 | 0.996 | 6.95x | 25.1x |
| 8 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x170` | 138,550 | 828.7 | 18,232 | 8,703 | 11,757 | 644.9 | `weight_read` | `b200_sxm-x87-tensor` | 381.0 | 6,675 | 11,691.3 | 0.995 | 2.18x | 18.1x |
| 8 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,646.5 | -- | 1,320 | -- | 465.0 | -- | -- | -- | -- | -- | 0.999 | 3.19x wafer/array | -- |
| 16 | array | `ROM-N5-native-HBMKV-array-hybrid-x161` | 131,215 | 857.6 | 18,010 | 8,242 | 10,553 | 585.9 | `weight_read` | `b200_sxm-x82-tensor` | 259.4 | 6,265 | 8,360.9 | 1.000 | 3.31x | 14.3x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,426.5 | 38,823 | 1,320 | 10,887 | 280.4 | `link_latency` | `b200_sxm-x87-tensor` | 261.9 | 6,675 | 8,713.1 | 0.996 | 9.27x | 31.1x |
| 16 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x170` | 138,550 | 828.7 | 18,232 | 8,703 | 11,757 | 644.9 | `weight_read` | `b200_sxm-x87-tensor` | 261.9 | 6,675 | 8,713.1 | 0.995 | 3.16x | 13.5x |
| 16 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | 2,426.5 | -- | 1,320 | -- | 280.4 | -- | -- | -- | -- | -- | 0.999 | 2.93x wafer/array | -- |
| 32 | array | `ROM-N5-native-HBMKV-array-hybrid-x170` | 138,550 | 825.3 | 26,409 | 8,703 | 12,243 | 463.6 | `weight_read` | `b200_sxm-x87-tensor` | 167.5 | 6,675 | 6,903.6 | 0.995 | 4.93x | 14.9x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,364.4 | 75,662 | 1,761 | 19,911 | 263.2 | `link_latency` | `b200_sxm-x116-tensor` | 172.3 | 9,050 | 8,588.5 | 0.996 | 13.72x | 32.6x |
| 32 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x227` | 185,005 | 670.1 | 21,444 | 11,621 | 19,493 | 909.0 | `weight_read` | `b200_sxm-x116-tensor` | 172.3 | 9,050 | 8,588.5 | 0.997 | 3.89x | 9.4x |
| 32 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,364.4 | -- | 1,761 | -- | 263.2 | -- | -- | -- | -- | -- | 1.001 | 3.53x wafer/array | -- |
| 64 | array | `ROM-N5-native-HBMKV-array-hybrid-x193` | 157,295 | 742.3 | 47,507 | 9,881 | 16,541 | 348.2 | `weight_read` | `b200_sxm-x98-tensor` | 102.2 | 7,576 | 6,211.1 | 1.003 | 7.26x | 17.8x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 2,219.3 | 142,032 | 2,641 | 33,127 | 233.2 | `link_latency` | `b200_sxm-x173-tensor` | 106.4 | 13,720 | 9,863.0 | 1.002 | 20.86x | 42.3x |
| 64 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | 277,100 | 585.0 | 37,442 | 17,407 | 32,102 | 857.4 | `weight_read` | `b200_sxm-x173-tensor` | 106.4 | 13,720 | 9,863.0 | 1.001 | 5.50x | 11.5x |
| 64 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 2,219.3 | -- | 2,641 | -- | 233.2 | -- | -- | -- | -- | -- | 0.999 | 3.79x wafer/array | -- |
| 256 | array | `ROM-N5-native-HBMKV-array-hybrid-x227` | 185,005 | 627.5 | 160,633 | 11,621 | 27,733 | 172.6 | `weight_read` | `b200_sxm-x116-hybrid` | 50.6 | 9,050 | 4,552.9 | 0.997 | 12.39x | 26.4x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,613.7 | 413,111 | 5,283 | 73,723 | 178.5 | `link_latency` | `b200_sxm-x347-hybrid` | 36.3 | 27,973 | 14,918.8 | 0.999 | 44.42x | 83.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-32 | `ROM-N5-native-HBMKV-wafer-hybrid-x3` | 138,675 | wafer | HBM | 1,320 |
| 64-256 | `ROM-N5-native-HBMKV-wafer-hybrid-x4` | 184,900 | wafer | HBM | 1,761 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Pro-0813 | HBM | rom | 159, 161, 170, 193, 227, 231, 308, 340 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 159, 161, 170, 193, 227, 231, 308, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 148, 150, 170, 180, 216, 227, 288, 340 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 148, 150, 170, 180, 216, 227, 288, 340 |

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
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 0.0 tok/s | 0.00x | within 2x | FAIL |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |
| A100 80GB at its published TDP, saturating load | 400.0 W | 461.7 W | 1.15x | within 2x | PASS |
| Taalas HC1 card power at its published operating point | 200.0-250.0 W | 87.6 W | 0.35x | within 2x | FAIL |

HC1 binds on `capacity_or_format`. Its component times are weight_read 61.42 us, kv_read 9.28 us, compute 61.42 us, link_latency 0.00 us, layer_fixed_latency 6.06 us.

**THE ANCHOR IS INFEASIBLE, AND THAT IS THE RESULT.** The model does not
under-predict the shipping part here -- it cannot place it. Taalas ships
this die; this model says the die cannot hold its own weights. At least one
of the constants below is therefore wrong, and the gate exists to say so
rather than to be closed:

- AREA: the array needs 770.5 mm2 to hold 3,513,239,296 B but only 432.4 mm2 of 815 mm2 is left after SRAM, HBM PHY, overhead and interconnect

The candidates, in the order they should be attacked: `rom.cell_to_sram_cell_area_ratio` and `rom.array_efficiency`, whose
product is now set by one sentence in one paper about a foundry memory
compiler and which together cut ROM capacity density by 2.243x;
`rom.cim_precompute_area_fraction`, taken from a different fabricated part
with a different architecture; `rom.cim_cell_area_multiplier`, for which no
published compute-in-ROM cell exists at any node; and
`reference_parts.taalas_hc1.weight_bits_per_parameter`, whose 3.0-6.0 sweep
the vendor's own 3-bit base type sits at the bottom of. **Nothing here is
tuned to make this gate pass.** The back-derivation below is still printed,
because what each input would have to be is exactly the question a failing
gate asks:

| Derived input | This model | Required by the shipping part | Shortfall |
|---|---:|---:|---:|
| ROM read bandwidth density (B/s/mm2) | 1.764e+11 | 1.837e+11 | 1.04x |
| Compute density (ops/s/mm2) | 1.261e+12 | 3.155e+12 | 2.50x |

The gate fails before either rate density can bind: the corrected
ROM capacity density and compute-in-ROM floorplan cannot fit the
published model in 815 mm2. The rate diagnostics remain useful --
ROM read density is 1.04x and
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
| range low | 70.0 ns/layer | 2.24 us | 0.0 | 0.00x | capacity_or_format |
| range stated | 189.4 ns/layer | 6.06 us | 0.0 | 0.00x | capacity_or_format |
| range high | 894.8 ns/layer | 28.63 us | 0.0 | 0.00x | capacity_or_format |

The per-layer cost that would land the model exactly on the
published figure is **-76.7 ns/layer**. It is negative, which means no positive latency term could close the gate. The current result is decided earlier by the reported capacity failure.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 0.0 | 0.00x | capacity_or_format |
| 3.5 | 0.0 | 0.00x | capacity_or_format |
| 4.0 | 0.0 | 0.00x | capacity_or_format |
| 5.0 | 0.0 | 0.00x | capacity_or_format |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 0.0 | 0.00x | capacity_or_format |
| 1,536 | 0.0 | 0.00x | capacity_or_format |
| 2,048 | 0.0 | 0.00x | capacity_or_format |

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
| Taalas HC1 card power | 200.0-250.0 W | 87.6 W | 0.35x | FAIL |

**Where the watts come from.**

| Term | A100 at TDP | Taalas HC1 |
|---|---:|---:|
| memory / array traffic (weights) | 213.9 W | 3.9 W |
| KV traffic | n/a: one saturating HBM stream | 10.3 W |
| operand delivery | 0.5 W | 12.1 W |
| arithmetic | 103.0 W | 8.7 W |
| static: leakage | 31.4 W | 20.9 W |
| static: clock distribution | 99.0 W | 31.6 W |
| static: memory-interface idle | 14.0 W | 0.0 W |
| **static charged** (max of the enumeration and the measured clocked-idle floor) | 144.4 W | 52.5 W |
| **total** | 461.7 W | 87.6 W |

On HC1 the enumerated static power is 52.5 W and the measured clocked-idle floor is 50.0 W, so the enumeration binds and the floor is inert.

**The band.** Every term in the power block bar one is `assumed`, and
two of them -- the fabric clock and the array clock multiplier --
multiply, so the gates are reported at both ends of the whole band
with every term moved together. Moving one at a time would report a
sensitivity that is really a bias.

| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 338.9 W | 0.85x | 63.3 W | 0.25x | 0.32x |
| stated | 461.7 W | 1.15x | 87.6 W | 0.35x | 0.44x |
| high | 698.3 W | 1.75x | 374.6 W | 1.50x | 1.87x |

**The outcome, stated as an outcome.** The A100 gate lands at 1.15x of its published TDP. The HC1 gate lands at 0.35x of the top of its published band, **2.86x low**, against 2.28x low at the bottom of it. The asymmetry is the finding and it should not be smoothed over.

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
| Taalas HC1 (modelled reconstruction) | n/a (0.005908 J/attempt) | 87.6 | 0.0 |
| A100 80GB, weight-bound gate, same model and batch | 1.465768 J/token | 359.6 | 245.3 |

No tokens-per-joule ratio is admissible for this pair: the HC1 throughput reconstruction is capacity-infeasible and delivers zero modelled tokens. Its energy cell above is the attempted-step energy inside the diagnostic power calculation, not the energy of a feasible machine. The power gate remains useful as a disclosed component check, and it is 2.3-2.9x below the shipping card's published band, but it cannot support an efficiency advantage.

**Where the remaining HC1 shortfall could live, none of it fitted.**
The ROM array is charged its stated leakage density: 2.9 W at the point
and 11.2 W at the
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

- **0 of 1,428 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 90% of its cooling budget, and the busiest wafer-scale ROM design 34%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 24 | 0 | 76.8% | 90.4% | 0.565 | 46% |
| gpu | wafer (>=40,000 mm2) | 456 | 0 | 42.5% | 74.9% | 0.468 | 82% |
| rom | wafer (>=40,000 mm2) | 948 | 0 | 18.2% | 34.0% | 0.170 | 95% |

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
| DeepSeek-V4-Pro-0813 | 1 | 138,675 | `DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x3` | 3.074912 | 8,144.7 | link_latency | `DSV4-Pro/b200_sxm-x87-tensor` | 44.959346 | 33,652.6 | link_latency | 14.62x |
| DeepSeek-V4-Pro-0813 | 2 | 138,675 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3` | 1.139984 | 9,058.7 | link_latency | `DSV4-Pro/b200_sxm-x87-tensor` | 26.596098 | 34,086.1 | link_latency | 23.33x |
| DeepSeek-V4-Pro-0813 | 4 | 138,675 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3` | 0.870000 | 9,216.2 | link_latency | `DSV4-Pro/b200_sxm-x87-tensor` | 17.031338 | 34,733.6 | link_latency | 19.58x |
| DeepSeek-V4-Pro-0813 | 8 | 138,675 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3` | 0.464999 | 9,845.1 | link_latency | `DSV4-Pro/b200_sxm-x87-tensor` | 11.691320 | 35,636.6 | link_latency | 25.14x |
| DeepSeek-V4-Pro-0813 | 16 | 138,675 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3` | 0.280415 | 10,886.6 | link_latency | `DSV4-Pro/b200_sxm-x87-tensor` | 8.713111 | 36,510.3 | link_latency | 31.07x |
| DeepSeek-V4-Pro-0813 | 32 | 184,900 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4` | 0.263152 | 19,910.6 | link_latency | `DSV4-Pro/b200_sxm-x116-tensor` | 8.588463 | 47,350.0 | link_latency | 32.64x |
| DeepSeek-V4-Pro-0813 | 64 | 277,350 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 0.233235 | 33,126.9 | link_latency | `DSV4-Pro/b200_sxm-x173-tensor` | 9.862972 | 67,159.3 | link_latency | 42.29x |
| DeepSeek-V4-Pro-0813 | 256 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.178458 | 73,722.8 | link_latency | `DSV4-Pro/b200_sxm-x347-hybrid` | 14.918843 | 138,741.3 | weight_read | 83.60x |

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
| DeepSeek-V4-Pro-0813 | 3 | 138,675 | 14,625.7 | wafer-pipeline | 2,648.8 | wafer-hybrid | 5.52x | 1,893.8 | pipeline | 748.5 | tensor | 2.53x | 7.72x | 3.54x | 0.46x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 14,625.7 | wafer-pipeline | 2,375.7 | wafer-hybrid | 6.16x | 1,984.6 | pipeline | 760.8 | tensor | 2.61x | 7.37x | 3.12x | 0.42x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 17,292.0 | wafer-pipeline | 2,250.0 | wafer-hybrid | 7.69x | 2,085.8 | pipeline | 773.9 | tensor | 2.70x | 8.29x | 2.91x | 0.35x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 19,654.0 | wafer-pipeline | 2,200.0 | wafer-hybrid | 8.93x | 2,142.6 | pipeline | 780.9 | tensor | 2.74x | 9.17x | 2.82x | 0.31x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 22,759.1 | wafer-pipeline | 2,106.0 | wafer-hybrid | 10.81x | 2,203.2 | pipeline | 788.0 | tensor | 2.80x | 10.33x | 2.67x | 0.26x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.26x to 0.46x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x3 | 138,675 | 2,648.8 | 2,648.8 | link_latency | DSV4-Pro/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 888.62 | 748.5 | 748.5 | link_latency | 3.54x | 3.54x | 99.30x | 3.54x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x148 | 120,620 | 1,041.6 | 1,041.6 | link_latency | DSV4-Pro/b200_sxm-x75-tensor | 120,000 | 1.01x | tensor | 887.67 | 740.6 | 740.6 | link_latency | 1.41x | 1.41x | 34.86x | 1.41x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,648.8 | 7,946.3 | link_latency | DSV4-Pro/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 989.12 | 640.8 | 1,281.6 | link_latency | 4.13x | 6.20x | 99.30x | 4.13x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x159 | 129,585 | 894.7 | 1,789.5 | link_latency | DSV4-Pro/b200_sxm-x81-tensor | 129,600 | 1.00x | tensor | 989.12 | 635.7 | 1,271.3 | link_latency | 1.41x | 1.41x | 31.75x | 1.41x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,648.3 | 10,593.3 | link_latency | DSV4-Pro/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 1,190.12 | 509.8 | 2,039.4 | link_latency | 5.19x | 5.19x | 99.28x | 5.19x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x159 | 129,585 | 723.1 | 14,462.8 | compute | DSV4-Pro/b200_sxm-x81-tensor | 129,600 | 1.00x | tensor | 1,190.12 | 505.7 | 2,022.8 | link_latency | 1.43x | 7.15x | 25.66x | 1.43x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,646.5 | 21,172.3 | link_latency | DSV4-Pro/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 1,592.13 | 381.0 | 3,048.1 | link_latency | 6.95x | 6.95x | 99.21x | 6.95x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x159 | 129,585 | 723.1 | 14,462.8 | compute | DSV4-Pro/b200_sxm-x81-tensor | 129,600 | 1.00x | tensor | 1,592.13 | 377.0 | 3,015.8 | link_latency | 1.92x | 4.80x | 25.66x | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,426.5 | 38,823.3 | link_latency | DSV4-Pro/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 2,396.13 | 261.9 | 4,190.3 | link_latency | 9.27x | 9.27x | 90.96x | 9.27x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x159 | 129,585 | 723.1 | 14,462.8 | compute | DSV4-Pro/b200_sxm-x81-tensor | 129,600 | 1.00x | tensor | 2,396.13 | 258.9 | 4,142.0 | link_latency | 2.79x | 3.49x | 25.66x | 2.79x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,364.4 | 75,662.3 | link_latency | DSV4-Pro/b200_sxm-x116-tensor | 185,600 | 1.00x | tensor | 4,085.55 | 172.3 | 5,513.2 | link_latency | 13.72x | 13.72x | 111.48x | 13.72x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x159 | 129,585 | 499.2 | 15,974.6 | compute | DSV4-Pro/b200_sxm-x81-tensor | 129,600 | 1.00x | tensor | 4,004.15 | 165.5 | 5,297.6 | link_latency | 3.02x | 3.02x | 17.71x | 3.02x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 2,219.3 | 142,032.2 | link_latency | DSV4-Pro/b200_sxm-x173-tensor | 276,800 | 1.00x | tensor | 7,525.45 | 106.4 | 6,809.2 | link_latency | 20.86x | 20.86x | 146.56x | 20.86x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x159 | 129,585 | 273.4 | 17,498.8 | compute | DSV4-Pro/b200_sxm-x81-tensor | 129,600 | 1.00x | tensor | 7,220.17 | 100.4 | 6,426.2 | link_latency | 2.72x | 2.72x | 9.70x | 2.72x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,613.7 | 413,111.5 | link_latency | DSV4-Pro/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 481.50 | 36.3 | 9,299.7 | weight_read | 44.42x | 44.42x | 199.29x | 44.42x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x159 | 129,585 | 75.8 | 19,396.0 | compute | DSV4-Pro/b200_sxm-x81-hybrid | 129,600 | 1.00x | hybrid | 498.55 | 51.0 | 13,055.0 | weight_read | 1.49x | 1.49x | 4.30x | 1.49x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 8 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 8 | Link us at domain 72 | tok/s at 8 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 9 | 14,400 | 845.69 | 297.98 | 508.3 | 704.4 |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 871.93 | 298.43 | 668.1 | 1,083.1 |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 885.04 | 298.53 | 725.1 | 1,261.5 |
| DeepSeek-V4-Pro-0813 | 75 | 120,000 | 887.67 | 846.34 | 740.6 | 764.0 |
| DeepSeek-V4-Pro-0813 | 76 | 121,600 | 887.67 | 846.34 | 741.4 | 764.8 |
| DeepSeek-V4-Pro-0813 | 81 | 129,600 | 888.62 | 846.34 | 744.6 | 768.8 |
| DeepSeek-V4-Pro-0813 | 82 | 131,200 | 888.62 | 846.34 | 745.3 | 769.5 |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 888.62 | 846.34 | 748.5 | 773.0 |
| DeepSeek-V4-Pro-0813 | 92 | 147,200 | 889.42 | 846.34 | 751.0 | 776.1 |
| DeepSeek-V4-Pro-0813 | 98 | 156,800 | 890.09 | 846.34 | 753.8 | 779.5 |
| DeepSeek-V4-Pro-0813 | 110 | 176,000 | 890.67 | 846.34 | 758.8 | 785.2 |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 891.16 | 846.34 | 760.8 | 787.7 |
| DeepSeek-V4-Pro-0813 | 118 | 188,800 | 891.16 | 846.34 | 761.5 | 788.5 |
| DeepSeek-V4-Pro-0813 | 147 | 235,200 | 892.64 | 863.83 | 769.1 | 786.5 |
| DeepSeek-V4-Pro-0813 | 149 | 238,400 | 892.64 | 863.83 | 769.5 | 787.0 |
| DeepSeek-V4-Pro-0813 | 157 | 251,200 | 892.91 | 863.83 | 771.1 | 788.8 |
| DeepSeek-V4-Pro-0813 | 165 | 264,000 | 893.16 | 863.83 | 772.6 | 790.5 |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 893.39 | 863.83 | 773.9 | 792.0 |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 894.54 | 872.57 | 780.9 | 794.5 |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 895.78 | 877.82 | 788.0 | 799.3 |

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
| DeepSeek-V4-Pro-0813 | 9 | 14,400 | 100.4 | 508.3 | 395.9 | tensor | 845.69 | 43.0% | weight_read |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 56.6 | 668.1 | 363.4 | tensor | 871.93 | 58.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 36.1 | 725.1 | 241.3 | tensor | 885.04 | 64.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 75 | 120,000 | 29.9 | 740.6 | 209.0 | tensor | 887.67 | 65.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 76 | 121,600 | 29.6 | 741.4 | 209.6 | tensor | 887.67 | 65.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 81 | 129,600 | 28.2 | 744.6 | 194.4 | tensor | 888.62 | 66.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 82 | 131,200 | 27.9 | 745.3 | 194.9 | tensor | 888.62 | 66.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 26.7 | 748.5 | 197.4 | tensor | 888.62 | 66.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 92 | 147,200 | 25.5 | 751.0 | 184.0 | tensor | 889.42 | 66.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 98 | 156,800 | 24.3 | 753.8 | 172.7 | tensor | 890.09 | 67.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 110 | 176,000 | 22.1 | 758.8 | 164.5 | tensor | 890.67 | 67.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 21.2 | 760.8 | 155.5 | tensor | 891.16 | 67.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 118 | 188,800 | 20.9 | 761.5 | 155.9 | tensor | 891.16 | 67.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 147 | 235,200 | 17.4 | 769.1 | 128.7 | tensor | 892.64 | 68.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 149 | 238,400 | 17.2 | 769.5 | 129.0 | tensor | 892.64 | 68.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 157 | 251,200 | 16.5 | 771.1 | 123.7 | tensor | 892.91 | 68.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 165 | 264,000 | 15.8 | 772.6 | 118.8 | tensor | 893.16 | 69.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 15.1 | 773.9 | 114.3 | tensor | 893.39 | 69.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 11.7 | 780.9 | 90.4 | tensor | 894.54 | 69.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 8.1 | 788.0 | 62.3 | tensor | 895.78 | 70.6% | link_latency |

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
| DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x150 | DeepSeek-V4-Pro-0813 | 150 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x3 | DeepSeek-V4-Pro-0813 | 3 | pipeline | on_wafer_n5 | inter_wafer | 60 | 12.47 us | 8,018.9 tok/s | 80,188.6 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x148 | DeepSeek-V4-Pro-0813 | 148 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x3 | DeepSeek-V4-Pro-0813 | 3 | tensor | on_wafer_n5 | inter_wafer | 244 | 1,478.17 us | 67.7 tok/s | 676.5 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 3 on inter_wafer (traversals 2.0) = 1,243.32 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hybrid-x150 | DeepSeek-V4-Pro-0813 | 150 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x3 | DeepSeek-V4-Pro-0813 | 3 | hybrid | on_wafer_n5 | inter_wafer | 124 | 245.04 us | 408.1 tok/s | 4,080.9 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 2 x point_to_point span 2 on inter_wafer (traversals 1.0) = 10.19 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x161 | DeepSeek-V4-Pro-0813 | 161 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3 | DeepSeek-V4-Pro-0813 | 3 | pipeline | on_wafer_n5 | inter_wafer | 60 | 12.47 us | 8,018.9 tok/s | 80,188.6 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x159 | DeepSeek-V4-Pro-0813 | 159 | tensor | nvlink5 | infiniband_ndr | 244 | 892.91 us | 112.0 tok/s | 1,119.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 595.01 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x3 | DeepSeek-V4-Pro-0813 | 3 | tensor | on_wafer_n5 | inter_wafer | 244 | 1,478.17 us | 67.7 tok/s | 676.5 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 3 on inter_wafer (traversals 2.0) = 1,243.32 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x161 | DeepSeek-V4-Pro-0813 | 161 | hybrid | nvlink5 | infiniband_ndr | 142 | 344.24 us | 290.5 tok/s | 2,905.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 20 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.33 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | DeepSeek-V4-Pro-0813 | 3 | hybrid | on_wafer_n5 | inter_wafer | 124 | 245.04 us | 408.1 tok/s | 4,080.9 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 2 x point_to_point span 2 on inter_wafer (traversals 1.0) = 10.19 us |
| DSV4-Pro/b200_sxm-x9-pipeline | DeepSeek-V4-Pro-0813 | 9 | pipeline | nvlink5 | infiniband_ndr | 8 | 10.83 us | 9,235.1 tok/s | 92,351.3 tok/s | 7 x point_to_point span 2 on nvlink5 (traversals 1.0) = 8.51 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x9-tensor | DeepSeek-V4-Pro-0813 | 9 | tensor | nvlink5 | infiniband_ndr | 244 | 845.69 us | 118.2 tok/s | 1,182.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 547.79 us |
| DSV4-Pro/b200_sxm-x9-hybrid | DeepSeek-V4-Pro-0813 | 9 | hybrid | nvlink5 | infiniband_ndr | 123 | 300.22 us | 333.1 tok/s | 3,330.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.32 us |
| DSV4-Pro/b200_sxm-x29-pipeline | DeepSeek-V4-Pro-0813 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 37.35 us | 2,677.5 tok/s | 26,774.9 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.40 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x29-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5 | infiniband_ndr | 244 | 871.93 us | 114.7 tok/s | 1,146.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 574.02 us |
| DSV4-Pro/b200_sxm-x29-hybrid | DeepSeek-V4-Pro-0813 | 29 | hybrid | nvlink5 | infiniband_ndr | 125 | 304.85 us | 328.0 tok/s | 3,280.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.95 us |
| DSV4-Pro/b200_sxm-x58-pipeline | DeepSeek-V4-Pro-0813 | 58 | pipeline | nvlink5 | infiniband_ndr | 57 | 77.01 us | 1,298.5 tok/s | 12,984.7 tok/s | 50 x point_to_point span 2 on nvlink5 (traversals 1.0) = 60.80 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x58-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5 | infiniband_ndr | 244 | 885.04 us | 113.0 tok/s | 1,129.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 587.14 us |
| DSV4-Pro/b200_sxm-x58-hybrid | DeepSeek-V4-Pro-0813 | 58 | hybrid | nvlink5 | infiniband_ndr | 129 | 314.12 us | 318.4 tok/s | 3,183.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x75-pipeline | DeepSeek-V4-Pro-0813 | 75 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x75-tensor | DeepSeek-V4-Pro-0813 | 75 | tensor | nvlink5 | infiniband_ndr | 244 | 887.67 us | 112.7 tok/s | 1,126.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 589.77 us |
| DSV4-Pro/b200_sxm-x75-hybrid | DeepSeek-V4-Pro-0813 | 75 | hybrid | nvlink5 | infiniband_ndr | 131 | 318.75 us | 313.7 tok/s | 3,137.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| DSV4-Pro/b200_sxm-x76-pipeline | DeepSeek-V4-Pro-0813 | 76 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x76-tensor | DeepSeek-V4-Pro-0813 | 76 | tensor | nvlink5 | infiniband_ndr | 244 | 887.67 us | 112.7 tok/s | 1,126.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 589.77 us |
| DSV4-Pro/b200_sxm-x76-hybrid | DeepSeek-V4-Pro-0813 | 76 | hybrid | nvlink5 | infiniband_ndr | 131 | 318.75 us | 313.7 tok/s | 3,137.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.85 us |
| DSV4-Pro/b200_sxm-x81-pipeline | DeepSeek-V4-Pro-0813 | 81 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x81-tensor | DeepSeek-V4-Pro-0813 | 81 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x81-hybrid | DeepSeek-V4-Pro-0813 | 81 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x82-pipeline | DeepSeek-V4-Pro-0813 | 82 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x82-tensor | DeepSeek-V4-Pro-0813 | 82 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x82-hybrid | DeepSeek-V4-Pro-0813 | 82 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x87-pipeline | DeepSeek-V4-Pro-0813 | 87 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x87-tensor | DeepSeek-V4-Pro-0813 | 87 | tensor | nvlink5 | infiniband_ndr | 244 | 888.62 us | 112.5 tok/s | 1,125.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 590.72 us |
| DSV4-Pro/b200_sxm-x87-hybrid | DeepSeek-V4-Pro-0813 | 87 | hybrid | nvlink5 | infiniband_ndr | 132 | 321.07 us | 311.5 tok/s | 3,114.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.17 us |
| DSV4-Pro/b200_sxm-x92-pipeline | DeepSeek-V4-Pro-0813 | 92 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x92-tensor | DeepSeek-V4-Pro-0813 | 92 | tensor | nvlink5 | infiniband_ndr | 244 | 889.42 us | 112.4 tok/s | 1,124.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 591.51 us |
| DSV4-Pro/b200_sxm-x92-hybrid | DeepSeek-V4-Pro-0813 | 92 | hybrid | nvlink5 | infiniband_ndr | 133 | 323.39 us | 309.2 tok/s | 3,092.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 25.48 us |
| DSV4-Pro/b200_sxm-x98-pipeline | DeepSeek-V4-Pro-0813 | 98 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x98-tensor | DeepSeek-V4-Pro-0813 | 98 | tensor | nvlink5 | infiniband_ndr | 244 | 890.09 us | 112.3 tok/s | 1,123.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 592.19 us |
| DSV4-Pro/b200_sxm-x98-hybrid | DeepSeek-V4-Pro-0813 | 98 | hybrid | nvlink5 | infiniband_ndr | 134 | 325.70 us | 307.0 tok/s | 3,070.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 27.80 us |
| DSV4-Pro/b200_sxm-x110-pipeline | DeepSeek-V4-Pro-0813 | 110 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x110-tensor | DeepSeek-V4-Pro-0813 | 110 | tensor | nvlink5 | infiniband_ndr | 244 | 890.67 us | 112.3 tok/s | 1,122.8 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 592.76 us |
| DSV4-Pro/b200_sxm-x110-hybrid | DeepSeek-V4-Pro-0813 | 110 | hybrid | nvlink5 | infiniband_ndr | 135 | 328.02 us | 304.9 tok/s | 3,048.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.12 us |
| DSV4-Pro/b200_sxm-x116-pipeline | DeepSeek-V4-Pro-0813 | 116 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x116-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x116-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x118-pipeline | DeepSeek-V4-Pro-0813 | 118 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x118-tensor | DeepSeek-V4-Pro-0813 | 118 | tensor | nvlink5 | infiniband_ndr | 244 | 891.16 us | 112.2 tok/s | 1,122.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 593.26 us |
| DSV4-Pro/b200_sxm-x118-hybrid | DeepSeek-V4-Pro-0813 | 118 | hybrid | nvlink5 | infiniband_ndr | 136 | 330.34 us | 302.7 tok/s | 3,027.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.43 us |
| DSV4-Pro/b200_sxm-x147-pipeline | DeepSeek-V4-Pro-0813 | 147 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x147-tensor | DeepSeek-V4-Pro-0813 | 147 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x147-hybrid | DeepSeek-V4-Pro-0813 | 147 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x149-pipeline | DeepSeek-V4-Pro-0813 | 149 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x149-tensor | DeepSeek-V4-Pro-0813 | 149 | tensor | nvlink5 | infiniband_ndr | 244 | 892.64 us | 112.0 tok/s | 1,120.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 19 on infiniband_ndr (traversals 2.0) = 594.74 us |
| DSV4-Pro/b200_sxm-x149-hybrid | DeepSeek-V4-Pro-0813 | 149 | hybrid | nvlink5 | infiniband_ndr | 140 | 339.60 us | 294.5 tok/s | 2,944.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 18 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 41.70 us |
| DSV4-Pro/b200_sxm-x157-pipeline | DeepSeek-V4-Pro-0813 | 157 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x157-tensor | DeepSeek-V4-Pro-0813 | 157 | tensor | nvlink5 | infiniband_ndr | 244 | 892.91 us | 112.0 tok/s | 1,119.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 20 on infiniband_ndr (traversals 2.0) = 595.01 us |
| DSV4-Pro/b200_sxm-x157-hybrid | DeepSeek-V4-Pro-0813 | 157 | hybrid | nvlink5 | infiniband_ndr | 141 | 341.92 us | 292.5 tok/s | 2,924.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 19 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 44.02 us |
| DSV4-Pro/b200_sxm-x165-pipeline | DeepSeek-V4-Pro-0813 | 165 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x165-tensor | DeepSeek-V4-Pro-0813 | 165 | tensor | nvlink5 | infiniband_ndr | 244 | 893.16 us | 112.0 tok/s | 1,119.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 21 on infiniband_ndr (traversals 2.0) = 595.26 us |
| DSV4-Pro/b200_sxm-x165-hybrid | DeepSeek-V4-Pro-0813 | 165 | hybrid | nvlink5 | infiniband_ndr | 142 | 344.24 us | 290.5 tok/s | 2,905.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 20 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.33 us |
| DSV4-Pro/b200_sxm-x173-pipeline | DeepSeek-V4-Pro-0813 | 173 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x173-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5 | infiniband_ndr | 244 | 893.39 us | 111.9 tok/s | 1,119.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 595.49 us |
| DSV4-Pro/b200_sxm-x173-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5 | infiniband_ndr | 143 | 346.55 us | 288.6 tok/s | 2,885.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 48.65 us |
| DSV4-Pro/b200_sxm-x231-pipeline | DeepSeek-V4-Pro-0813 | 231 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x231-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5 | infiniband_ndr | 244 | 894.54 us | 111.8 tok/s | 1,117.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 596.64 us |
| DSV4-Pro/b200_sxm-x231-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5 | infiniband_ndr | 150 | 362.77 us | 275.7 tok/s | 2,756.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 64.87 us |
| DSV4-Pro/b200_sxm-x347-pipeline | DeepSeek-V4-Pro-0813 | 347 | pipeline | nvlink5 | infiniband_ndr | 60 | 80.66 us | 1,239.8 tok/s | 12,397.5 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 16.22 us |
| DSV4-Pro/b200_sxm-x347-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5 | infiniband_ndr | 244 | 895.78 us | 111.6 tok/s | 1,116.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 597.87 us |
| DSV4-Pro/b200_sxm-x347-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5 | infiniband_ndr | 165 | 397.52 us | 251.6 tok/s | 2,515.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 99.62 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x3 | 138,675 | 2,648.8 | 0.019 | 1,041.6 (120,620) | 2,648.8 (138,675) | 2.54x | link_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,648.8 | 0.019 | 918.1 (131,215) | 2,648.8 (138,675) | 2.88x | link_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,648.3 | 0.019 | 857.6 (131,215) | 2,648.3 (138,675) | 3.09x | link_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,646.5 | 0.019 | 857.6 (131,215) | 2,646.5 (138,675) | 3.09x | link_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 2,426.5 | 0.017 | 857.6 (131,215) | 2,426.5 (138,675) | 2.83x | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,364.4 | 0.013 | 825.3 (138,550) | 2,364.4 (184,900) | 2.87x | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 2,219.3 | 0.008 | 705.4 (138,550) | 2,219.3 (277,350) | 3.15x | link_latency |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,613.7 | 0.003 | 627.5 (185,005) | 1,613.7 (554,700) | 2.57x | link_latency |

## The two ROM floorplans on one die

This probe requests 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. The ROM-plus-MAC floorplan holds the requested weights; the compute-in-ROM floorplan holds only 87.0% and is infeasible at this area. The failed floorplan is retained so the capacity cost of the larger cell remains visible.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 374.6 mm2 | 521.6 mm2 |
| weight capacity | 3.51 GB (100.0%) | 3.06 GB (87.0%) |
| capacity-feasible | yes | **no** |
| compute block | 293.7 mm2 | 146.7 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 0.0 mm2 |
| sustained fp8 compute roof | 2.197e+14 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 1.098e+14 | n/a |
| weight bytes/s the array supplies | 1.019e+14 | 8.872e+13 |
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

`docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md` names an open
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
subject of `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md`: its sweep depth
is the load of the **busiest** expert region, computed from the routing
distribution rather than from the mean engaged region.

| Model | B | Spare silicon | Batched aggregate | Per-stream aggregate | Per-region aggregate | Per-stream penalty | Per-region over broadcast | Batched binds on | Per-stream binds on | Per-region binds on |
|---|---:|---|---:|---:|---:|---:|---:|---|---|---|
| DeepSeek-V4-Pro-0813 | 1 | sram | 26,083.1 | 26,053.1 | 26,053.1 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 26,083.1 | 26,053.1 | 26,053.1 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 26,083.1 | 26,053.1 | 26,053.1 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 26,083.1 | 26,053.1 | 26,053.1 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 38,823.3 | 26,053.1 | 28,943.2 | 1.49x | 1.11x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | sram | 75,662.3 | 26,053.1 | 48,310.3 | 2.90x | 1.85x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 130,773.3 | 26,053.1 | 81,807.8 | 5.02x | 3.14x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 344,285.4 | 26,053.1 | 209,544.8 | 13.21x | 8.04x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 71,184.8 | 29,915.9 | 29,915.9 | 2.38x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 71,184.8 | 29,915.9 | 29,915.9 | 2.38x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 71,184.8 | 29,915.9 | 29,915.9 | 2.38x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 71,184.8 | 29,915.9 | 29,915.9 | 2.38x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 71,184.8 | 29,915.9 | 30,927.7 | 2.38x | 1.03x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | rom | 75,662.3 | 29,915.9 | 52,211.0 | 2.53x | 1.75x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 142,032.2 | 29,915.9 | 89,180.9 | 4.75x | 2.98x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 413,111.5 | 29,915.9 | 232,276.8 | 13.81x | 7.76x | link_latency | weight_read | weight_read |

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
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 71,184.8 | 0.128 | weight_read | 2.73x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 71,184.8 | 0.128 | weight_read | 2.73x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 71,184.8 | 0.128 | weight_read | 2.73x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 71,184.8 | 0.128 | weight_read | 2.73x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perregion-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 1.15x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 38,823.3 | 0.280 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 2.73 | 1.00 | 71,184.8 | 0.128 | weight_read | 1.83x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 0.67x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 0.77x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 1.19 | 28,943.2 | 0.104 | link_latency | 0.75x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion-romfill | 277,350 | 1.15 | 1.19 | 30,927.7 | 0.112 | link_latency | 0.80x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 75,662.3 | 0.409 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 1.00 | 1.00 | 75,662.3 | 0.409 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 0.34x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 0.40x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 1.66 | 48,310.3 | 0.174 | weight_read | 0.64x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion-romfill | 277,350 | 1.15 | 1.66 | 52,211.0 | 0.188 | weight_read | 0.69x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 130,773.3 | 0.707 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 1.37 | 1.00 | 142,032.2 | 0.512 | link_latency | 1.09x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 0.20x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 0.23x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 2.18 | 81,807.8 | 0.295 | weight_read | 0.63x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion-romfill | 277,350 | 1.15 | 2.18 | 89,180.9 | 0.322 | weight_read | 0.68x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 344,285.4 | 0.931 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2.73 | 1.00 | 413,111.5 | 0.745 | link_latency | 1.20x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream | 277,350 | 1.00 | 1.00 | 26,053.1 | 0.094 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x6-perstream-romfill | 277,350 | 1.15 | 1.00 | 29,915.9 | 0.108 | weight_read | 0.09x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion | 277,350 | 1.00 | 4.02 | 209,544.8 | 0.756 | weight_read | 0.61x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-perregion-romfill | 277,350 | 1.15 | 4.02 | 232,276.8 | 0.837 | weight_read | 0.67x |

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
| DeepSeek-V4-Pro-0813 | 1 | 293 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 341 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 341 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 341 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 341 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 341 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 323 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 323 | 1.00 | 1.000 | 1.000 | 1.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 1 | 9 | 4.56 | 3.12 | 1.46x |
| DeepSeek-V4-Pro-0813 | 2 | 9 | 4.56 | 3.12 | 1.46x |
| DeepSeek-V4-Pro-0813 | 4 | 9 | 4.56 | 3.12 | 1.46x |
| DeepSeek-V4-Pro-0813 | 8 | 9 | 4.56 | 3.12 | 1.46x |
| DeepSeek-V4-Pro-0813 | 16 | 9 | 6.42 | 3.75 | 1.71x |
| DeepSeek-V4-Pro-0813 | 32 | 9 | 8.23 | 4.54 | 1.81x |
| DeepSeek-V4-Pro-0813 | 64 | 9 | 8.93 | 5.31 | 1.68x |
| DeepSeek-V4-Pro-0813 | 256 | 9 | 9.00 | 6.58 | 1.37x |
| DeepSeek-V4-Pro-0813 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 2 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 8 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 16 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 32 | 29 | 6.01 | 4.50 | 1.34x |
| DeepSeek-V4-Pro-0813 | 64 | 29 | 10.70 | 6.10 | 1.75x |
| DeepSeek-V4-Pro-0813 | 256 | 29 | 23.96 | 10.50 | 2.28x |
| DeepSeek-V4-Pro-0813 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 2 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 4 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 8 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 16 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 32 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 64 | 58 | 6.30 | 5.21 | 1.21x |
| DeepSeek-V4-Pro-0813 | 256 | 58 | 20.96 | 10.41 | 2.01x |
| DeepSeek-V4-Pro-0813 | 1 | 75 | 5.80 | 5.10 | 1.14x |
| DeepSeek-V4-Pro-0813 | 2 | 75 | 5.80 | 5.10 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 75 | 5.80 | 5.10 | 1.14x |
| DeepSeek-V4-Pro-0813 | 8 | 75 | 5.80 | 5.10 | 1.14x |
| DeepSeek-V4-Pro-0813 | 16 | 75 | 5.80 | 5.10 | 1.14x |
| DeepSeek-V4-Pro-0813 | 32 | 75 | 5.80 | 5.10 | 1.14x |
| DeepSeek-V4-Pro-0813 | 64 | 75 | 5.80 | 5.10 | 1.14x |
| DeepSeek-V4-Pro-0813 | 256 | 75 | 17.73 | 9.75 | 1.82x |
| DeepSeek-V4-Pro-0813 | 1 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4-Pro-0813 | 2 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4-Pro-0813 | 8 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4-Pro-0813 | 16 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4-Pro-0813 | 32 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4-Pro-0813 | 64 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4-Pro-0813 | 256 | 76 | 17.56 | 9.72 | 1.81x |
| DeepSeek-V4-Pro-0813 | 1 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 4 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 8 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 16 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 32 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 64 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Pro-0813 | 256 | 81 | 16.75 | 9.55 | 1.75x |
| DeepSeek-V4-Pro-0813 | 1 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Pro-0813 | 4 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Pro-0813 | 8 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Pro-0813 | 16 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Pro-0813 | 32 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Pro-0813 | 64 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Pro-0813 | 256 | 82 | 16.59 | 9.52 | 1.74x |
| DeepSeek-V4-Pro-0813 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 4 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 8 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 16 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 32 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 64 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 256 | 87 | 15.84 | 9.37 | 1.69x |
| DeepSeek-V4-Pro-0813 | 1 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Pro-0813 | 4 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Pro-0813 | 8 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Pro-0813 | 16 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Pro-0813 | 32 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Pro-0813 | 64 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Pro-0813 | 256 | 92 | 15.15 | 9.25 | 1.64x |
| DeepSeek-V4-Pro-0813 | 1 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 4 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 8 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 16 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 32 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 64 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 256 | 98 | 14.38 | 9.12 | 1.58x |
| DeepSeek-V4-Pro-0813 | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 4 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 8 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 16 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 32 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 64 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 256 | 110 | 13.04 | 8.88 | 1.47x |
| DeepSeek-V4-Pro-0813 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 4 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 8 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 16 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 32 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 64 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 256 | 116 | 12.45 | 8.77 | 1.42x |
| DeepSeek-V4-Pro-0813 | 1 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 4 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 8 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 16 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 32 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 64 | 118 | 5.87 | 5.38 | 1.09x |
| DeepSeek-V4-Pro-0813 | 256 | 118 | 12.27 | 8.73 | 1.41x |
| DeepSeek-V4-Pro-0813 | 1 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 4 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 8 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 16 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 32 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 64 | 147 | 5.90 | 5.49 | 1.08x |
| DeepSeek-V4-Pro-0813 | 256 | 147 | 10.06 | 8.12 | 1.24x |
| DeepSeek-V4-Pro-0813 | 1 | 149 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 149 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 149 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 149 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 149 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 149 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 149 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 149 | 9.94 | 8.07 | 1.23x |
| DeepSeek-V4-Pro-0813 | 1 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 157 | 5.91 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 157 | 9.47 | 7.88 | 1.20x |
| DeepSeek-V4-Pro-0813 | 1 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 165 | 9.04 | 7.69 | 1.18x |
| DeepSeek-V4-Pro-0813 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 4 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 8 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 16 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 32 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 64 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 256 | 173 | 8.65 | 7.49 | 1.15x |
| DeepSeek-V4-Pro-0813 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 231 | 6.56 | 6.17 | 1.06x |
| DeepSeek-V4-Pro-0813 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 347 | 5.96 | 5.77 | 1.03x |

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
| gpu | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 1.4% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 4.7% |

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
| DeepSeek-V4-Pro-0813 | 1 | 293 | 94.10% | 611.69 | 2.22 |
| DeepSeek-V4-Pro-0813 | 2 | 6 | 2.03% | 15.33 | 2.22 |
| DeepSeek-V4-Pro-0813 | 4 | 6 | 2.03% | 15.33 | 2.22 |
| DeepSeek-V4-Pro-0813 | 8 | 6 | 2.03% | 15.33 | 2.22 |
| DeepSeek-V4-Pro-0813 | 16 | 6 | 2.03% | 15.33 | 2.22 |
| DeepSeek-V4-Pro-0813 | 32 | 6 | 2.03% | 15.33 | 2.22 |

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
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 121.5 | 19,310.8 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 121.5 | 19,310.8 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 121.5 | 19,310.8 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 121.5 | 19,310.8 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 121.5 | 19,310.8 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 121.5 | 19,310.8 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 121.5 | 19,310.8 |
| DeepSeek-V4-Pro-0813 | 256 | 2.50% | 47.4 GB | 5.31% | 1,375.40 TB/s | 25,902.15 TB/s | 75.8 | 19,396.0 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | link_latency | 151 |
| gpu | weight_read | 329 |
| rom | compute | 56 |
| rom | infeasible | 684 |
| rom | kv_read | 6 |
| rom | link_latency | 404 |
| rom | weight_read | 482 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 684 |

## Mechanical consistency audit

**PASS** over 44,985 checks.

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 70 |
| derived | 41 |
| assumed | 60 |

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
  2.3-2.9x low on the other.** Leakage, clock distribution, operand
  delivery and a measured clocked-idle floor are charged per mm2 per
  second whether or not a byte moves, and the HBM traffic energy is a
  measured SC 2025 figure rather than an HBM2-era model. The A100 lands
  at 1.15x of its published TDP under a saturating load; the Taalas HC1
  lands at 0.35x of its published card power. **The second one FAILS its
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

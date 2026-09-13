# Area-constrained roofline: n6_vs_a100-flash-32k

> CONTEXT-LADDER RUNG of n6_vs_a100: DeepSeek-V4-Flash-0731 at 32,768 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 467x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 1 device. On the GPU side the correction reaches 507x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 92 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Flash-0731 takes 1 x 46,225 mm2 (46,225 mm2, wafer, KV in HBM) at 4,708 tok/s per user and 102 tok/s per 1,000 mm2, holding 2,679 sessions, against 56 copies of one unified HBM die at the same silicon: 6.5x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Flash-0731 on 277,350 mm2 of ROM silicon at 4,060 tok/s per user against 277,536 mm2 of a100_sxm_80gb-x336-tensor at 623 tok/s: **6.5x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 103,968. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 152.82x to it.** At 554,700 mm2 on DeepSeek-V4-Flash-0731 the pipeline-only GPU delivers 4.11 tok/s and the same silicon running tensor delivers 628 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.60x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 73.36x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 17.4% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 531 to 21,759 tok/s, and its rate with every slot occupied from 20,725 to 21,759. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 39 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,218 us over NVLink, capping per-user decode at 821 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 165.6 us and cap it at 6,040 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 5.2x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 8 of 8 operating points and an array 0; on tokens per second per square millimetre the same points go 0 to the array and 8 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 11 of 1996 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 22.1x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 11.37x, on DeepSeek-V4-Flash-0731 at batch 256, where the busiest region carries 2.79x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 16 of 16 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 75% of its cooling budget. The companion study at the other node does have power-limited points.


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

### DeepSeek-V4-Flash-0731 at 32,768 tokens

**Recommended: `ROM-N6-native-HBMKV-wafer-tensor-x1`** -- 1 x 46,225 mm2 wafer, 46,225 mm2 total, `tensor`-parallel, KV in HBM, spare silicon to `sram`.

- **4,707.9 tok/s per user** (0.21 ms/token), binding on `link_latency`
- **101.8 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,708 tok/s aggregate with every slot full, over 2,679 resident sessions (fill limited by `batch`)
- 4,006 W at 0.087 W/mm2, 851.0 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 56 copies of one unified HBM die -- `a100_sxm_80gb-x56-tensor`, 46,256 mm2, area ratio 0.9993 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 46,225 | 46,256 | 0.9993 |
| user tok/s | 4,707.9 | 723.1 | 6.51x |
| aggregate tok/s | 4,708 | 723 | 6.51x |
| resident sessions | 2,679 | 16,726 | -- |
| J/token | 0.8510 | 12.3696 | 14.5x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 2,679 sessions against one that holds 16,726 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x224-tensor` at 185,024 mm2 and 787.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 101.8 | 1 | 6.51x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 101.8 | 1 | 6.51x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hybrid-x36` | 29,340 | 1,403.5 | 47.8 | 1 | 2.05x |
| **after -- this report's rule** | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 101.8 | 2,679 | 6.51x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-HBMKV-wafer-tensor-x1` **<-- recommended** | 46,225 | 1 | 4,707.9 | 4,708 | 101.8 | 2,679 | `link_latency` | 4,006 | 851.0 | `a100_sxm_80gb-x56-tensor` | 6.51x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 144 | densest | `ROM-N6-native-SRAMKV-array-hybrid-x37` | 30,155 | 1,539.7 | 51.1 | 1 |
| array | 144 | fastest | `ROM-N6-native-SRAMKV-array-hybrid-x37` | 30,155 | 1,539.7 | 51.1 | 1 |
| array | 144 | smallest | `ROM-N6-native-SRAMKV-array-hybrid-x36` | 29,340 | 1,403.5 | 47.8 | 1 |
| wafer | 80 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 101.8 | 1 |
| wafer | 80 | fastest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 101.8 | 1 |
| wafer | 80 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 101.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hybrid-x37` | 30,155 | 1,539.7 | 1,540 | 1 | 1,858 | 1,206.5 | `link_latency` | `a100_sxm_80gb-x37-tensor` | 687.1 | 10,806 | 8,963.6 | 0.987 | 2.24x | 7.4x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 4,708 | 1 | 3,844 | 816.6 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 723.1 | 16,726 | 12,369.6 | 0.999 | 6.51x | 15.1x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x56` | 45,640 | 1,368.4 | 9,579 | 17,448 | 4,642 | 484.6 | `link_latency` | `a100_sxm_80gb-x55-tensor` | 721.6 | 16,414 | 12,192.3 | 1.005 | 1.90x | 25.2x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | -- | 1 | -- | 816.6 | -- | -- | -- | -- | -- | 0.987 | 3.44x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hybrid-x40` | 32,600 | 1,539.7 | 7,699 | 12,463 | 2,505 | 325.4 | `link_latency` | `a100_sxm_80gb-x39-tensor` | 583.2 | 11,429 | 5,603.6 | 1.012 | 2.64x | 17.2x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 9,416 | 2,679 | 4,050 | 430.1 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 614.5 | 16,726 | 7,354.8 | 0.999 | 7.66x | 17.1x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x56` | 45,640 | 1,368.4 | 9,579 | 17,448 | 4,642 | 484.6 | `link_latency` | `a100_sxm_80gb-x55-tensor` | 612.8 | 16,414 | 7,254.6 | 1.005 | 2.23x | 15.0x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | -- | 2,679 | -- | 430.1 | -- | -- | -- | -- | -- | 0.987 | 3.44x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hybrid-x40` | 32,600 | 1,539.7 | 7,699 | 12,463 | 2,505 | 325.4 | `link_latency` | `a100_sxm_80gb-x39-tensor` | 467.8 | 11,429 | 3,572.5 | 1.012 | 3.29x | 11.0x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 18,832 | 2,679 | 4,137 | 219.7 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 495.2 | 16,726 | 4,645.3 | 0.999 | 9.51x | 21.1x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x56` | 45,640 | 1,368.4 | 9,579 | 17,448 | 4,642 | 484.6 | `link_latency` | `a100_sxm_80gb-x55-tensor` | 493.7 | 16,414 | 4,584.2 | 1.005 | 2.77x | 9.5x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | -- | 2,679 | -- | 219.7 | -- | -- | -- | -- | -- | 0.987 | 3.44x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hybrid-x47` | 38,305 | 1,443.6 | 11,549 | 14,644 | 3,469 | 300.4 | `link_latency` | `a100_sxm_80gb-x46-tensor` | 360.8 | 13,610 | 2,746.3 | 1.008 | 4.00x | 9.1x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | 37,663 | 2,679 | 4,311 | 114.5 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 373.5 | 16,726 | 3,151.1 | 0.999 | 12.60x | 27.5x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x56` | 45,640 | 1,366.3 | 10,930 | 17,448 | 4,655 | 425.9 | `link_latency` | `a100_sxm_80gb-x55-tensor` | 372.2 | 16,414 | 3,112.2 | 1.005 | 3.67x | 7.3x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | 4,707.9 | -- | 2,679 | -- | 114.5 | -- | -- | -- | -- | -- | 0.987 | 3.45x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hybrid-x47` | 38,305 | 1,422.2 | 22,756 | 14,644 | 3,573 | 157.0 | `link_latency` | `a100_sxm_80gb-x46-tensor` | 253.7 | 13,610 | 2,001.7 | 1.008 | 5.61x | 12.7x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,406.4 | 70,503 | 5,359 | 9,269 | 131.5 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 290.7 | 34,174 | 3,841.5 | 0.999 | 15.16x | 29.2x |
| 16 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x111-romfill` | 90,465 | 1,229.0 | 19,664 | 34,585 | 10,272 | 522.4 | `link_latency` | `a100_sxm_80gb-x110-tensor` | 290.0 | 33,551 | 3,788.4 | 0.996 | 4.24x | 7.3x |
| 16 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,406.4 | -- | 5,359 | -- | 131.5 | -- | -- | -- | -- | -- | 0.979 | 3.59x wafer/array | -- |
| 32 | array | `ROM-N6-native-HBMKV-array-hybrid-x56` | 45,640 | 1,316.1 | 42,116 | 17,448 | 4,943 | 117.4 | `link_latency` | `a100_sxm_80gb-x55-tensor` | 174.7 | 16,414 | 1,712.5 | 1.005 | 7.54x | 14.6x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,205.0 | 134,559 | 10,718 | 18,477 | 137.3 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 204.7 | 69,071 | 5,229.4 | 0.999 | 20.54x | 38.1x |
| 32 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 1,171.7 | 37,495 | 70,728 | 20,979 | 559.5 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 204.7 | 69,071 | 5,229.4 | 1.000 | 5.72x | 9.3x |
| 32 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 4,205.0 | -- | 10,718 | -- | 137.3 | -- | -- | -- | -- | -- | 1.001 | 3.59x wafer/array | -- |
| 64 | array | `ROM-N6-native-HBMKV-array-hybrid-x57` | 46,455 | 1,203.9 | 77,050 | 17,760 | 5,398 | 70.1 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 112.3 | 16,726 | 1,335.5 | 1.004 | 10.72x | 19.1x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 3,915.3 | 250,581 | 16,077 | 28,155 | 112.4 | `link_latency` | `a100_sxm_80gb-x336-tensor` | 122.6 | 103,968 | 6,393.2 | 0.999 | 31.94x | 56.9x |
| 64 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 277,100 | 1,128.8 | 72,243 | 84,749 | 30,385 | 420.6 | `link_latency` | `a100_sxm_80gb-x335-tensor` | 122.6 | 103,657 | 6,376.0 | 1.001 | 9.21x | 15.2x |
| 64 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 3,915.3 | -- | 16,077 | -- | 112.4 | -- | -- | -- | -- | -- | 0.999 | 3.47x wafer/array | -- |
| 256 | array | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 1,028.9 | 263,394 | 70,728 | 23,052 | 87.5 | `link_latency` | `a100_sxm_80gb-x224-hybrid` | 42.4 | 69,071 | 3,410.7 | 1.000 | 24.29x | 39.0x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,899.7 | 742,331 | 32,155 | 58,424 | 78.7 | `link_latency` | `a100_sxm_80gb-x672-tensor` | 39.5 | 208,659 | 9,660.9 | 0.999 | 73.36x | 122.7x |

**One design wins at every batch this study evaluates.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-256 | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | wafer | HBM | 2,679 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 39, 40, 47, 56, 57, 74, 111, 113, 148, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 39, 40, 47, 56, 57, 74, 111, 113, 148, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 36, 37, 44, 53, 57, 70, 105, 113, 140, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 36, 37, 44, 53, 57, 70, 105, 113, 140, 170, 227, 340 |

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

- **0 of 1,996 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 75% of its cooling budget, and the busiest wafer-scale ROM design 31%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 144 | 0 | 47.9% | 57.8% | 0.280 | 75% |
| gpu | small array (1,600-5,000 mm2) | 16 | 0 | 71.5% | 75.4% | 0.365 | 50% |
| gpu | wafer (>=40,000 mm2) | 504 | 0 | 41.1% | 53.8% | 0.261 | 88% |
| rom | large array (5,000-40,000 mm2) | 162 | 0 | 15.9% | 22.7% | 0.114 | 96% |
| rom | wafer (>=40,000 mm2) | 1,170 | 0 | 20.8% | 31.3% | 0.157 | 98% |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | `DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1` | 0.816574 | 3,844.4 | link_latency | `DSV4-Flash/a100_sxm_80gb-x56-tensor` | 12.369585 | 8,944.7 | link_latency | 15.15x |
| DeepSeek-V4-Flash-0731 | 2 | 46,225 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1` | 0.430139 | 4,050.1 | link_latency | `DSV4-Flash/a100_sxm_80gb-x56-tensor` | 7.354817 | 9,038.7 | link_latency | 17.10x |
| DeepSeek-V4-Flash-0731 | 4 | 46,225 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1` | 0.219704 | 4,137.4 | link_latency | `DSV4-Flash/a100_sxm_80gb-x56-tensor` | 4.645325 | 9,201.0 | link_latency | 21.14x |
| DeepSeek-V4-Flash-0731 | 8 | 46,225 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1` | 0.114452 | 4,310.6 | link_latency | `DSV4-Flash/a100_sxm_80gb-x56-tensor` | 3.151069 | 9,416.1 | link_latency | 27.53x |
| DeepSeek-V4-Flash-0731 | 16 | 92,450 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 0.131475 | 9,269.4 | link_latency | `DSV4-Flash/a100_sxm_80gb-x112-tensor` | 3.841521 | 17,870.7 | link_latency | 29.22x |
| DeepSeek-V4-Flash-0731 | 32 | 138,675 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 0.105610 | 14,160.6 | link_latency | `DSV4-Flash/a100_sxm_80gb-x168-tensor` | 4.085823 | 26,121.1 | link_latency | 38.69x |
| DeepSeek-V4-Flash-0731 | 64 | 277,350 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 0.112359 | 28,155.1 | link_latency | `DSV4-Flash/a100_sxm_80gb-x336-tensor` | 6.393242 | 50,165.0 | link_latency | 56.90x |
| DeepSeek-V4-Flash-0731 | 256 | 554,700 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.078704 | 58,424.2 | link_latency | `DSV4-Flash/a100_sxm_80gb-x672-tensor` | 9.660858 | 97,760.0 | link_latency | 122.75x |

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
| DeepSeek-V4-Flash-0731 | 32,768 | 284 B | 166.9 GB | 4.70 | 0.066 GB | 0.231 GB | 170.1 |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 19,190.8 | wafer-pipeline | 4,707.9 | wafer-tensor | 4.08x | 1,586.3 | pipeline | 723.1 | tensor | 2.19x | 12.10x | 6.51x | 0.54x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 25,511.9 | wafer-pipeline | 4,422.7 | wafer-hybrid | 5.77x | 1,816.5 | pipeline | 763.9 | tensor | 2.38x | 14.04x | 5.79x | 0.41x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 31,242.4 | wafer-pipeline | 4,326.3 | wafer-hybrid | 7.22x | 1,913.2 | pipeline | 779.3 | tensor | 2.46x | 16.33x | 5.55x | 0.34x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 35,193.1 | wafer-pipeline | 4,233.8 | wafer-hybrid | 8.31x | 1,966.5 | pipeline | 787.4 | tensor | 2.50x | 17.90x | 5.38x | 0.30x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 40,285.5 | wafer-pipeline | 4,060.2 | wafer-hybrid | 9.92x | 2,023.6 | pipeline | 622.7 | tensor | 3.25x | 19.91x | 6.52x | 0.33x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 43,426.5 | wafer-pipeline | 3,900.1 | wafer-hybrid | 11.13x | 2,053.7 | pipeline | 625.3 | tensor | 3.28x | 21.15x | 6.24x | 0.29x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 47,098.2 | wafer-pipeline | 3,615.1 | wafer-hybrid | 13.03x | 2,084.9 | pipeline | 628.0 | tensor | 3.32x | 22.59x | 5.76x | 0.25x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.25x to 0.54x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | 46,225 | 4,707.9 | 4,707.9 | link_latency | DSV4-Flash/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 857.79 | 723.1 | 723.1 | link_latency | 6.51x | 6.51x | 135.73x | 6.51x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x36 | 29,340 | 1,403.5 | 1,403.5 | link_latency | DSV4-Flash/a100_sxm_80gb-x36-tensor | 29,736 | 0.99x | tensor | 852.96 | 684.2 | 684.2 | link_latency | 2.05x | 2.05x | 30.27x | 2.05x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 4,707.9 | 9,415.8 | link_latency | DSV4-Flash/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 936.42 | 614.5 | 1,228.9 | link_latency | 7.66x | 7.66x | 135.73x | 7.66x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x39 | 31,785 | 1,458.9 | 7,294.7 | link_latency | DSV4-Flash/a100_sxm_80gb-x38-tensor | 31,388 | 1.01x | tensor | 926.76 | 580.5 | 1,161.0 | link_latency | 2.51x | 6.28x | 32.55x | 2.51x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 4,707.9 | 18,831.6 | link_latency | DSV4-Flash/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 1,093.67 | 495.2 | 1,980.7 | link_latency | 9.51x | 9.51x | 135.73x | 9.51x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x39 | 31,785 | 1,458.9 | 7,294.7 | link_latency | DSV4-Flash/a100_sxm_80gb-x38-tensor | 31,388 | 1.01x | tensor | 1,074.35 | 465.3 | 1,861.1 | link_latency | 3.14x | 3.92x | 32.55x | 3.14x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 4,707.9 | 37,663.2 | link_latency | DSV4-Flash/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 1,408.19 | 373.5 | 2,988.2 | link_latency | 12.60x | 12.60x | 135.73x | 12.60x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x39 | 31,785 | 1,210.1 | 9,680.9 | link_latency | DSV4-Flash/a100_sxm_80gb-x38-tensor | 31,388 | 1.01x | tensor | 1,369.54 | 348.0 | 2,783.7 | link_latency | 3.48x | 3.48x | 26.99x | 3.48x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,406.4 | 70,503.2 | link_latency | DSV4-Flash/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 2,133.84 | 290.7 | 4,652.0 | link_latency | 15.16x | 15.16x | 214.13x | 15.16x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x39 | 31,785 | 831.8 | 13,308.6 | compute | DSV4-Flash/a100_sxm_80gb-x38-tensor | 31,388 | 1.01x | tensor | 1,959.92 | 244.1 | 3,905.7 | link_latency | 3.41x | 3.41x | 18.56x | 3.41x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,205.0 | 134,559.0 | link_latency | DSV4-Flash/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 3,585.13 | 204.7 | 6,550.0 | link_latency | 20.54x | 20.54x | 368.62x | 20.54x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x39 | 31,785 | 531.4 | 20,725.2 | compute | DSV4-Flash/a100_sxm_80gb-x38-tensor | 31,388 | 1.01x | tensor | 3,140.68 | 163.2 | 5,222.7 | link_latency | 3.26x | 3.97x | 11.85x | 3.26x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 3,915.3 | 250,581.4 | link_latency | DSV4-Flash/a100_sxm_80gb-x336-tensor | 277,536 | 1.00x | tensor | 6,804.67 | 122.6 | 7,846.6 | link_latency | 31.94x | 31.94x | 495.74x | 31.94x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x39 | 31,785 | 331.1 | 21,189.3 | compute | DSV4-Flash/a100_sxm_80gb-x38-tensor | 31,388 | 1.01x | tensor | 5,502.21 | 106.3 | 6,804.8 | link_latency | 3.11x | 3.11x | 9.16x | 3.11x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,899.7 | 742,330.6 | link_latency | DSV4-Flash/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 24,091.39 | 39.5 | 10,119.2 | link_latency | 73.36x | 73.36x | 705.64x | 73.36x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x39 | 31,785 | 85.0 | 21,759.5 | compute | DSV4-Flash/a100_sxm_80gb-x38-hybrid | 31,388 | 1.01x | hybrid | 820.85 | 53.0 | 13,566.0 | weight_read | 1.60x | 1.60x | 4.43x | 1.60x |

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
| DeepSeek-V4-Flash-0731 | 4 | 3,304 | 119.2 | 393.7 | — | tensor | 435.28 | 17.1% | weight_read |
| DeepSeek-V4-Flash-0731 | 36 | 29,736 | 46.4 | 684.2 | 290.7 | tensor | 852.96 | 58.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 37 | 30,562 | 45.6 | 687.1 | 293.4 | tensor | 852.96 | 58.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 38 | 31,388 | 44.8 | 689.8 | 295.9 | tensor | 852.96 | 58.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 39 | 32,214 | 44.1 | 692.5 | 298.4 | tensor | 852.96 | 59.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 43 | 35,518 | 41.4 | 700.8 | 262.3 | tensor | 855.78 | 60.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 46 | 37,996 | 39.6 | 707.1 | 267.6 | tensor | 855.78 | 60.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 52 | 42,952 | 36.5 | 717.0 | 241.8 | tensor | 857.79 | 61.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 55 | 45,430 | 35.1 | 721.6 | 245.6 | tensor | 857.79 | 61.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 56 | 46,256 | 34.7 | 723.1 | 246.8 | tensor | 857.79 | 62.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 69 | 56,994 | 29.9 | 737.4 | 207.6 | tensor | 860.47 | 63.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 70 | 57,820 | 29.6 | 738.4 | 208.3 | tensor | 860.47 | 63.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 73 | 60,298 | 28.7 | 740.8 | 191.2 | tensor | 861.41 | 63.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 77 | 63,602 | 27.6 | 744.3 | 193.5 | tensor | 861.41 | 64.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 82 | 67,732 | 26.3 | 747.8 | 179.8 | tensor | 862.18 | 64.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 92 | 75,992 | 24.1 | 754.2 | 170.0 | tensor | 862.82 | 65.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 104 | 85,904 | 21.8 | 760.5 | 161.7 | tensor | 863.36 | 65.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 110 | 90,860 | 20.9 | 763.0 | 152.4 | tensor | 863.83 | 65.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 111 | 91,686 | 20.7 | 763.5 | 152.7 | tensor | 863.83 | 66.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 112 | 92,512 | 20.6 | 763.9 | 152.9 | tensor | 863.83 | 66.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 138 | 113,988 | 17.3 | 772.4 | 125.0 | tensor | 865.17 | 66.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 146 | 120,596 | 16.5 | 774.4 | 119.8 | tensor | 865.42 | 67.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 168 | 138,768 | 14.7 | 779.3 | 111.1 | tensor | 865.84 | 67.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 224 | 185,024 | 11.4 | 787.4 | 87.3 | tensor | 866.85 | 68.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 335 | 276,710 | 7.9 | 622.7 | 61.1 | tensor | 1,217.01 | 75.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 336 | 277,536 | 7.9 | 622.7 | 61.1 | tensor | 1,217.01 | 75.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 448 | 370,048 | 6.0 | 625.3 | 47.1 | tensor | 1,217.52 | 76.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 672 | 555,072 | 4.1 | 628.0 | 32.3 | tensor | 1,218.02 | 76.5% | link_latency |

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
| DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x37 | DeepSeek-V4-Flash-0731 | 37 | pipeline | nvlink3 | infiniband_hdr | 36 | 90.30 us | 1,107.4 tok/s | 11,073.6 tok/s | 32 x point_to_point span 2 on nvlink3 (traversals 1.0) = 80.87 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-tensor-x36 | DeepSeek-V4-Flash-0731 | 36 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x37 | DeepSeek-V4-Flash-0731 | 37 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x40 | DeepSeek-V4-Flash-0731 | 40 | pipeline | nvlink3 | infiniband_hdr | 39 | 97.89 us | 1,021.6 tok/s | 10,215.9 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.46 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-tensor-x39 | DeepSeek-V4-Flash-0731 | 39 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x40 | DeepSeek-V4-Flash-0731 | 40 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x4-pipeline | DeepSeek-V4-Flash-0731 | 4 | pipeline | nvlink3 | infiniband_hdr | 3 | 7.58 us | 13,189.3 tok/s | 131,892.7 tok/s | 3 x point_to_point span 2 on nvlink3 (traversals 1.0) = 7.58 us |
| DSV4-Flash/a100_sxm_80gb-x4-tensor | DeepSeek-V4-Flash-0731 | 4 | tensor | nvlink3 | infiniband_hdr | 86 | 435.28 us | 229.7 tok/s | 2,297.4 tok/s | 86 x all_reduce span 4 on nvlink3 (traversals 2.0) = 435.28 us |
| DSV4-Flash/a100_sxm_80gb-x36-pipeline | DeepSeek-V4-Flash-0731 | 36 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x36-tensor | DeepSeek-V4-Flash-0731 | 36 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x36-hybrid | DeepSeek-V4-Flash-0731 | 36 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-pipeline | DeepSeek-V4-Flash-0731 | 37 | pipeline | nvlink3 | infiniband_hdr | 36 | 90.30 us | 1,107.4 tok/s | 11,073.6 tok/s | 32 x point_to_point span 2 on nvlink3 (traversals 1.0) = 80.87 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-tensor | DeepSeek-V4-Flash-0731 | 37 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x37-hybrid | DeepSeek-V4-Flash-0731 | 37 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x38-pipeline | DeepSeek-V4-Flash-0731 | 38 | pipeline | nvlink3 | infiniband_hdr | 37 | 92.83 us | 1,077.2 tok/s | 10,772.2 tok/s | 33 x point_to_point span 2 on nvlink3 (traversals 1.0) = 83.40 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x38-tensor | DeepSeek-V4-Flash-0731 | 38 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x38-hybrid | DeepSeek-V4-Flash-0731 | 38 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x39-pipeline | DeepSeek-V4-Flash-0731 | 39 | pipeline | nvlink3 | infiniband_hdr | 38 | 95.36 us | 1,048.7 tok/s | 10,486.7 tok/s | 34 x point_to_point span 2 on nvlink3 (traversals 1.0) = 85.93 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x39-tensor | DeepSeek-V4-Flash-0731 | 39 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x39-hybrid | DeepSeek-V4-Flash-0731 | 39 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x43-pipeline | DeepSeek-V4-Flash-0731 | 43 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x43-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x43-hybrid | DeepSeek-V4-Flash-0731 | 43 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x46-pipeline | DeepSeek-V4-Flash-0731 | 46 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x46-tensor | DeepSeek-V4-Flash-0731 | 46 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x46-hybrid | DeepSeek-V4-Flash-0731 | 46 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x52-pipeline | DeepSeek-V4-Flash-0731 | 52 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x52-tensor | DeepSeek-V4-Flash-0731 | 52 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x52-hybrid | DeepSeek-V4-Flash-0731 | 52 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x55-pipeline | DeepSeek-V4-Flash-0731 | 55 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x55-tensor | DeepSeek-V4-Flash-0731 | 55 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x55-hybrid | DeepSeek-V4-Flash-0731 | 55 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Flash-0731 | 56 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Flash-0731 | 56 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Flash-0731 | 56 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x69-pipeline | DeepSeek-V4-Flash-0731 | 69 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x69-tensor | DeepSeek-V4-Flash-0731 | 69 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x69-hybrid | DeepSeek-V4-Flash-0731 | 69 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x70-pipeline | DeepSeek-V4-Flash-0731 | 70 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x70-tensor | DeepSeek-V4-Flash-0731 | 70 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x70-hybrid | DeepSeek-V4-Flash-0731 | 70 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x73-pipeline | DeepSeek-V4-Flash-0731 | 73 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x73-tensor | DeepSeek-V4-Flash-0731 | 73 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x73-hybrid | DeepSeek-V4-Flash-0731 | 73 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x77-pipeline | DeepSeek-V4-Flash-0731 | 77 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x77-tensor | DeepSeek-V4-Flash-0731 | 77 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x77-hybrid | DeepSeek-V4-Flash-0731 | 77 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x82-pipeline | DeepSeek-V4-Flash-0731 | 82 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x82-tensor | DeepSeek-V4-Flash-0731 | 82 | tensor | nvlink3 | infiniband_hdr | 172 | 862.18 us | 116.0 tok/s | 1,159.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 426.02 us |
| DSV4-Flash/a100_sxm_80gb-x82-hybrid | DeepSeek-V4-Flash-0731 | 82 | hybrid | nvlink3 | infiniband_hdr | 96 | 459.74 us | 217.5 tok/s | 2,175.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| DSV4-Flash/a100_sxm_80gb-x92-pipeline | DeepSeek-V4-Flash-0731 | 92 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x92-tensor | DeepSeek-V4-Flash-0731 | 92 | tensor | nvlink3 | infiniband_hdr | 172 | 862.82 us | 115.9 tok/s | 1,159.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 426.66 us |
| DSV4-Flash/a100_sxm_80gb-x92-hybrid | DeepSeek-V4-Flash-0731 | 92 | hybrid | nvlink3 | infiniband_hdr | 97 | 462.10 us | 216.4 tok/s | 2,164.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.93 us |
| DSV4-Flash/a100_sxm_80gb-x104-pipeline | DeepSeek-V4-Flash-0731 | 104 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x104-tensor | DeepSeek-V4-Flash-0731 | 104 | tensor | nvlink3 | infiniband_hdr | 172 | 863.36 us | 115.8 tok/s | 1,158.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 427.20 us |
| DSV4-Flash/a100_sxm_80gb-x104-hybrid | DeepSeek-V4-Flash-0731 | 104 | hybrid | nvlink3 | infiniband_hdr | 98 | 464.46 us | 215.3 tok/s | 2,153.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.29 us |
| DSV4-Flash/a100_sxm_80gb-x110-pipeline | DeepSeek-V4-Flash-0731 | 110 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x110-tensor | DeepSeek-V4-Flash-0731 | 110 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x110-hybrid | DeepSeek-V4-Flash-0731 | 110 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x111-pipeline | DeepSeek-V4-Flash-0731 | 111 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x111-tensor | DeepSeek-V4-Flash-0731 | 111 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x111-hybrid | DeepSeek-V4-Flash-0731 | 111 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Flash-0731 | 112 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Flash-0731 | 112 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Flash-0731 | 112 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x138-pipeline | DeepSeek-V4-Flash-0731 | 138 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x138-tensor | DeepSeek-V4-Flash-0731 | 138 | tensor | nvlink3 | infiniband_hdr | 172 | 865.17 us | 115.6 tok/s | 1,155.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 429.00 us |
| DSV4-Flash/a100_sxm_80gb-x138-hybrid | DeepSeek-V4-Flash-0731 | 138 | hybrid | nvlink3 | infiniband_hdr | 103 | 476.25 us | 210.0 tok/s | 2,099.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| DSV4-Flash/a100_sxm_80gb-x146-pipeline | DeepSeek-V4-Flash-0731 | 146 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x146-tensor | DeepSeek-V4-Flash-0731 | 146 | tensor | nvlink3 | infiniband_hdr | 172 | 865.42 us | 115.6 tok/s | 1,155.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 429.25 us |
| DSV4-Flash/a100_sxm_80gb-x146-hybrid | DeepSeek-V4-Flash-0731 | 146 | hybrid | nvlink3 | infiniband_hdr | 104 | 478.60 us | 208.9 tok/s | 2,089.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 42.44 us |
| DSV4-Flash/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Flash-0731 | 168 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Flash-0731 | 168 | tensor | nvlink3 | infiniband_hdr | 172 | 865.84 us | 115.5 tok/s | 1,154.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 429.68 us |
| DSV4-Flash/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Flash-0731 | 168 | hybrid | nvlink3 | infiniband_hdr | 106 | 483.32 us | 206.9 tok/s | 2,069.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.15 us |
| DSV4-Flash/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Flash-0731 | 224 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Flash-0731 | 224 | tensor | nvlink3 | infiniband_hdr | 172 | 866.85 us | 115.4 tok/s | 1,153.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 430.68 us |
| DSV4-Flash/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Flash-0731 | 224 | hybrid | nvlink3 | infiniband_hdr | 113 | 499.82 us | 200.1 tok/s | 2,000.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.66 us |
| DSV4-Flash/a100_sxm_80gb-x335-pipeline | DeepSeek-V4-Flash-0731 | 335 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x335-tensor | DeepSeek-V4-Flash-0731 | 335 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.01 us | 82.2 tok/s | 821.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 780.85 us |
| DSV4-Flash/a100_sxm_80gb-x335-hybrid | DeepSeek-V4-Flash-0731 | 335 | hybrid | nvlink3 | infiniband_hdr | 127 | 532.83 us | 187.7 tok/s | 1,876.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| DSV4-Flash/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Flash-0731 | 336 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Flash-0731 | 336 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.01 us | 82.2 tok/s | 821.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 780.85 us |
| DSV4-Flash/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Flash-0731 | 336 | hybrid | nvlink3 | infiniband_hdr | 127 | 532.83 us | 187.7 tok/s | 1,876.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| DSV4-Flash/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Flash-0731 | 448 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Flash-0731 | 448 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.52 us | 82.1 tok/s | 821.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 781.35 us |
| DSV4-Flash/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Flash-0731 | 448 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Flash-0731 | 672 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Flash-0731 | 672 | tensor | nvlink3 | infiniband_hdr | 172 | 1,218.02 us | 82.1 tok/s | 821.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 781.85 us |
| DSV4-Flash/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Flash-0731 | 672 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 1 | wafer | wafer | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | 46,225 | 4,707.9 | 0.102 | 1,539.7 (30,155) | 4,707.9 (46,225) | 3.06x | link_latency |
| DeepSeek-V4-Flash-0731 | 2 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 4,707.9 | 0.102 | 1,539.7 (32,600) | 4,707.9 (46,225) | 3.06x | link_latency |
| DeepSeek-V4-Flash-0731 | 4 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 4,707.9 | 0.102 | 1,539.7 (32,600) | 4,707.9 (46,225) | 3.06x | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 4,707.9 | 0.102 | 1,418.0 (32,600) | 4,707.9 (46,225) | 3.32x | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,406.4 | 0.048 | 1,422.2 (38,305) | 4,406.4 (92,450) | 3.10x | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,190.1 | 0.030 | 1,272.9 (38,305) | 4,190.1 (138,675) | 3.29x | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 3,915.3 | 0.014 | 1,196.5 (45,640) | 3,915.3 (277,350) | 3.27x | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,899.7 | 0.005 | 1,018.7 (120,620) | 2,899.7 (554,700) | 2.85x | link_latency |

## The two ROM floorplans on one die

This probe requests 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. The ROM-plus-MAC floorplan holds the requested weights; the compute-in-ROM floorplan holds only 67.7% and is infeasible at this area. The failed floorplan is retained so the capacity cost of the larger cell remains visible.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 481.6 mm2 | 521.6 mm2 |
| weight capacity | 3.51 GB (100.0%) | 2.38 GB (67.7%) |
| capacity-feasible | yes | **no** |
| compute block | 186.7 mm2 | 146.7 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 0.0 mm2 |
| sustained fp8 compute roof | 9.154e+13 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 4.577e+13 | n/a |
| weight bytes/s the array supplies | 1.019e+14 | 6.900e+13 |
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
| DeepSeek-V4-Flash-0731 | 256 | 574.9 MB | 126.1 mm2 | 22.70 mm2 (18.0%) | 32,278 mm2 | 5,810 mm2 | 36,600 mm2 = 44.9 reticles |

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
| DeepSeek-V4-Flash-0731 | 1 | sram | 28,756.4 | 26,008.0 | 26,008.0 | 1.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 28,756.4 | 26,008.0 | 26,008.0 | 1.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 28,756.4 | 26,008.0 | 26,008.0 | 1.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 37,663.2 | 26,008.0 | 26,353.6 | 1.45x | 1.01x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | sram | 65,349.8 | 26,008.0 | 46,137.9 | 2.51x | 1.77x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | sram | 122,884.3 | 26,008.0 | 79,080.0 | 4.72x | 3.04x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 209,726.5 | 26,008.0 | 129,804.8 | 8.06x | 4.99x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 576,101.4 | 26,066.2 | 296,340.9 | 22.10x | 11.37x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 273,531.4 | 41,334.8 | 41,334.8 | 6.62x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 273,531.4 | 41,334.8 | 41,334.8 | 6.62x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 273,531.4 | 41,334.8 | 41,334.8 | 6.62x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 273,531.4 | 41,334.8 | 41,334.8 | 6.62x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 273,531.4 | 41,334.8 | 55,953.6 | 6.62x | 1.35x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | rom | 273,531.4 | 41,334.8 | 99,243.9 | 6.62x | 2.40x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | rom | 273,531.4 | 41,334.8 | 169,200.5 | 6.62x | 4.09x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 742,330.6 | 41,482.0 | 326,305.9 | 17.90x | 7.87x | link_latency | weight_read | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 9.51x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.44x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.44x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 9.51x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.44x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.44x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 9.51x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.44x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.44x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 37,663.2 | 0.815 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 7.26x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.69x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.10x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.57 | 26,353.6 | 0.285 | link_latency | 0.70x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 1.10x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 65,349.8 | 1.414 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 4.19x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.40x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 0.63x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.13 | 46,137.9 | 0.499 | link_latency | 0.71x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.59 | 2.13 | 55,953.6 | 0.605 | link_latency | 0.86x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 122,884.3 | 1.329 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 2.23x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.21x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 0.34x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.88 | 79,080.0 | 0.855 | weight_read | 0.64x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.59 | 2.88 | 99,243.9 | 1.073 | link_latency | 0.81x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 209,726.5 | 1.512 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 273,531.4 | 0.493 | weight_read | 1.30x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,008.0 | 0.281 | weight_read | 0.12x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 1.00 | 41,334.8 | 0.447 | weight_read | 0.20x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 4.03 | 129,804.8 | 1.404 | weight_read | 0.62x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.59 | 4.03 | 169,200.5 | 1.830 | weight_read | 0.81x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 576,101.4 | 2.077 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 10.55 | 1.00 | 742,330.6 | 1.338 | link_latency | 1.29x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 2.25 | 26,066.2 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 1.59 | 2.25 | 41,482.0 | 0.449 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 8.80 | 296,340.9 | 3.205 | weight_read | 0.51x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.59 | 8.80 | 326,305.9 | 3.530 | kv_read | 0.57x |

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
| DeepSeek-V4-Flash-0731 | 1 | 71 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 71 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 71 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | 114 | 2.25 | 1.015 | 1.183 | 1.17x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4-Flash-0731 | 2 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4-Flash-0731 | 8 | 4 | 3.87 | 2.62 | 1.47x |
| DeepSeek-V4-Flash-0731 | 16 | 4 | 3.99 | 2.91 | 1.37x |
| DeepSeek-V4-Flash-0731 | 32 | 4 | 4.00 | 3.15 | 1.27x |
| DeepSeek-V4-Flash-0731 | 64 | 4 | 4.00 | 3.33 | 1.20x |
| DeepSeek-V4-Flash-0731 | 256 | 4 | 4.00 | 3.55 | 1.13x |
| DeepSeek-V4-Flash-0731 | 1 | 36 | 5.60 | 4.50 | 1.25x |
| DeepSeek-V4-Flash-0731 | 2 | 36 | 5.60 | 4.50 | 1.25x |
| DeepSeek-V4-Flash-0731 | 4 | 36 | 5.60 | 4.50 | 1.25x |
| DeepSeek-V4-Flash-0731 | 8 | 36 | 5.60 | 4.50 | 1.25x |
| DeepSeek-V4-Flash-0731 | 16 | 36 | 5.60 | 4.50 | 1.25x |
| DeepSeek-V4-Flash-0731 | 32 | 36 | 5.60 | 4.50 | 1.25x |
| DeepSeek-V4-Flash-0731 | 64 | 36 | 9.27 | 5.87 | 1.58x |
| DeepSeek-V4-Flash-0731 | 256 | 36 | 24.24 | 10.61 | 2.29x |
| DeepSeek-V4-Flash-0731 | 1 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 2 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 4 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 8 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 16 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 32 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 64 | 37 | 9.09 | 5.84 | 1.56x |
| DeepSeek-V4-Flash-0731 | 256 | 37 | 24.20 | 10.62 | 2.28x |
| DeepSeek-V4-Flash-0731 | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 2 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 4 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 8 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 16 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 32 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 64 | 38 | 8.91 | 5.82 | 1.53x |
| DeepSeek-V4-Flash-0731 | 256 | 38 | 24.13 | 10.62 | 2.27x |
| DeepSeek-V4-Flash-0731 | 1 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 2 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 4 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 8 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 16 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 32 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Flash-0731 | 64 | 39 | 8.74 | 5.79 | 1.51x |
| DeepSeek-V4-Flash-0731 | 256 | 39 | 24.05 | 10.63 | 2.26x |
| DeepSeek-V4-Flash-0731 | 1 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 4 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 8 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 16 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 32 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 64 | 43 | 8.11 | 5.69 | 1.43x |
| DeepSeek-V4-Flash-0731 | 256 | 43 | 23.55 | 10.61 | 2.22x |
| DeepSeek-V4-Flash-0731 | 1 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 4 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 8 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 16 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 32 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 64 | 46 | 7.68 | 5.61 | 1.37x |
| DeepSeek-V4-Flash-0731 | 256 | 46 | 23.06 | 10.59 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 2 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 4 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 8 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 16 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 32 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 64 | 52 | 6.93 | 5.42 | 1.28x |
| DeepSeek-V4-Flash-0731 | 256 | 52 | 21.93 | 10.50 | 2.09x |
| DeepSeek-V4-Flash-0731 | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 4 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 8 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 16 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 32 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 64 | 55 | 6.60 | 5.32 | 1.24x |
| DeepSeek-V4-Flash-0731 | 256 | 55 | 21.34 | 10.43 | 2.05x |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 21.14 | 10.40 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 8 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 16 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 32 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 64 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 256 | 69 | 18.63 | 9.93 | 1.88x |
| DeepSeek-V4-Flash-0731 | 1 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4-Flash-0731 | 8 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4-Flash-0731 | 16 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4-Flash-0731 | 32 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4-Flash-0731 | 64 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4-Flash-0731 | 256 | 70 | 18.45 | 9.89 | 1.87x |
| DeepSeek-V4-Flash-0731 | 1 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 2 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 4 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 8 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 16 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 32 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 64 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 256 | 73 | 17.93 | 9.78 | 1.83x |
| DeepSeek-V4-Flash-0731 | 1 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 2 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 4 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 8 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 16 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 32 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 64 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 256 | 77 | 17.26 | 9.64 | 1.79x |
| DeepSeek-V4-Flash-0731 | 1 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Flash-0731 | 2 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Flash-0731 | 4 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Flash-0731 | 8 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Flash-0731 | 16 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Flash-0731 | 32 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Flash-0731 | 64 | 82 | 5.82 | 5.16 | 1.13x |
| DeepSeek-V4-Flash-0731 | 256 | 82 | 16.47 | 9.48 | 1.74x |
| DeepSeek-V4-Flash-0731 | 1 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 4 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 8 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 16 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 32 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 64 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4-Flash-0731 | 256 | 92 | 15.05 | 9.22 | 1.63x |
| DeepSeek-V4-Flash-0731 | 1 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 4 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 8 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 16 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 32 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 64 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 256 | 104 | 13.61 | 8.97 | 1.52x |
| DeepSeek-V4-Flash-0731 | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 4 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 8 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 16 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 32 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 64 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 256 | 110 | 12.98 | 8.86 | 1.46x |
| DeepSeek-V4-Flash-0731 | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 4 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 8 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 16 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 32 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 64 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 256 | 111 | 12.88 | 8.84 | 1.46x |
| DeepSeek-V4-Flash-0731 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 4 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 8 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 16 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 32 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 64 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 256 | 112 | 12.78 | 8.82 | 1.45x |
| DeepSeek-V4-Flash-0731 | 1 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 2 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 4 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 8 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 16 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 32 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 64 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 256 | 138 | 10.63 | 8.30 | 1.28x |
| DeepSeek-V4-Flash-0731 | 1 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 2 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 4 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 8 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 16 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 32 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 64 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 256 | 146 | 10.10 | 8.12 | 1.24x |
| DeepSeek-V4-Flash-0731 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 2 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 4 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 8 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 16 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 32 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 64 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 256 | 168 | 8.87 | 7.61 | 1.17x |
| DeepSeek-V4-Flash-0731 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 4 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 8 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 16 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 32 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 64 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 256 | 224 | 6.76 | 6.32 | 1.07x |
| DeepSeek-V4-Flash-0731 | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 4 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 8 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 16 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 32 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 64 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 256 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 4 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 8 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 16 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 32 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 64 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 256 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 4 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 8 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 16 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 32 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 64 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 256 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 4 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 8 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 16 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 32 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 64 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 256 | 672 | 5.98 | 5.88 | 1.02x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 1.0% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 5.8% |

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
| DeepSeek-V4-Flash-0731 | 1 | 71 | 17.72% | 33.32 | 2.65 |
| DeepSeek-V4-Flash-0731 | 2 | 71 | 17.72% | 33.32 | 2.65 |
| DeepSeek-V4-Flash-0731 | 4 | 71 | 17.72% | 33.32 | 2.65 |
| DeepSeek-V4-Flash-0731 | 8 | 2 | 0.34% | 1.03 | 2.65 |
| DeepSeek-V4-Flash-0731 | 16 | 2 | 0.34% | 1.03 | 2.65 |
| DeepSeek-V4-Flash-0731 | 32 | 2 | 0.34% | 1.03 | 2.65 |
| DeepSeek-V4-Flash-0731 | 64 | 2 | 0.34% | 1.03 | 2.65 |
| DeepSeek-V4-Flash-0731 | 256 | 2 | 0.76% | 2.31 | 2.65 |

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
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 531.4 | 20,725.2 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 531.4 | 20,725.2 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 531.4 | 20,725.2 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 531.4 | 20,725.2 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 531.4 | 20,725.2 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 6.72% | 325.47 TB/s | 4,841.92 TB/s | 531.4 | 20,725.2 |
| DeepSeek-V4-Flash-0731 | 64 | 3.82% | 13.4 GB | 8.02% | 388.39 TB/s | 4,841.92 TB/s | 331.1 | 21,189.3 |
| DeepSeek-V4-Flash-0731 | 256 | 14.42% | 29.0 GB | 17.37% | 840.99 TB/s | 4,841.92 TB/s | 85.0 | 21,759.5 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | link_latency | 215 |
| gpu | weight_read | 449 |
| rom | compute | 46 |
| rom | infeasible | 940 |
| rom | kv_read | 11 |
| rom | link_latency | 726 |
| rom | weight_read | 549 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 940 |

## Mechanical consistency audit

**PASS** over 62,857 checks.

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

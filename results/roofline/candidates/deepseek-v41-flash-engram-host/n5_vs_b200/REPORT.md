# Area-constrained roofline: n5_vs_b200-deepseek-v41-flash-engram-host

> CANDIDATE MODEL under n5_vs_b200: DeepSeek-V4.1-Flash-engram-host at 200,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 490x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 1 device. On the GPU side the correction reaches 233x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 55 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash-engram-host takes 1 x 46,225 mm2 (46,225 mm2, wafer, KV in HBM) at 5,037 tok/s per user and 109 tok/s per 1,000 mm2, holding 4,818 sessions, against 29 copies of one unified HBM die at the same silicon: 3.9x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash-engram-host on 46,225 mm2 of ROM silicon at 5,037 tok/s per user against 46,400 mm2 of b200_sxm-x29-tensor at 1,292 tok/s: **3.9x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 24,296. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 61.64x to it.** At 554,700 mm2 on DeepSeek-V4.1-Flash-engram-host the pipeline-only GPU delivers 23.12 tok/s and the same silicon running tensor delivers 1,425 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.35x (DeepSeek-V4.1-Flash-engram-host, ROM binding on `link_latency`) to 33.04x (DeepSeek-V4.1-Flash-engram-host, ROM binding on `link_latency`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash-engram-host engages 4.2% of its ROM array at batch 1 and 9.4% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 461 to 26,443 tok/s, and its rate with every slot occupied from 25,374 to 26,443. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 55 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 567 us over NVLink, capping per-user decode at 1,763 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 154.0 us and cap it at 6,494 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 3.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 8 of 8 operating points and an array 0; on tokens per second per square millimetre the same points go 0 to the array and 8 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 0 of 1822 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 29.0x of aggregate throughput (DeepSeek-V4.1-Flash-engram-host). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 13.47x, on DeepSeek-V4.1-Flash-engram-host at batch 256, where the busiest region carries 3.12x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 16 of 16 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 99% of its cooling budget. The companion study at the other node does have power-limited points.


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

### DeepSeek-V4.1-Flash-engram-host at 200,000 tokens

**Recommended: `ROM-N5-native-HBMKV-wafer-tensor-x1`** -- 1 x 46,225 mm2 wafer, 46,225 mm2 total, `tensor`-parallel, KV in HBM, spare silicon to `sram`.

- **5,037.3 tok/s per user** (0.20 ms/token), binding on `link_latency`
- **109.0 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 5,037 tok/s aggregate with every slot full, over 4,818 resident sessions (fill limited by `batch`)
- 2,768 W at 0.060 W/mm2, 549.6 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 29 copies of one unified HBM die -- `b200_sxm-x29-tensor`, 46,400 mm2, area ratio 0.9962 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 46,225 | 46,400 | 0.9962 |
| user tok/s | 5,037.3 | 1,291.8 | 3.90x |
| aggregate tok/s | 5,037 | 1,292 | 3.90x |
| resident sessions | 4,818 | 24,296 | -- |
| J/token | 0.5496 | 9.2458 | 16.8x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 4,818 sessions against one that holds 24,296 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x347-tensor` at 555,200 mm2 and 1,425.0 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,037.3 | 109.0 | 1 | 3.90x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,037.3 | 109.0 | 1 | 3.90x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hybrid-x51` | 41,565 | 2,058.0 | 49.5 | 1 | 1.61x |
| **after -- this report's rule** | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 46,225 | 5,037.3 | 109.0 | 4,818 | 3.90x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-HBMKV-wafer-tensor-x1` **<-- recommended** | 46,225 | 1 | 5,037.3 | 5,037 | 109.0 | 4,818 | `link_latency` | 2,768 | 549.6 | `b200_sxm-x29-tensor` | 3.90x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 132 | densest | `ROM-N5-native-SRAMKV-array-hybrid-x51` | 41,565 | 2,058.0 | 49.5 | 1 |
| array | 132 | fastest | `ROM-N5-native-SRAMKV-array-hybrid-x51` | 41,565 | 2,058.0 | 49.5 | 1 |
| array | 132 | smallest | `ROM-N5-native-SRAMKV-array-hybrid-x51` | 41,565 | 2,058.0 | 49.5 | 1 |
| wafer | 80 | densest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,037.3 | 109.0 | 1 |
| wafer | 80 | fastest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,037.3 | 109.0 | 1 |
| wafer | 80 | smallest | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,037.3 | 109.0 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hybrid-x51` | 41,565 | 2,058.0 | 2,058 | 1 | 2,562 | 1,245.0 | `weight_read` | `b200_sxm-x26-tensor` | 1,276.3 | 21,607 | 8,517.8 | 0.999 | 1.61x | 6.8x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,037.3 | 5,037 | 1 | 2,610 | 518.1 | `link_latency` | `b200_sxm-x29-tensor` | 1,291.8 | 24,296 | 9,245.8 | 0.996 | 3.90x | 17.8x |
| 1 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x55` | 44,825 | 2,058.0 | 14,406 | 30,817 | 3,330 | 231.2 | `weight_read` | `b200_sxm-x28-tensor` | 1,287.0 | 23,400 | 9,003.3 | 1.001 | 1.60x | 38.9x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,037.3 | -- | 1 | -- | 518.1 | -- | -- | -- | -- | -- | 0.970 | 2.45x wafer/array | -- |
| 2 | array | `ROM-N5-native-HBMKV-array-hybrid-x55` | 44,825 | 2,058.0 | 14,406 | 30,817 | 3,330 | 231.2 | `weight_read` | `b200_sxm-x28-tensor` | 1,120.7 | 23,400 | 5,305.2 | 1.001 | 1.84x | 23.0x |
| 2 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 46,225 | 5,037.3 | 10,075 | 4,818 | 2,817 | 279.6 | `link_latency` | `b200_sxm-x29-tensor` | 1,125.8 | 24,296 | 5,441.0 | 0.996 | 4.47x | 19.5x |
| 2 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x55` | 44,825 | 2,058.0 | 14,406 | 30,817 | 3,330 | 231.2 | `weight_read` | `b200_sxm-x28-tensor` | 1,120.7 | 23,400 | 5,305.2 | 1.001 | 1.84x | 23.0x |
| 2 | wafer reference | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 46,225 | 5,037.3 | -- | 4,818 | -- | 279.6 | -- | -- | -- | -- | -- | 0.970 | 2.45x wafer/array | -- |
| 4 | array | `ROM-N5-native-HBMKV-array-hybrid-x55` | 44,825 | 2,058.0 | 14,406 | 30,817 | 3,330 | 231.2 | `weight_read` | `b200_sxm-x28-hybrid` | 948.0 | 23,400 | 3,966.5 | 1.001 | 2.17x | 17.2x |
| 4 | wafer | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 46,225 | 5,019.4 | 20,078 | 4,818 | 2,913 | 145.1 | `link_latency` | `b200_sxm-x29-hybrid` | 958.7 | 24,296 | 4,029.1 | 0.996 | 5.24x | 27.8x |
| 4 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x55` | 44,825 | 2,058.0 | 14,406 | 30,817 | 3,330 | 231.2 | `weight_read` | `b200_sxm-x28-hybrid` | 948.0 | 23,400 | 3,966.5 | 1.001 | 2.17x | 17.2x |
| 4 | wafer reference | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 46,225 | 5,019.4 | -- | 4,818 | -- | 145.1 | -- | -- | -- | -- | -- | 0.970 | 2.44x wafer/array | -- |
| 8 | array | `ROM-N5-native-HBMKV-array-hybrid-x55` | 44,825 | 1,927.3 | 15,419 | 30,817 | 3,337 | 216.4 | `compute` | `b200_sxm-x28-hybrid` | 734.2 | 23,400 | 2,597.9 | 1.001 | 2.62x | 12.0x |
| 8 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,401.1 | 35,209 | 9,637 | 8,561 | 243.1 | `link_latency` | `b200_sxm-x58-tensor` | 767.0 | 50,294 | 3,882.6 | 0.996 | 5.74x | 16.0x |
| 8 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x108-romfill` | 88,020 | 1,468.3 | 20,556 | 48,410 | 9,294 | 452.1 | `weight_read` | `b200_sxm-x55-tensor` | 765.8 | 47,605 | 3,716.2 | 1.000 | 1.92x | 8.2x |
| 8 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,401.1 | -- | 9,637 | -- | 243.1 | -- | -- | -- | -- | -- | 0.952 | 3.00x wafer/array | -- |
| 16 | array | `ROM-N5-native-HBMKV-array-hybrid-x57` | 46,455 | 1,885.8 | 30,174 | 31,937 | 3,748 | 124.2 | `weight_read` | `b200_sxm-x29-hybrid` | 558.6 | 24,296 | 1,833.1 | 1.001 | 3.38x | 14.8x |
| 16 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,395.9 | 70,334 | 9,637 | 8,895 | 126.5 | `link_latency` | `b200_sxm-x58-tensor` | 543.6 | 50,294 | 2,824.3 | 0.996 | 8.09x | 22.3x |
| 16 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x108-romfill` | 88,020 | 1,466.7 | 23,468 | 48,410 | 9,322 | 397.2 | `weight_read` | `b200_sxm-x55-tensor` | 543.3 | 47,605 | 2,704.6 | 1.000 | 2.70x | 6.8x |
| 16 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,395.9 | -- | 9,637 | -- | 126.5 | -- | -- | -- | -- | -- | 0.952 | 3.00x wafer/array | -- |
| 32 | array | `ROM-N5-native-HBMKV-array-hybrid-x68` | 55,420 | 1,732.3 | 55,434 | 38,101 | 5,445 | 98.2 | `weight_read` | `b200_sxm-x35-hybrid` | 395.5 | 29,675 | 1,572.7 | 0.990 | 4.38x | 16.0x |
| 32 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,385.3 | 140,330 | 9,637 | 9,553 | 68.1 | `link_latency` | `b200_sxm-x58-hybrid` | 382.7 | 50,294 | 2,355.9 | 0.996 | 11.46x | 34.6x |
| 32 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x108-romfill` | 88,020 | 1,454.4 | 46,541 | 48,410 | 9,543 | 205.0 | `weight_read` | `b200_sxm-x55-hybrid` | 402.5 | 47,605 | 2,162.3 | 1.000 | 3.61x | 10.5x |
| 32 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,385.3 | -- | 9,637 | -- | 68.1 | -- | -- | -- | -- | -- | 0.952 | 3.02x wafer/array | -- |
| 64 | array | `ROM-N5-native-HBMKV-array-hybrid-x68` | 55,420 | 1,690.4 | 108,184 | 38,101 | 5,946 | 55.0 | `weight_read` | `b200_sxm-x35-hybrid` | 278.1 | 29,675 | 1,200.9 | 0.990 | 6.08x | 21.8x |
| 64 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 4,186.5 | 267,939 | 14,456 | 14,859 | 55.5 | `link_latency` | `b200_sxm-x87-hybrid` | 277.5 | 76,293 | 2,336.4 | 0.996 | 15.09x | 42.1x |
| 64 | array @ wafer area | `ROM-N5-native-HBMKV-array-hybrid-x162-romfill` | 132,030 | 1,422.5 | 91,041 | 54,462 | 13,945 | 153.2 | `weight_read` | `b200_sxm-x83-hybrid` | 273.4 | 72,707 | 2,281.9 | 0.994 | 5.20x | 14.9x |
| 64 | wafer reference | `ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 138,675 | 4,186.5 | -- | 14,456 | -- | 55.5 | -- | -- | -- | -- | -- | 0.952 | 2.94x wafer/array | -- |
| 256 | array | `ROM-N5-native-HBMKV-array-hybrid-x216-romfill` | 176,040 | 1,340.0 | 343,049 | 48,410 | 19,928 | 58.1 | `weight_read` | `b200_sxm-x110-hybrid` | 144.4 | 96,912 | 1,516.1 | 1.000 | 9.28x | 26.1x |
| 256 | wafer | `ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,369.2 | 862,525 | 44,376 | 57,013 | 66.1 | `link_latency` | `b200_sxm-x347-hybrid` | 102.0 | 309,382 | 5,278.0 | 0.999 | 33.04x | 79.8x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-32 | `ROM-N5-native-HBMKV-wafer-tensor-x1` | 46,225 | wafer | HBM | 4,818 |
| 64-256 | `ROM-N5-native-HBMKV-wafer-hybrid-x2` | 92,450 | wafer | HBM | 9,637 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash-engram-host | HBM | rom | 55, 57, 68, 81, 108, 113, 162, 170, 216, 227, 340 |
| DeepSeek-V4.1-Flash-engram-host | HBM | sram | 55, 57, 68, 81, 108, 113, 162, 170, 216, 227, 340 |
| DeepSeek-V4.1-Flash-engram-host | SRAM | rom | 51, 57, 63, 75, 100, 113, 150, 170, 200, 227, 340 |
| DeepSeek-V4.1-Flash-engram-host | SRAM | sram | 51, 57, 63, 75, 100, 113, 150, 170, 200, 227, 340 |

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

- **0 of 1,822 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 99% of its cooling budget, and the busiest wafer-scale ROM design 33%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | small array (1,600-5,000 mm2) | 16 | 0 | 93.3% | 99.4% | 0.621 | 38% |
| gpu | wafer (>=40,000 mm2) | 528 | 0 | 45.2% | 74.8% | 0.468 | 78% |
| rom | wafer (>=40,000 mm2) | 1,278 | 0 | 18.7% | 33.4% | 0.167 | 98% |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 46,225 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-tensor-x1` | 0.518145 | 2,610.1 | link_latency | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-tensor` | 9.245837 | 11,944.2 | link_latency | 17.84x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 46,225 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1` | 0.279590 | 2,816.8 | link_latency | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-tensor` | 5.440987 | 12,250.7 | link_latency | 19.46x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 46,225 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1` | 0.145061 | 2,912.5 | link_latency | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-hybrid` | 4.029102 | 15,450.8 | weight_read | 27.78x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 46,225 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1` | 0.089187 | 3,043.9 | link_latency | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-hybrid` | 2.636974 | 15,675.2 | weight_read | 29.57x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 92,450 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 0.126468 | 8,895.0 | link_latency | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-tensor` | 2.824273 | 24,564.7 | link_latency | 22.33x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 92,450 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 0.068073 | 9,552.6 | link_latency | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-hybrid` | 2.355944 | 28,849.3 | weight_read | 34.61x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 92,450 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2` | 0.046321 | 11,962.0 | link_latency | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-hybrid` | 1.699657 | 30,580.3 | weight_read | 36.69x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 369,800 | `DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 0.048776 | 40,648.7 | link_latency | `DeepSeek-V4.1-Flash-engram-host/b200_sxm-x231-hybrid` | 3.138100 | 98,406.1 | weight_read | 64.34x |

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
| DeepSeek-V4.1-Flash-engram-host | 200,000 | 552 B | 307.5 GB | 4.46 | 0.047 GB | 0.181 GB | 278.7 |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 46,225 | 20,246.1 | wafer-pipeline | 5,037.3 | wafer-tensor | 4.02x | 3,921.2 | pipeline | 1,291.8 | tensor | 3.04x | 5.16x | 3.90x | 0.76x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 92,450 | 22,956.7 | wafer-pipeline | 4,417.2 | wafer-hybrid | 5.20x | 4,422.3 | pipeline | 1,356.9 | tensor | 3.26x | 5.19x | 3.26x | 0.63x |
| DeepSeek-V4.1-Flash-engram-host | 3 | 138,675 | 29,401.5 | wafer-pipeline | 4,320.7 | wafer-hybrid | 6.80x | 4,748.8 | pipeline | 1,382.9 | tensor | 3.43x | 6.19x | 3.12x | 0.50x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 184,900 | 34,200.8 | wafer-pipeline | 4,228.2 | wafer-hybrid | 8.09x | 4,937.4 | pipeline | 1,396.1 | tensor | 3.54x | 6.93x | 3.03x | 0.44x |
| DeepSeek-V4.1-Flash-engram-host | 6 | 277,350 | 40,870.8 | wafer-pipeline | 4,054.5 | wafer-hybrid | 10.08x | 5,144.2 | pipeline | 1,410.1 | tensor | 3.65x | 7.95x | 2.88x | 0.36x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 369,800 | 45,286.1 | wafer-pipeline | 3,894.5 | wafer-hybrid | 11.63x | 5,258.9 | pipeline | 1,417.5 | tensor | 3.71x | 8.61x | 2.75x | 0.32x |
| DeepSeek-V4.1-Flash-engram-host | 12 | 554,700 | 50,770.3 | wafer-pipeline | 3,609.6 | wafer-hybrid | 14.07x | 5,380.2 | pipeline | 1,425.0 | tensor | 3.78x | 9.44x | 2.53x | 0.27x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.27x to 0.76x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash-engram-host | 1 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-tensor-x1 | 46,225 | 5,037.3 | 5,037.3 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-tensor | 46,400 | 1.00x | tensor | 556.05 | 1,291.8 | 1,291.8 | link_latency | 3.90x | 3.90x | 30.62x | 3.90x |
| DeepSeek-V4.1-Flash-engram-host | 1 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hybrid-x51 | 41,565 | 2,058.0 | 2,058.0 | weight_read | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x26-tensor | 41,600 | 1.00x | tensor | 556.05 | 1,276.3 | 1,276.3 | link_latency | 1.61x | 1.61x | 11.72x | 1.61x |
| DeepSeek-V4.1-Flash-engram-host | 2 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 5,037.3 | 10,074.7 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-tensor | 46,400 | 1.00x | tensor | 595.31 | 1,125.8 | 2,251.6 | link_latency | 4.47x | 4.47x | 30.62x | 4.47x |
| DeepSeek-V4.1-Flash-engram-host | 2 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hybrid-x55 | 44,825 | 2,058.0 | 14,405.8 | weight_read | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-tensor | 44,800 | 1.00x | tensor | 595.31 | 1,120.7 | 2,241.4 | link_latency | 1.84x | 6.43x | 12.25x | 1.84x |
| DeepSeek-V4.1-Flash-engram-host | 4 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 5,019.4 | 20,077.8 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 201.09 | 958.7 | 3,834.8 | weight_read | 5.24x | 5.24x | 30.51x | 5.24x |
| DeepSeek-V4.1-Flash-engram-host | 4 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hybrid-x55 | 44,825 | 2,058.0 | 14,405.8 | weight_read | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-hybrid | 44,800 | 1.00x | hybrid | 201.09 | 948.0 | 3,792.2 | weight_read | 2.17x | 3.80x | 12.25x | 2.17x |
| DeepSeek-V4.1-Flash-engram-host | 8 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,401.1 | 35,209.1 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-tensor | 92,800 | 1.00x | tensor | 879.98 | 767.0 | 6,135.8 | link_latency | 5.74x | 5.74x | 42.32x | 5.74x |
| DeepSeek-V4.1-Flash-engram-host | 8 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hybrid-x55 | 44,825 | 1,927.3 | 15,418.8 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-hybrid | 44,800 | 1.00x | hybrid | 204.10 | 734.2 | 5,873.8 | weight_read | 2.62x | 2.62x | 11.47x | 2.62x |
| DeepSeek-V4.1-Flash-engram-host | 16 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,395.9 | 70,333.7 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-tensor | 92,800 | 1.00x | tensor | 1,243.16 | 543.6 | 8,697.7 | link_latency | 8.09x | 8.09x | 42.27x | 8.09x |
| DeepSeek-V4.1-Flash-engram-host | 16 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hybrid-x55 | 44,825 | 1,214.4 | 19,430.1 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-hybrid | 44,800 | 1.00x | hybrid | 210.10 | 550.9 | 8,814.1 | weight_read | 2.20x | 2.20x | 7.23x | 2.20x |
| DeepSeek-V4.1-Flash-engram-host | 32 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,385.3 | 140,330.0 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-hybrid | 92,800 | 1.00x | hybrid | 221.50 | 382.7 | 12,245.3 | weight_read | 11.46x | 11.46x | 42.17x | 11.46x |
| DeepSeek-V4.1-Flash-engram-host | 32 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hybrid-x55 | 44,825 | 698.0 | 22,335.5 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-hybrid | 44,800 | 1.00x | hybrid | 222.12 | 393.5 | 12,591.4 | weight_read | 1.77x | 1.77x | 4.39x | 1.77x |
| DeepSeek-V4.1-Flash-engram-host | 64 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,186.5 | 267,938.7 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x87-hybrid | 139,200 | 1.00x | hybrid | 238.12 | 277.5 | 17,759.1 | weight_read | 15.09x | 15.09x | 54.60x | 15.09x |
| DeepSeek-V4.1-Flash-engram-host | 64 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x55 | 44,825 | 405.6 | 25,958.9 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-hybrid | 44,800 | 1.00x | hybrid | 246.15 | 271.3 | 17,360.7 | weight_read | 1.50x | 1.50x | 3.48x | 1.50x |
| DeepSeek-V4.1-Flash-engram-host | 256 | fastest | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,369.2 | 862,524.7 | link_latency | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 331.54 | 102.0 | 26,103.8 | weight_read | 33.04x | 33.04x | 145.74x | 33.09x |
| DeepSeek-V4.1-Flash-engram-host | 256 | smallest silicon | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x55 | 44,825 | 103.3 | 26,443.0 | compute | DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-hybrid | 44,800 | 1.00x | hybrid | 390.33 | 130.9 | 33,507.3 | weight_read | 0.79x | 0.79x | 1.80x | 0.79x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 8 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 8 | Link us at domain 72 | tok/s at 8 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-host | 3 | 4,800 | 193.82 | 193.82 | 1,010.0 | 1,010.0 |
| DeepSeek-V4.1-Flash-engram-host | 26 | 41,600 | 556.05 | 194.63 | 1,276.3 | 2,369.3 |
| DeepSeek-V4.1-Flash-engram-host | 28 | 44,800 | 556.05 | 194.63 | 1,287.0 | 2,406.2 |
| DeepSeek-V4.1-Flash-engram-host | 29 | 46,400 | 556.05 | 194.64 | 1,291.8 | 2,423.2 |
| DeepSeek-V4.1-Flash-engram-host | 32 | 51,200 | 556.05 | 194.65 | 1,305.0 | 2,469.8 |
| DeepSeek-V4.1-Flash-engram-host | 35 | 56,000 | 558.51 | 194.65 | 1,312.0 | 2,510.4 |
| DeepSeek-V4.1-Flash-engram-host | 38 | 60,800 | 558.51 | 194.66 | 1,321.7 | 2,546.1 |
| DeepSeek-V4.1-Flash-engram-host | 41 | 65,600 | 560.15 | 194.66 | 1,327.3 | 2,577.8 |
| DeepSeek-V4.1-Flash-engram-host | 51 | 81,600 | 561.32 | 194.68 | 1,347.1 | 2,661.8 |
| DeepSeek-V4.1-Flash-engram-host | 52 | 83,200 | 561.32 | 194.68 | 1,348.9 | 2,668.8 |
| DeepSeek-V4.1-Flash-engram-host | 55 | 88,000 | 561.32 | 194.68 | 1,353.9 | 2,688.5 |
| DeepSeek-V4.1-Flash-engram-host | 56 | 89,600 | 561.32 | 194.68 | 1,355.5 | 2,694.7 |
| DeepSeek-V4.1-Flash-engram-host | 58 | 92,800 | 562.20 | 194.68 | 1,356.9 | 2,706.6 |
| DeepSeek-V4.1-Flash-engram-host | 76 | 121,600 | 563.43 | 544.07 | 1,375.1 | 1,412.7 |
| DeepSeek-V4.1-Flash-engram-host | 83 | 132,800 | 563.87 | 544.07 | 1,380.0 | 1,418.8 |
| DeepSeek-V4.1-Flash-engram-host | 87 | 139,200 | 563.87 | 544.07 | 1,382.9 | 1,421.8 |
| DeepSeek-V4.1-Flash-engram-host | 92 | 147,200 | 564.25 | 544.07 | 1,385.5 | 1,425.4 |
| DeepSeek-V4.1-Flash-engram-host | 102 | 163,200 | 564.56 | 544.07 | 1,390.6 | 1,431.4 |
| DeepSeek-V4.1-Flash-engram-host | 110 | 176,000 | 564.83 | 544.07 | 1,394.0 | 1,435.5 |
| DeepSeek-V4.1-Flash-engram-host | 116 | 185,600 | 565.06 | 544.07 | 1,396.1 | 1,438.3 |
| DeepSeek-V4.1-Flash-engram-host | 173 | 276,800 | 566.11 | 552.26 | 1,410.1 | 1,438.2 |
| DeepSeek-V4.1-Flash-engram-host | 231 | 369,600 | 566.65 | 556.36 | 1,417.5 | 1,438.5 |
| DeepSeek-V4.1-Flash-engram-host | 347 | 555,200 | 567.22 | 558.81 | 1,425.0 | 1,442.3 |

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
| DeepSeek-V4.1-Flash-engram-host | 3 | 4,800 | 421.7 | 1,010.0 | — | tensor | 193.82 | 19.6% | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 26 | 41,600 | 175.6 | 1,276.3 | 925.3 | tensor | 556.05 | 71.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 28 | 44,800 | 168.0 | 1,287.0 | 948.0 | tensor | 556.05 | 71.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 29 | 46,400 | 164.5 | 1,291.8 | 958.7 | tensor | 556.05 | 71.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 32 | 51,200 | 154.9 | 1,305.0 | 988.2 | tensor | 556.05 | 72.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 35 | 56,000 | 146.3 | 1,312.0 | 846.3 | tensor | 558.51 | 73.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 38 | 60,800 | 138.8 | 1,321.7 | 866.8 | tensor | 558.51 | 73.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 41 | 65,600 | 132.0 | 1,327.3 | 760.5 | tensor | 560.15 | 74.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 51 | 81,600 | 113.9 | 1,347.1 | 707.0 | tensor | 561.32 | 75.6% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 52 | 83,200 | 112.4 | 1,348.9 | 710.4 | tensor | 561.32 | 75.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 55 | 88,000 | 108.0 | 1,353.9 | 720.3 | tensor | 561.32 | 76.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 56 | 89,600 | 106.6 | 1,355.5 | 723.4 | tensor | 561.32 | 76.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 58 | 92,800 | 104.0 | 1,356.9 | 650.2 | tensor | 562.20 | 76.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 76 | 121,600 | 85.1 | 1,375.1 | 567.5 | tensor | 563.43 | 77.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 83 | 132,800 | 79.5 | 1,380.0 | 530.6 | tensor | 563.87 | 77.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 87 | 139,200 | 76.7 | 1,382.9 | 535.4 | tensor | 563.87 | 78.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 92 | 147,200 | 73.4 | 1,385.5 | 500.4 | tensor | 564.25 | 78.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 102 | 163,200 | 67.6 | 1,390.6 | 474.0 | tensor | 564.56 | 78.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 110 | 176,000 | 63.6 | 1,394.0 | 448.8 | tensor | 564.83 | 78.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 116 | 185,600 | 60.8 | 1,396.1 | 425.0 | tensor | 565.06 | 78.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 173 | 276,800 | 43.3 | 1,410.1 | 314.7 | tensor | 566.11 | 79.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 231 | 369,600 | 33.6 | 1,417.5 | 249.9 | tensor | 566.65 | 80.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 347 | 555,200 | 23.1 | 1,425.0 | 173.4 | tensor | 567.22 | 80.8% | link_latency |

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
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-pipeline-x51 | DeepSeek-V4.1-Flash-engram-host | 51 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4.1-Flash-engram-host | 1 | pipeline | on_wafer_n5 | inter_wafer | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-tensor-x51 | DeepSeek-V4.1-Flash-engram-host | 51 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4.1-Flash-engram-host | 1 | tensor | on_wafer_n5 | inter_wafer | 80 | 154.00 us | 649.4 tok/s | 6,493.5 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-array-hybrid-x51 | DeepSeek-V4.1-Flash-engram-host | 51 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x55 | DeepSeek-V4.1-Flash-engram-host | 55 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4.1-Flash-engram-host | 1 | pipeline | on_wafer_n5 | inter_wafer | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-tensor-x55 | DeepSeek-V4.1-Flash-engram-host | 55 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4.1-Flash-engram-host | 1 | tensor | on_wafer_n5 | inter_wafer | 80 | 154.00 us | 649.4 tok/s | 6,493.5 tok/s | 80 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 154.00 us |
| DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-hybrid-x55 | DeepSeek-V4.1-Flash-engram-host | 55 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x3-pipeline | DeepSeek-V4.1-Flash-engram-host | 3 | pipeline | nvlink5 | infiniband_ndr | 2 | 2.42 us | 41,275.3 tok/s | 412,753.2 tok/s | 2 x point_to_point span 2 on nvlink5 (traversals 1.0) = 2.42 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x3-tensor | DeepSeek-V4.1-Flash-engram-host | 3 | tensor | nvlink5 | infiniband_ndr | 80 | 193.82 us | 515.9 tok/s | 5,159.4 tok/s | 80 x all_reduce span 3 on nvlink5 (traversals 2.0) = 193.82 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x26-pipeline | DeepSeek-V4.1-Flash-engram-host | 26 | pipeline | nvlink5 | infiniband_ndr | 25 | 33.35 us | 2,998.1 tok/s | 29,980.8 tok/s | 22 x point_to_point span 2 on nvlink5 (traversals 1.0) = 26.65 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x26-tensor | DeepSeek-V4.1-Flash-engram-host | 26 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x26-hybrid | DeepSeek-V4.1-Flash-engram-host | 26 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-pipeline | DeepSeek-V4.1-Flash-engram-host | 28 | pipeline | nvlink5 | infiniband_ndr | 27 | 35.78 us | 2,795.1 tok/s | 27,950.6 tok/s | 24 x point_to_point span 2 on nvlink5 (traversals 1.0) = 29.07 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-tensor | DeepSeek-V4.1-Flash-engram-host | 28 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x28-hybrid | DeepSeek-V4.1-Flash-engram-host | 28 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-pipeline | DeepSeek-V4.1-Flash-engram-host | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.99 us | 2,703.5 tok/s | 27,035.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.28 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-tensor | DeepSeek-V4.1-Flash-engram-host | 29 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x29-hybrid | DeepSeek-V4.1-Flash-engram-host | 29 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x32-pipeline | DeepSeek-V4.1-Flash-engram-host | 32 | pipeline | nvlink5 | infiniband_ndr | 31 | 40.62 us | 2,461.7 tok/s | 24,616.6 tok/s | 28 x point_to_point span 2 on nvlink5 (traversals 1.0) = 33.92 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x32-tensor | DeepSeek-V4.1-Flash-engram-host | 32 | tensor | nvlink5 | infiniband_ndr | 160 | 556.05 us | 179.8 tok/s | 1,798.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 361.66 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x32-hybrid | DeepSeek-V4.1-Flash-engram-host | 32 | hybrid | nvlink5 | infiniband_ndr | 83 | 201.09 us | 497.3 tok/s | 4,972.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.70 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x35-pipeline | DeepSeek-V4.1-Flash-engram-host | 35 | pipeline | nvlink5 | infiniband_ndr | 34 | 45.28 us | 2,208.5 tok/s | 22,084.5 tok/s | 30 x point_to_point span 2 on nvlink5 (traversals 1.0) = 36.34 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x35-tensor | DeepSeek-V4.1-Flash-engram-host | 35 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x35-hybrid | DeepSeek-V4.1-Flash-engram-host | 35 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x38-pipeline | DeepSeek-V4.1-Flash-engram-host | 38 | pipeline | nvlink5 | infiniband_ndr | 37 | 48.91 us | 2,044.4 tok/s | 20,443.8 tok/s | 33 x point_to_point span 2 on nvlink5 (traversals 1.0) = 39.98 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x38-tensor | DeepSeek-V4.1-Flash-engram-host | 38 | tensor | nvlink5 | infiniband_ndr | 160 | 558.51 us | 179.0 tok/s | 1,790.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 364.12 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x38-hybrid | DeepSeek-V4.1-Flash-engram-host | 38 | hybrid | nvlink5 | infiniband_ndr | 84 | 203.33 us | 491.8 tok/s | 4,918.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x41-pipeline | DeepSeek-V4.1-Flash-engram-host | 41 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x41-tensor | DeepSeek-V4.1-Flash-engram-host | 41 | tensor | nvlink5 | infiniband_ndr | 160 | 560.15 us | 178.5 tok/s | 1,785.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 365.76 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x41-hybrid | DeepSeek-V4.1-Flash-engram-host | 41 | hybrid | nvlink5 | infiniband_ndr | 85 | 205.56 us | 486.5 tok/s | 4,864.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 11.17 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x51-pipeline | DeepSeek-V4.1-Flash-engram-host | 51 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x51-tensor | DeepSeek-V4.1-Flash-engram-host | 51 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x51-hybrid | DeepSeek-V4.1-Flash-engram-host | 51 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x52-pipeline | DeepSeek-V4.1-Flash-engram-host | 52 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x52-tensor | DeepSeek-V4.1-Flash-engram-host | 52 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x52-hybrid | DeepSeek-V4.1-Flash-engram-host | 52 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x55-pipeline | DeepSeek-V4.1-Flash-engram-host | 55 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x55-tensor | DeepSeek-V4.1-Flash-engram-host | 55 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x55-hybrid | DeepSeek-V4.1-Flash-engram-host | 55 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x56-pipeline | DeepSeek-V4.1-Flash-engram-host | 56 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x56-tensor | DeepSeek-V4.1-Flash-engram-host | 56 | tensor | nvlink5 | infiniband_ndr | 160 | 561.32 us | 178.2 tok/s | 1,781.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 366.93 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x56-hybrid | DeepSeek-V4.1-Flash-engram-host | 56 | hybrid | nvlink5 | infiniband_ndr | 86 | 207.80 us | 481.2 tok/s | 4,812.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.41 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-pipeline | DeepSeek-V4.1-Flash-engram-host | 58 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-tensor | DeepSeek-V4.1-Flash-engram-host | 58 | tensor | nvlink5 | infiniband_ndr | 160 | 562.20 us | 177.9 tok/s | 1,778.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 367.81 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x58-hybrid | DeepSeek-V4.1-Flash-engram-host | 58 | hybrid | nvlink5 | infiniband_ndr | 87 | 210.03 us | 476.1 tok/s | 4,761.2 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.64 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x76-pipeline | DeepSeek-V4.1-Flash-engram-host | 76 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x76-tensor | DeepSeek-V4.1-Flash-engram-host | 76 | tensor | nvlink5 | infiniband_ndr | 160 | 563.43 us | 177.5 tok/s | 1,774.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 369.04 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x76-hybrid | DeepSeek-V4.1-Flash-engram-host | 76 | hybrid | nvlink5 | infiniband_ndr | 89 | 214.50 us | 466.2 tok/s | 4,661.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 20.11 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x83-pipeline | DeepSeek-V4.1-Flash-engram-host | 83 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x83-tensor | DeepSeek-V4.1-Flash-engram-host | 83 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x83-hybrid | DeepSeek-V4.1-Flash-engram-host | 83 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x87-pipeline | DeepSeek-V4.1-Flash-engram-host | 87 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x87-tensor | DeepSeek-V4.1-Flash-engram-host | 87 | tensor | nvlink5 | infiniband_ndr | 160 | 563.87 us | 177.3 tok/s | 1,773.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 369.48 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x87-hybrid | DeepSeek-V4.1-Flash-engram-host | 87 | hybrid | nvlink5 | infiniband_ndr | 90 | 216.74 us | 461.4 tok/s | 4,613.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 22.35 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x92-pipeline | DeepSeek-V4.1-Flash-engram-host | 92 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x92-tensor | DeepSeek-V4.1-Flash-engram-host | 92 | tensor | nvlink5 | infiniband_ndr | 160 | 564.25 us | 177.2 tok/s | 1,772.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 369.86 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x92-hybrid | DeepSeek-V4.1-Flash-engram-host | 92 | hybrid | nvlink5 | infiniband_ndr | 91 | 218.97 us | 456.7 tok/s | 4,566.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 24.58 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x102-pipeline | DeepSeek-V4.1-Flash-engram-host | 102 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x102-tensor | DeepSeek-V4.1-Flash-engram-host | 102 | tensor | nvlink5 | infiniband_ndr | 160 | 564.56 us | 177.1 tok/s | 1,771.3 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 13 on infiniband_ndr (traversals 2.0) = 370.17 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x102-hybrid | DeepSeek-V4.1-Flash-engram-host | 102 | hybrid | nvlink5 | infiniband_ndr | 92 | 221.21 us | 452.1 tok/s | 4,520.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 12 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 26.82 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x110-pipeline | DeepSeek-V4.1-Flash-engram-host | 110 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x110-tensor | DeepSeek-V4.1-Flash-engram-host | 110 | tensor | nvlink5 | infiniband_ndr | 160 | 564.83 us | 177.0 tok/s | 1,770.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 14 on infiniband_ndr (traversals 2.0) = 370.44 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x110-hybrid | DeepSeek-V4.1-Flash-engram-host | 110 | hybrid | nvlink5 | infiniband_ndr | 93 | 223.44 us | 447.5 tok/s | 4,475.4 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 13 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 29.05 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x116-pipeline | DeepSeek-V4.1-Flash-engram-host | 116 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x116-tensor | DeepSeek-V4.1-Flash-engram-host | 116 | tensor | nvlink5 | infiniband_ndr | 160 | 565.06 us | 177.0 tok/s | 1,769.7 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 370.68 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x116-hybrid | DeepSeek-V4.1-Flash-engram-host | 116 | hybrid | nvlink5 | infiniband_ndr | 94 | 225.68 us | 443.1 tok/s | 4,431.1 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 31.29 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-pipeline | DeepSeek-V4.1-Flash-engram-host | 173 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-tensor | DeepSeek-V4.1-Flash-engram-host | 173 | tensor | nvlink5 | infiniband_ndr | 160 | 566.11 us | 176.6 tok/s | 1,766.5 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 371.72 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x173-hybrid | DeepSeek-V4.1-Flash-engram-host | 173 | hybrid | nvlink5 | infiniband_ndr | 101 | 241.32 us | 414.4 tok/s | 4,143.9 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.93 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x231-pipeline | DeepSeek-V4.1-Flash-engram-host | 231 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x231-tensor | DeepSeek-V4.1-Flash-engram-host | 231 | tensor | nvlink5 | infiniband_ndr | 160 | 566.65 us | 176.5 tok/s | 1,764.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 372.26 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x231-hybrid | DeepSeek-V4.1-Flash-engram-host | 231 | hybrid | nvlink5 | infiniband_ndr | 108 | 256.96 us | 389.2 tok/s | 3,891.6 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 62.57 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-pipeline | DeepSeek-V4.1-Flash-engram-host | 347 | pipeline | nvlink5 | infiniband_ndr | 39 | 51.34 us | 1,947.9 tok/s | 19,479.0 tok/s | 35 x point_to_point span 2 on nvlink5 (traversals 1.0) = 42.40 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.94 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-tensor | DeepSeek-V4.1-Flash-engram-host | 347 | tensor | nvlink5 | infiniband_ndr | 160 | 567.22 us | 176.3 tok/s | 1,763.0 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 80 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 372.83 us |
| DeepSeek-V4.1-Flash-engram-host/b200_sxm-x347-hybrid | DeepSeek-V4.1-Flash-engram-host | 347 | hybrid | nvlink5 | infiniband_ndr | 119 | 281.55 us | 355.2 tok/s | 3,551.8 tok/s | 80 x all_reduce span 8 on nvlink5 (traversals 2.0) = 194.39 us; 39 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 87.16 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4.1-Flash-engram-host | 1 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-tensor-x1 | 46,225 | 5,037.3 | 0.109 | 2,058.0 (41,565) | 5,037.3 (46,225) | 2.45x | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 2 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 5,037.3 | 0.109 | 2,058.0 (44,825) | 5,037.3 (46,225) | 2.45x | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 4 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 5,019.4 | 0.109 | 2,058.0 (44,825) | 5,019.4 (46,225) | 2.44x | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 8 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 4,266.2 | 0.092 | 1,927.3 (44,825) | 4,266.2 (46,225) | 2.21x | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 16 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,395.9 | 0.048 | 1,885.8 (46,455) | 4,395.9 (92,450) | 2.33x | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 32 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,385.3 | 0.047 | 1,732.3 (55,420) | 4,385.3 (92,450) | 2.53x | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 64 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,035.0 | 0.044 | 1,690.4 (55,420) | 4,035.0 (92,450) | 2.39x | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 256 | wafer | wafer | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,255.3 | 0.009 | 1,301.4 (88,020) | 3,255.3 (369,800) | 2.50x | link_latency |

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
| DeepSeek-V4.1-Flash-engram-host | 384 | 752.0 MB | 128.3 mm2 | 23.09 mm2 (18.0%) | 49,261 mm2 | 8,867 mm2 | 52,460 mm2 = 64.4 reticles |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | sram | 28,795.8 | 26,024.2 | 26,024.2 | 1.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 2 | sram | 28,795.8 | 26,024.2 | 26,024.2 | 1.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 4 | sram | 28,795.8 | 26,024.2 | 26,024.2 | 1.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 8 | sram | 34,129.8 | 26,024.2 | 28,692.8 | 1.31x | 1.10x | link_latency | weight_read | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 16 | sram | 64,990.9 | 26,024.2 | 49,667.5 | 2.50x | 1.91x | link_latency | weight_read | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 32 | sram | 129,693.7 | 26,024.2 | 87,703.2 | 4.98x | 3.37x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 64 | sram | 258,242.7 | 26,024.2 | 145,985.1 | 9.92x | 5.61x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 256 | sram | 754,874.0 | 26,073.5 | 351,156.8 | 28.95x | 13.47x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 1 | rom | 206,905.6 | 43,395.4 | 43,395.4 | 4.77x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 2 | rom | 206,905.6 | 43,395.4 | 43,395.4 | 4.77x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 4 | rom | 206,905.6 | 43,395.4 | 43,395.4 | 4.77x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 8 | rom | 206,905.6 | 43,395.4 | 43,395.4 | 4.77x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 16 | rom | 206,905.6 | 43,395.4 | 52,144.2 | 4.77x | 1.20x | weight_read | weight_read | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 32 | rom | 206,905.6 | 43,395.4 | 92,663.4 | 4.77x | 2.14x | weight_read | weight_read | link_latency |
| DeepSeek-V4.1-Flash-engram-host | 64 | rom | 267,938.7 | 43,395.4 | 155,489.3 | 6.17x | 3.58x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-host | 256 | rom | 862,524.7 | 43,583.1 | 379,974.0 | 19.79x | 8.72x | link_latency | weight_read | weight_read |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 1 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.96 | 1.00 | 206,905.6 | 0.373 | weight_read | 7.19x |
| DeepSeek-V4.1-Flash-engram-host | 1 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,024.2 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4.1-Flash-engram-host | 1 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x180-perstream-romfill | 146,700 | 1.69 | 1.00 | 43,395.4 | 0.296 | weight_read | 1.51x |
| DeepSeek-V4.1-Flash-engram-host | 1 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,024.2 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4.1-Flash-engram-host | 1 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x180-perregion-romfill | 146,700 | 1.69 | 1.00 | 43,395.4 | 0.296 | weight_read | 1.51x |
| DeepSeek-V4.1-Flash-engram-host | 2 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 2 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.96 | 1.00 | 206,905.6 | 0.373 | weight_read | 7.19x |
| DeepSeek-V4.1-Flash-engram-host | 2 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,024.2 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4.1-Flash-engram-host | 2 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x180-perstream-romfill | 146,700 | 1.69 | 1.00 | 43,395.4 | 0.296 | weight_read | 1.51x |
| DeepSeek-V4.1-Flash-engram-host | 2 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,024.2 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4.1-Flash-engram-host | 2 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x180-perregion-romfill | 146,700 | 1.69 | 1.00 | 43,395.4 | 0.296 | weight_read | 1.51x |
| DeepSeek-V4.1-Flash-engram-host | 4 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 28,795.8 | 0.623 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 4 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.96 | 1.00 | 206,905.6 | 0.373 | weight_read | 7.19x |
| DeepSeek-V4.1-Flash-engram-host | 4 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,024.2 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4.1-Flash-engram-host | 4 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x180-perstream-romfill | 146,700 | 1.69 | 1.00 | 43,395.4 | 0.296 | weight_read | 1.51x |
| DeepSeek-V4.1-Flash-engram-host | 4 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perregion | 92,450 | 1.00 | 1.00 | 26,024.2 | 0.281 | weight_read | 0.90x |
| DeepSeek-V4.1-Flash-engram-host | 4 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x180-perregion-romfill | 146,700 | 1.69 | 1.00 | 43,395.4 | 0.296 | weight_read | 1.51x |
| DeepSeek-V4.1-Flash-engram-host | 8 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 34,129.8 | 0.738 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 8 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.96 | 1.00 | 206,905.6 | 0.373 | weight_read | 6.06x |
| DeepSeek-V4.1-Flash-engram-host | 8 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,024.2 | 0.281 | weight_read | 0.76x |
| DeepSeek-V4.1-Flash-engram-host | 8 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x180-perstream-romfill | 146,700 | 1.69 | 1.00 | 43,395.4 | 0.296 | weight_read | 1.27x |
| DeepSeek-V4.1-Flash-engram-host | 8 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.43 | 28,692.8 | 0.310 | link_latency | 0.84x |
| DeepSeek-V4.1-Flash-engram-host | 8 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x180-perregion-romfill | 146,700 | 1.69 | 1.00 | 43,395.4 | 0.296 | weight_read | 1.27x |
| DeepSeek-V4.1-Flash-engram-host | 16 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 64,990.9 | 0.703 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 16 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.96 | 1.00 | 206,905.6 | 0.373 | weight_read | 3.18x |
| DeepSeek-V4.1-Flash-engram-host | 16 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,024.2 | 0.281 | weight_read | 0.40x |
| DeepSeek-V4.1-Flash-engram-host | 16 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x180-perstream-romfill | 146,700 | 1.69 | 1.00 | 43,395.4 | 0.296 | weight_read | 0.67x |
| DeepSeek-V4.1-Flash-engram-host | 16 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.99 | 49,667.5 | 0.537 | link_latency | 0.76x |
| DeepSeek-V4.1-Flash-engram-host | 16 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.11 | 1.99 | 52,144.2 | 0.564 | link_latency | 0.80x |
| DeepSeek-V4.1-Flash-engram-host | 32 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 129,693.7 | 1.403 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 32 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 7.96 | 1.00 | 206,905.6 | 0.373 | weight_read | 1.60x |
| DeepSeek-V4.1-Flash-engram-host | 32 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,024.2 | 0.281 | weight_read | 0.20x |
| DeepSeek-V4.1-Flash-engram-host | 32 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x180-perstream-romfill | 146,700 | 1.69 | 1.00 | 43,395.4 | 0.296 | weight_read | 0.33x |
| DeepSeek-V4.1-Flash-engram-host | 32 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.54 | 87,703.2 | 0.949 | weight_read | 0.68x |
| DeepSeek-V4.1-Flash-engram-host | 32 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.11 | 2.54 | 92,663.4 | 1.002 | link_latency | 0.71x |
| DeepSeek-V4.1-Flash-engram-host | 64 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 258,242.7 | 2.793 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 64 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 1.98 | 1.00 | 267,938.7 | 1.932 | link_latency | 1.04x |
| DeepSeek-V4.1-Flash-engram-host | 64 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 1.00 | 26,024.2 | 0.281 | weight_read | 0.10x |
| DeepSeek-V4.1-Flash-engram-host | 64 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x180-perstream-romfill | 146,700 | 1.69 | 1.00 | 43,395.4 | 0.296 | weight_read | 0.17x |
| DeepSeek-V4.1-Flash-engram-host | 64 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 3.49 | 145,985.1 | 1.579 | weight_read | 0.57x |
| DeepSeek-V4.1-Flash-engram-host | 64 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.11 | 3.49 | 155,489.3 | 1.682 | weight_read | 0.60x |
| DeepSeek-V4.1-Flash-engram-host | 256 | batched | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 754,874.0 | 5.443 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 256 | batched | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 7.96 | 1.00 | 862,524.7 | 1.555 | link_latency | 1.14x |
| DeepSeek-V4.1-Flash-engram-host | 256 | per_stream | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 2.25 | 26,073.5 | 0.282 | weight_read | 0.03x |
| DeepSeek-V4.1-Flash-engram-host | 256 | per_stream | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-array-pipeline-x180-perstream-romfill | 146,700 | 1.69 | 1.42 | 43,583.1 | 0.297 | weight_read | 0.06x |
| DeepSeek-V4.1-Flash-engram-host | 256 | per_region | sram | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 7.20 | 351,156.8 | 3.798 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash-engram-host | 256 | per_region | rom | DeepSeek-V4.1-Flash-engram-host/ROM-N5-native-HBMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 1.11 | 7.20 | 379,974.0 | 4.110 | weight_read | 0.50x |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 101 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 101 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 101 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 109 | 2.35 | 1.011 | 1.144 | 1.13x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-host | 1 | 3 | 2.74 | 2.02 | 1.35x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 3 | 2.74 | 2.02 | 1.35x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 3 | 2.88 | 2.11 | 1.37x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 3 | 3.00 | 2.31 | 1.30x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 3 | 3.00 | 2.47 | 1.22x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 3 | 3.00 | 2.60 | 1.16x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 3 | 3.00 | 2.69 | 1.11x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 3 | 3.00 | 2.80 | 1.07x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 26 | 6.53 | 4.59 | 1.42x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 26 | 11.34 | 6.19 | 1.83x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 26 | 23.01 | 10.32 | 2.23x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 28 | 6.17 | 4.53 | 1.36x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 28 | 10.91 | 6.13 | 1.78x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 28 | 23.70 | 10.45 | 2.27x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 29 | 6.01 | 4.50 | 1.34x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 29 | 10.70 | 6.10 | 1.75x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 29 | 23.96 | 10.50 | 2.28x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 32 | 5.55 | 4.39 | 1.27x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 32 | 10.07 | 6.00 | 1.68x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 32 | 24.44 | 10.62 | 2.30x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 35 | 5.59 | 4.47 | 1.25x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 35 | 5.59 | 4.47 | 1.25x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 35 | 5.59 | 4.47 | 1.25x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 35 | 5.59 | 4.47 | 1.25x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 35 | 5.59 | 4.47 | 1.25x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 35 | 5.59 | 4.47 | 1.25x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 35 | 9.48 | 5.91 | 1.61x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 35 | 24.57 | 10.69 | 2.30x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 38 | 8.93 | 5.82 | 1.53x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 38 | 24.44 | 10.72 | 2.28x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 41 | 5.65 | 4.61 | 1.22x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 41 | 8.43 | 5.75 | 1.47x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 41 | 24.13 | 10.72 | 2.25x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 51 | 5.71 | 4.80 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 51 | 5.71 | 4.80 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 51 | 5.71 | 4.80 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 51 | 5.71 | 4.80 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 51 | 5.71 | 4.80 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 51 | 5.71 | 4.80 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 51 | 7.05 | 5.46 | 1.29x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 51 | 22.39 | 10.60 | 2.11x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 52 | 6.93 | 5.42 | 1.28x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 52 | 22.19 | 10.58 | 2.10x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 55 | 6.61 | 5.32 | 1.24x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 55 | 21.57 | 10.50 | 2.05x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 56 | 21.37 | 10.48 | 2.04x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 58 | 6.30 | 5.21 | 1.21x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 58 | 20.96 | 10.41 | 2.01x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 76 | 17.56 | 9.72 | 1.81x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 83 | 5.82 | 5.17 | 1.13x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 83 | 16.44 | 9.49 | 1.73x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 87 | 15.84 | 9.37 | 1.69x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 92 | 5.84 | 5.23 | 1.12x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 92 | 15.15 | 9.25 | 1.64x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 102 | 5.85 | 5.30 | 1.11x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 102 | 5.85 | 5.30 | 1.11x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 102 | 5.85 | 5.30 | 1.11x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 102 | 5.85 | 5.30 | 1.11x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 102 | 5.85 | 5.30 | 1.11x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 102 | 5.85 | 5.30 | 1.11x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 102 | 5.85 | 5.30 | 1.11x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 102 | 13.91 | 9.04 | 1.54x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 110 | 13.04 | 8.88 | 1.47x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 116 | 12.45 | 8.77 | 1.42x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 173 | 8.65 | 7.49 | 1.15x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 231 | 6.56 | 6.17 | 1.06x |
| DeepSeek-V4.1-Flash-engram-host | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4.1-Flash-engram-host | 2 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4.1-Flash-engram-host | 4 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4.1-Flash-engram-host | 8 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4.1-Flash-engram-host | 16 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4.1-Flash-engram-host | 32 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4.1-Flash-engram-host | 64 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4.1-Flash-engram-host | 256 | 347 | 5.96 | 5.77 | 1.03x |

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
| gpu | DeepSeek-V4.1-Flash-engram-host | 1 | 10.05 | 1.4% |
| rom | DeepSeek-V4.1-Flash-engram-host | 1 | 10.05 | 5.1% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash-engram-host | sram | interleaved | 128 B | 1.77x |
| DeepSeek-V4.1-Flash-engram-host | hbm | interleaved | 32 B | 1.34x |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 101 | 21.03% | 90.04 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 2 | 101 | 21.03% | 90.04 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 4 | 101 | 21.03% | 90.04 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 8 | 2 | 0.70% | 3.36 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 16 | 2 | 0.70% | 3.36 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 32 | 2 | 0.70% | 3.36 | 4.24 |
| DeepSeek-V4.1-Flash-engram-host | 64 | 2 | 0.70% | 3.36 | 4.24 |

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
| DeepSeek-V4.1-Flash-engram-host | 1 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 461.3 | 25,373.6 |
| DeepSeek-V4.1-Flash-engram-host | 2 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 461.3 | 25,373.6 |
| DeepSeek-V4.1-Flash-engram-host | 4 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 461.3 | 25,373.6 |
| DeepSeek-V4.1-Flash-engram-host | 8 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 461.3 | 25,373.6 |
| DeepSeek-V4.1-Flash-engram-host | 16 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 461.3 | 25,373.6 |
| DeepSeek-V4.1-Flash-engram-host | 32 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 461.3 | 25,373.6 |
| DeepSeek-V4.1-Flash-engram-host | 64 | 1.82% | 13.8 GB | 4.48% | 399.44 TB/s | 8,922.81 TB/s | 405.6 | 25,958.9 |
| DeepSeek-V4.1-Flash-engram-host | 256 | 7.07% | 28.9 GB | 9.41% | 839.50 TB/s | 8,922.81 TB/s | 103.3 | 26,443.0 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | link_latency | 176 |
| gpu | weight_read | 368 |
| rom | compute | 37 |
| rom | infeasible | 946 |
| rom | link_latency | 526 |
| rom | weight_read | 715 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 946 |

## Mechanical consistency audit

**PASS** over 58,045 checks.

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

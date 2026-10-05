# Area-constrained roofline: n6_vs_a100-mimo-v26-pro-8k

> CANDIDATE MODEL under n6_vs_a100: MiMo-V2.6-Pro at 8,192 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 47x (ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream, 227 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 2 devices. On the GPU side the correction reaches 36x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 112 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Pro takes 3 x 46,225 mm2 (138,675 mm2, wafer, KV in SRAM) at 3,567 tok/s per user and 26 tok/s per 1,000 mm2, holding 1 session, against 168 copies of one unified HBM die at the same silicon: 12.6x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Pro on 277,350 mm2 of ROM silicon at 3,630 tok/s per user against 277,536 mm2 of a100_sxm_80gb-x336-hybrid at 263 tok/s: **13.8x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 8,098 resident sessions against the GPU cluster's 51,500. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 7.13x to it.** At 231,125 mm2 on MiMo-V2.6-Pro the pipeline-only GPU delivers 40.41 tok/s and the same silicon running tensor delivers 288 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.03x (MiMo-V2.6-Pro, ROM binding on `link_latency`) to 10.29x (MiMo-V2.6-Pro, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Pro engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 194 to 26,197 tok/s, and its rate with every slot occupied from 25,553 to 26,197. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 132 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 2,056 us over NVLink, capping per-user decode at 486 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 334.6 us and cap it at 2,989 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 6 of 10 operating points and an array 4; on tokens per second per square millimetre the same points go 6 to the array and 4 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 201 of 3783 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 36.2x of aggregate throughput (MiMo-V2.6-Pro). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 7.37x, on MiMo-V2.6-Pro at batch 4096, where the busiest region carries 3.17x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 80% of its cooling budget. The companion study at the other node does have power-limited points.


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

### MiMo-V2.6-Pro at 8,192 tokens

**Recommended: `ROM-N6-native-SRAMKV-wafer-hybrid-x3`** -- 3 x 46,225 mm2 wafers, 138,675 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **3,567.3 tok/s per user** (0.28 ms/token), binding on `layer_fixed_latency`
- **25.7 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 3,567 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 10,408 W at 0.075 W/mm2, 2,917.6 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 168 copies of one unified HBM die -- `a100_sxm_80gb-x168-tensor`, 138,768 mm2, area ratio 0.9993 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 138,675 | 138,768 | 0.9993 |
| user tok/s | 3,567.3 | 283.7 | 12.57x |
| aggregate tok/s | 3,567 | 284 | 0.53x |
| resident sessions | 1 | 25,133 | -- |
| J/token | 2.9176 | 89.6921 | 30.7x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 25,133 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x280-tensor` at 231,280 mm2 and 287.9 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,567.3 | 25.7 | 1 | 12.57x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 3,636.1 | 15.7 | 6,748 | 12.63x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-hybrid-x122` | 99,430 | 1,572.1 | 15.8 | 1 | 5.62x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,567.3 | 25.7 | 1 | 12.57x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,567.3 | 25.7 | -- | 25.7 | ACCEPT |
| `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 3,636.1 | 15.7 | 0.7 | 25.7 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x3` **<-- recommended** | 138,675 | 3 | 3,567.3 | 3,567 | 25.7 | 1 | `layer_fixed_latency` | 10,408 | 2,917.6 | `a100_sxm_80gb-x168-tensor` | 12.57x |
| `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 5 | 3,636.1 | 32,725 | 15.7 | 6,748 | `layer_fixed_latency` | 26,469 | 6,767.3 | `a100_sxm_80gb-x280-tensor` | 12.63x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 288 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x139` | 113,285 | 2,258.3 | 19.9 | 1 |
| array | 288 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 171,965 | 3,007.4 | 17.5 | 33,115 |
| array | 288 | smallest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x122` | 99,430 | 1,572.1 | 15.8 | 1 |
| wafer | 57 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,567.3 | 25.7 | 1 |
| wafer | 57 | fastest | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 3,636.1 | 15.7 | 6,748 |
| wafer | 57 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,567.3 | 25.7 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 171,965 | 3,007.4 | 81,201 | 33,115 | 23,346 | 6,098.3 | `layer_fixed_latency` | `a100_sxm_80gb-x208-tensor` | 285.7 | 31,411 | 109,298.3 | 1.001 | 10.53x | 17.9x |
| 1 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 3,636.1 | 32,725 | 6,748 | 26,469 | 6,767.3 | `layer_fixed_latency` | `a100_sxm_80gb-x280-tensor` | 287.9 | 42,711 | 144,589.4 | 0.999 | 12.63x | 21.4x |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 171,965 | 3,007.4 | 81,201 | 33,115 | 23,346 | 3,081.1 | `layer_fixed_latency` | `a100_sxm_80gb-x208-hybrid` | 260.9 | 31,411 | 61,743.9 | 1.001 | 11.53x | 19.6x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 3,636.1 | 32,725 | 6,748 | 26,469 | 3,415.7 | `layer_fixed_latency` | `a100_sxm_80gb-x280-hybrid` | 263.0 | 42,711 | 81,048.4 | 0.999 | 13.83x | 23.3x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 171,965 | 3,007.4 | 81,201 | 33,115 | 23,346 | 1,572.6 | `layer_fixed_latency` | `a100_sxm_80gb-x208-hybrid` | 260.9 | 31,411 | 32,966.8 | 1.001 | 11.53x | 21.0x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 3,636.1 | 32,725 | 6,748 | 26,469 | 1,739.8 | `layer_fixed_latency` | `a100_sxm_80gb-x280-hybrid` | 263.0 | 42,711 | 42,619.0 | 0.999 | 13.83x | 24.5x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 171,965 | 3,007.4 | 81,201 | 33,115 | 23,346 | 818.3 | `layer_fixed_latency` | `a100_sxm_80gb-x208-hybrid` | 236.8 | 31,411 | 19,667.3 | 1.001 | 12.70x | 24.0x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x5` | 231,125 | 3,636.1 | 32,725 | 6,748 | 26,469 | 901.9 | `layer_fixed_latency` | `a100_sxm_80gb-x280-hybrid` | 247.0 | 42,711 | 23,524.7 | 0.999 | 14.72x | 26.1x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 171,965 | 3,007.4 | 81,201 | 33,115 | 23,346 | 441.2 | `layer_fixed_latency` | `a100_sxm_80gb-x208-hybrid` | 216.5 | 31,411 | 12,861.3 | 1.001 | 13.89x | 29.2x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,611.2 | 79,446 | 16,196 | 77,221 | 1,312.5 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 252.2 | 104,234 | 27,296.9 | 0.999 | 14.32x | 20.8x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 205,380 | 2,958.5 | 94,672 | 39,550 | 28,871 | 305.0 | `layer_fixed_latency` | `a100_sxm_80gb-x249-hybrid` | 211.9 | 37,846 | 9,492.3 | 0.999 | 13.96x | 31.1x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,256.7 | 140,039 | 16,196 | 81,100 | 756.2 | `layer_fixed_latency` | `a100_sxm_80gb-x672-hybrid` | 228.4 | 104,234 | 16,439.5 | 0.999 | 14.26x | 21.7x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 308,070 | 2,762.3 | 176,784 | 59,326 | 45,143 | 255.4 | `layer_fixed_latency` | `a100_sxm_80gb-x373-hybrid` | 198.9 | 57,307 | 7,625.7 | 1.000 | 13.88x | 29.9x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 2,723.8 | 174,324 | 16,196 | 82,790 | 474.9 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 211.4 | 104,234 | 11,361.8 | 0.999 | 12.89x | 23.9x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 308,070 | 1,884.0 | 482,308 | 59,326 | 63,978 | 132.6 | `compute` | `a100_sxm_80gb-x373-hybrid` | 116.4 | 57,307 | 3,518.5 | 1.000 | 16.19x | 26.5x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,182.9 | 302,814 | 16,196 | 90,633 | 299.3 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 152.1 | 104,234 | 4,660.4 | 0.999 | 7.78x | 15.6x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 308,070 | 731.2 | 748,730 | 59,326 | 82,685 | 110.4 | `weight_read` | `a100_sxm_80gb-x373-hybrid` | 49.0 | 57,307 | 2,206.3 | 1.000 | 14.91x | 20.0x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 345.9 | 354,201 | 16,196 | 93,763 | 264.7 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 71.5 | 104,234 | 2,661.3 | 0.999 | 4.84x | 10.1x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 308,070 | 230.6 | 944,443 | 59,326 | 92,854 | 98.3 | `compute` | `a100_sxm_80gb-x373-hybrid` | 22.4 | 57,307 | 1,214.2 | 1.000 | 10.29x | 12.3x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 89.5 | 366,735 | 16,196 | 92,868 | 253.2 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 29.5 | 104,234 | 1,654.9 | 0.999 | 3.04x | 6.5x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | wafer | SRAM | 1 |
| 2-8 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | wafer | HBM | 5,398 |
| 16 | `ROM-N6-native-HBMKV-array-hw-hybrid-x158` | 128,770 | array | HBM | 24,797 |
| 32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x204` | 166,260 | array | HBM | 32,017 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 171,965 | array | HBM | 33,115 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x252` | 205,380 | array | HBM | 39,550 |
| 1024 | `ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 277,100 | array | HBM | 53,362 |
| 4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 308,070 | array | HBM | 59,326 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Pro | HBM | rom | 132, 136, 158, 170, 175, 189, 204, 210, 211, 227, 252, 340, 378 |
| MiMo-V2.6-Pro | HBM | sram | 132, 136, 158, 170, 175, 189, 204, 210, 211, 227, 252, 340, 378 |
| MiMo-V2.6-Pro | SRAM | rom | 122, 126, 135, 139, 147, 170, 176, 227, 234, 340, 351 |
| MiMo-V2.6-Pro | SRAM | sram | 122, 126, 135, 139, 147, 170, 176, 227, 234, 340, 351 |

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
| MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 1 | 32 on `rom_wafer_express` | 3.00 | one_shot, rec_doubling | 158.59 | 69.06 | 61.87 | 63.45 | 3,567.3 |
| MiMo-V2.6-Pro | `a100_sxm_80gb-x168-tensor` | 1 | 168 | 3.00 | hierarchical | 472.25 | 2,909.23 | 143.44 | 1,495.86 | 283.7 |
| MiMo-V2.6-Pro | `a100_sxm_80gb-x168-tensor` | 64 | 168 | 3.00 | hierarchical | 472.25 | 22,227.03 | 1,625.06 | 14,830.49 | 41.1 |

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

- **0 of 3,783 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 34%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 39 | 0 | 49.8% | 79.9% | 0.387 | 72% |
| gpu | wafer (>=40,000 mm2) | 1,200 | 0 | 41.0% | 79.7% | 0.386 | 88% |
| rom | wafer (>=40,000 mm2) | 2,544 | 0 | 22.4% | 60.3% | 0.301 | 88% |

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
| MiMo-V2.6-Pro | 1 | 138,675 | `MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 2.917589 | 10,408.0 | layer_fixed_latency | `MiMo-V2.6-Pro/a100_sxm_80gb-x168-tensor` | 89.692141 | 25,445.1 | link_latency | 30.74x |
| MiMo-V2.6-Pro | 2 | 184,900 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4` | 2.533940 | 18,460.5 | layer_fixed_latency | `MiMo-V2.6-Pro/a100_sxm_80gb-x224-hybrid` | 65.635865 | 36,752.5 | link_latency | 25.52x |
| MiMo-V2.6-Pro | 4 | 184,900 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4` | 1.298978 | 18,460.5 | layer_fixed_latency | `MiMo-V2.6-Pro/a100_sxm_80gb-x224-hybrid` | 34.912772 | 36,752.5 | link_latency | 26.88x |
| MiMo-V2.6-Pro | 8 | 184,900 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4` | 0.681748 | 19,369.5 | layer_fixed_latency | `MiMo-V2.6-Pro/a100_sxm_80gb-x224-hybrid` | 20.642799 | 39,677.8 | link_latency | 30.28x |
| MiMo-V2.6-Pro | 16 | 554,700 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1.312472 | 77,220.7 | layer_fixed_latency | `MiMo-V2.6-Pro/a100_sxm_80gb-x672-hybrid` | 27.296943 | 110,164.8 | link_latency | 20.80x |
| MiMo-V2.6-Pro | 32 | 554,700 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 0.756191 | 81,099.5 | layer_fixed_latency | `MiMo-V2.6-Pro/a100_sxm_80gb-x672-hybrid` | 16.439546 | 120,131.1 | link_latency | 21.74x |
| MiMo-V2.6-Pro | 64 | 185,005 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 0.183376 | 30,880.3 | layer_fixed_latency | `MiMo-V2.6-Pro/a100_sxm_80gb-x224-hybrid` | 5.415697 | 60,127.4 | weight_read | 29.53x |
| MiMo-V2.6-Pro | 256 | 308,070 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 0.132649 | 63,977.9 | compute | `MiMo-V2.6-Pro/a100_sxm_80gb-x373-hybrid` | 3.518497 | 104,839.6 | weight_read | 26.52x |
| MiMo-V2.6-Pro | 1024 | 277,100 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 0.105360 | 75,948.9 | compute | `MiMo-V2.6-Pro/a100_sxm_80gb-x335-hybrid` | 2.125200 | 99,892.7 | weight_read | 20.17x |
| MiMo-V2.6-Pro | 4096 | 308,070 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 0.098316 | 92,853.6 | compute | `MiMo-V2.6-Pro/a100_sxm_80gb-x373-hybrid` | 1.214179 | 111,407.8 | weight_read | 12.35x |

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
| MiMo-V2.6-Pro | 8,192 | 1,020 B | 566.0 GB | 4.44 | 0.459 GB | 0.459 GB | 85.8 |

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
| MiMo-V2.6-Pro | 3 | 138,675 | 5,777.5 | wafer-pipeline | 3,567.3 | wafer-hybrid | 1.62x | 1,261.2 | pipeline | 283.7 | tensor | 4.45x | 4.58x | 12.57x | 2.74x |
| MiMo-V2.6-Pro | 4 | 184,900 | 5,857.1 | wafer-pipeline | 3,552.9 | wafer-hybrid | 1.65x | 1,320.9 | pipeline | 286.3 | tensor | 4.61x | 4.43x | 12.41x | 2.80x |
| MiMo-V2.6-Pro | 6 | 277,350 | 5,940.2 | wafer-pipeline | 3,630.5 | wafer-hybrid | 1.64x | 1,386.6 | pipeline | 262.8 | hybrid | 5.28x | 4.28x | 13.81x | 3.22x |
| MiMo-V2.6-Pro | 8 | 369,800 | 5,980.3 | wafer-pipeline | 3,607.5 | wafer-hybrid | 1.66x | 1,422.0 | pipeline | 266.4 | hybrid | 5.34x | 4.21x | 13.54x | 3.22x |
| MiMo-V2.6-Pro | 12 | 554,700 | 6,023.3 | wafer-pipeline | 3,611.2 | wafer-hybrid | 1.67x | 1,459.2 | pipeline | 264.4 | hybrid | 5.52x | 4.13x | 13.66x | 3.31x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 2.74x to 3.31x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Pro | 1 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 3,636.1 | 32,724.8 | layer_fixed_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x280-tensor | 231,280 | 1.00x | tensor | 2,914.56 | 287.9 | 287.9 | link_latency | 12.63x | 2.89x | 89.98x | 12.63x |
| MiMo-V2.6-Pro | 1 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x122 | 99,430 | 1,572.1 | 1,572.1 | link_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x120-tensor | 99,120 | 1.00x | tensor | 2,903.91 | 279.6 | 279.6 | link_latency | 5.62x | 0.32x | 38.90x | 5.62x |
| MiMo-V2.6-Pro | 2 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 3,636.1 | 32,724.8 | layer_fixed_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x280-hybrid | 231,280 | 1.00x | hybrid | 2,899.72 | 263.0 | 1,315.0 | link_latency | 13.83x | 2.89x | 89.98x | 13.83x |
| MiMo-V2.6-Pro | 2 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x132 | 107,580 | 1,506.3 | 7,531.7 | link_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x130-tensor | 107,380 | 1.00x | tensor | 3,209.60 | 255.1 | 510.2 | link_latency | 5.90x | 1.43x | 37.28x | 5.90x |
| MiMo-V2.6-Pro | 4 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 3,636.1 | 32,724.8 | layer_fixed_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x280-hybrid | 231,280 | 1.00x | hybrid | 2,899.72 | 263.0 | 1,315.0 | link_latency | 13.83x | 2.89x | 89.98x | 13.83x |
| MiMo-V2.6-Pro | 4 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x132 | 107,580 | 1,506.3 | 7,531.7 | link_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | 107,380 | 1.00x | hybrid | 2,990.01 | 245.6 | 982.5 | link_latency | 6.13x | 1.43x | 37.28x | 6.13x |
| MiMo-V2.6-Pro | 8 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | 231,125 | 3,636.1 | 32,724.8 | layer_fixed_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x280-hybrid | 231,280 | 1.00x | hybrid | 3,071.90 | 247.0 | 1,976.3 | link_latency | 14.72x | 2.89x | 89.98x | 14.72x |
| MiMo-V2.6-Pro | 8 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x132 | 107,580 | 1,418.8 | 12,769.2 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | 107,380 | 1.00x | hybrid | 3,016.01 | 218.6 | 1,749.2 | link_latency | 6.49x | 2.43x | 35.11x | 6.49x |
| MiMo-V2.6-Pro | 16 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 3,611.2 | 79,446.5 | layer_fixed_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 3,046.63 | 252.2 | 4,035.8 | link_latency | 14.32x | 2.93x | 89.37x | 14.32x |
| MiMo-V2.6-Pro | 16 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x132 | 107,580 | 1,105.5 | 18,794.0 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | 107,380 | 1.00x | hybrid | 1,112.75 | 211.1 | 3,589.3 | weight_read | 5.24x | 3.58x | 27.36x | 5.24x |
| MiMo-V2.6-Pro | 32 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 3,256.7 | 140,038.6 | layer_fixed_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 3,041.27 | 228.4 | 7,307.4 | link_latency | 14.26x | 5.16x | 80.59x | 14.26x |
| MiMo-V2.6-Pro | 32 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x132 | 107,580 | 683.0 | 22,538.4 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | 107,380 | 1.00x | hybrid | 1,137.68 | 180.1 | 5,764.3 | weight_read | 3.79x | 3.91x | 16.90x | 3.79x |
| MiMo-V2.6-Pro | 64 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill | 308,070 | 2,762.3 | 176,784.4 | layer_fixed_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x373-hybrid | 308,098 | 1.00x | hybrid | 1,203.95 | 198.9 | 12,732.6 | weight_read | 13.88x | 11.73x | 68.36x | 13.88x |
| MiMo-V2.6-Pro | 64 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x132 | 107,580 | 374.4 | 23,962.4 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | 107,380 | 1.00x | hybrid | 1,190.84 | 138.0 | 8,834.7 | weight_read | 2.71x | 2.71x | 9.27x | 2.71x |
| MiMo-V2.6-Pro | 256 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill | 308,070 | 1,884.0 | 482,307.6 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x373-hybrid | 308,098 | 1.00x | hybrid | 1,379.57 | 116.4 | 29,796.7 | weight_read | 16.19x | 16.19x | 46.62x | 16.19x |
| MiMo-V2.6-Pro | 256 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x132 | 107,580 | 101.1 | 25,870.4 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | 107,380 | 1.00x | hybrid | 1,509.83 | 61.7 | 15,803.9 | weight_read | 1.64x | 1.64x | 3.17x | 1.64x |
| MiMo-V2.6-Pro | 1024 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378 | 308,070 | 731.2 | 748,729.7 | weight_read | MiMo-V2.6-Pro/a100_sxm_80gb-x373-hybrid | 308,098 | 1.00x | hybrid | 2,082.04 | 49.0 | 50,225.3 | weight_read | 14.91x | 14.91x | 26.77x | 14.91x |
| MiMo-V2.6-Pro | 1024 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x132 | 107,580 | 25.5 | 26,130.8 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | 107,380 | 1.00x | hybrid | 2,785.81 | 26.4 | 27,003.8 | weight_read | 0.97x | 0.97x | 1.76x | 0.97x |
| MiMo-V2.6-Pro | 4096 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 230.6 | 944,443.2 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x373-hybrid | 308,098 | 1.00x | hybrid | 4,891.92 | 22.4 | 91,755.7 | weight_read | 10.29x | 10.29x | 20.13x | 10.29x |
| MiMo-V2.6-Pro | 4096 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x132 | 107,580 | 6.4 | 26,196.6 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | 107,380 | 1.00x | hybrid | 7,889.70 | 16.3 | 66,964.8 | weight_read | 0.39x | 0.39x | 1.17x | 0.39x |

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
| MiMo-V2.6-Pro | 34 | 28,084 | 40.6 | 247.1 | 210.7 | tensor | 2,866.64 | 70.8% | link_latency |
| MiMo-V2.6-Pro | 56 | 46,256 | 40.5 | 264.2 | 238.7 | tensor | 2,882.61 | 76.2% | link_latency |
| MiMo-V2.6-Pro | 59 | 48,734 | 40.5 | 265.4 | 241.2 | tensor | 2,887.60 | 76.6% | link_latency |
| MiMo-V2.6-Pro | 65 | 53,690 | 40.4 | 267.8 | 243.6 | tensor | 2,891.49 | 77.4% | link_latency |
| MiMo-V2.6-Pro | 75 | 61,950 | 40.4 | 271.1 | 249.6 | tensor | 2,894.59 | 78.5% | link_latency |
| MiMo-V2.6-Pro | 112 | 92,512 | 40.4 | 278.6 | 263.5 | tensor | 2,902.58 | 80.9% | link_latency |
| MiMo-V2.6-Pro | 120 | 99,120 | 40.4 | 279.6 | 265.5 | tensor | 2,903.91 | 81.2% | link_latency |
| MiMo-V2.6-Pro | 124 | 102,424 | 40.4 | 280.0 | 266.4 | tensor | 2,905.07 | 81.3% | link_latency |
| MiMo-V2.6-Pro | 130 | 107,380 | 40.4 | 280.6 | 254.9 | tensor | 2,906.10 | 81.5% | link_latency |
| MiMo-V2.6-Pro | 133 | 109,858 | 40.4 | 280.9 | 255.7 | tensor | 2,906.10 | 81.6% | link_latency |
| MiMo-V2.6-Pro | 134 | 110,684 | 40.4 | 281.0 | 256.0 | tensor | 2,906.10 | 81.7% | link_latency |
| MiMo-V2.6-Pro | 137 | 113,162 | 40.4 | 281.3 | 256.8 | tensor | 2,907.01 | 81.8% | link_latency |
| MiMo-V2.6-Pro | 145 | 119,770 | 40.4 | 282.0 | 258.7 | tensor | 2,907.83 | 82.0% | link_latency |
| MiMo-V2.6-Pro | 156 | 128,856 | 40.4 | 282.9 | 261.1 | tensor | 2,908.57 | 82.3% | link_latency |
| MiMo-V2.6-Pro | 168 | 138,768 | 40.4 | 283.7 | 263.3 | tensor | 2,909.23 | 82.5% | link_latency |
| MiMo-V2.6-Pro | 173 | 142,898 | 40.4 | 284.0 | 264.2 | tensor | 2,909.84 | 82.6% | link_latency |
| MiMo-V2.6-Pro | 174 | 143,724 | 40.4 | 284.0 | 264.4 | tensor | 2,909.84 | 82.7% | link_latency |
| MiMo-V2.6-Pro | 186 | 153,636 | 40.4 | 284.7 | 266.3 | tensor | 2,910.90 | 82.9% | link_latency |
| MiMo-V2.6-Pro | 201 | 166,026 | 40.4 | 285.4 | 259.8 | tensor | 2,911.79 | 83.1% | link_latency |
| MiMo-V2.6-Pro | 207 | 170,982 | 40.4 | 285.7 | 260.7 | tensor | 2,911.79 | 83.2% | link_latency |
| MiMo-V2.6-Pro | 208 | 171,808 | 40.4 | 285.7 | 260.9 | tensor | 2,911.79 | 83.2% | link_latency |
| MiMo-V2.6-Pro | 224 | 185,024 | 40.4 | 286.3 | 263.2 | tensor | 2,912.56 | 83.4% | link_latency |
| MiMo-V2.6-Pro | 231 | 190,806 | 40.4 | 286.6 | 264.1 | tensor | 2,912.90 | 83.5% | link_latency |
| MiMo-V2.6-Pro | 249 | 205,674 | 40.4 | 287.1 | 266.2 | tensor | 2,913.81 | 83.7% | link_latency |
| MiMo-V2.6-Pro | 280 | 231,280 | 40.4 | 287.9 | 263.0 | tensor | 2,914.56 | 83.9% | link_latency |
| MiMo-V2.6-Pro | 335 | 276,710 | 40.4 | 231.9 | 262.7 | hybrid | 2,902.24 | 76.3% | link_latency |
| MiMo-V2.6-Pro | 336 | 277,536 | 40.4 | 231.9 | 262.8 | hybrid | 2,902.24 | 76.3% | link_latency |
| MiMo-V2.6-Pro | 346 | 285,796 | 40.4 | 232.0 | 263.7 | hybrid | 2,902.24 | 76.5% | link_latency |
| MiMo-V2.6-Pro | 373 | 308,098 | 40.4 | 232.2 | 265.8 | hybrid | 2,902.24 | 77.1% | link_latency |
| MiMo-V2.6-Pro | 448 | 370,048 | 40.4 | 232.8 | 266.4 | hybrid | 2,904.76 | 77.4% | link_latency |
| MiMo-V2.6-Pro | 672 | 555,072 | 40.4 | 233.6 | 264.4 | hybrid | 2,914.85 | 77.1% | link_latency |

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
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x139 | MiMo-V2.6-Pro | 139 | pipeline | rom_package_ucie | rom_board_serdes | 69 | 7.81 us | 12,810.6 tok/s | 128,105.7 tok/s | 35 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.45 us; 34 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 7.35 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x126 | MiMo-V2.6-Pro | 126 | tensor | rom_package_ucie | rom_board_serdes | 280 | 457.31 us | 218.7 tok/s | 2,186.7 tok/s | 140 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.69 us; 140 x all_reduce span 63 on rom_board_serdes (traversals 15.4) = 453.61 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x139 | MiMo-V2.6-Pro | 139 | hybrid | rom_package_ucie | rom_board_serdes | 209 | 18.62 us | 5,371.1 tok/s | 53,711.5 tok/s | 140 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.69 us; 69 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 14.92 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x139 | MiMo-V2.6-Pro | 139 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3 | MiMo-V2.6-Pro | 3 | pipeline | on_wafer | rom_wafer_serdes | 69 | 8.71 us | 11,479.5 tok/s | 114,794.8 tok/s | 68 x point_to_point span 2 on on_wafer (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.21 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-tensor-x122 | MiMo-V2.6-Pro | 122 | tensor | nvlink3 | infiniband_hdr | 280 | 1,476.99 us | 67.7 tok/s | 677.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 761.94 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x3 | MiMo-V2.6-Pro | 3 | tensor | on_wafer | rom_wafer_serdes | 280 | 334.48 us | 299.0 tok/s | 2,989.7 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 140 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 64.98 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hybrid-x135 | MiMo-V2.6-Pro | 135 | hybrid | nvlink3 | infiniband_hdr | 156 | 755.40 us | 132.4 tok/s | 1,323.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.34 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | MiMo-V2.6-Pro | 3 | hybrid | on_wafer | rom_wafer_serdes | 142 | 269.92 us | 370.5 tok/s | 3,704.8 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.42 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x211 | MiMo-V2.6-Pro | 211 | pipeline | rom_package_ucie | rom_board_serdes | 69 | 7.81 us | 12,810.6 tok/s | 128,105.7 tok/s | 35 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.45 us; 34 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 7.35 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x136 | MiMo-V2.6-Pro | 136 | tensor | rom_package_ucie | rom_board_serdes | 280 | 521.68 us | 191.7 tok/s | 1,916.9 tok/s | 140 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.69 us; 140 x all_reduce span 68 on rom_board_serdes (traversals 17.6) = 517.99 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x204 | MiMo-V2.6-Pro | 204 | hybrid | rom_package_ucie | rom_board_serdes | 209 | 18.62 us | 5,371.1 tok/s | 53,711.5 tok/s | 140 x all_reduce span 2 on rom_package_ucie (traversals 2.2) = 3.69 us; 69 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 14.92 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-pipeline-x210 | MiMo-V2.6-Pro | 210 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4 | MiMo-V2.6-Pro | 4 | pipeline | on_wafer | rom_wafer_serdes | 69 | 8.71 us | 11,479.5 tok/s | 114,794.8 tok/s | 68 x point_to_point span 2 on on_wafer (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.21 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-tensor-x132 | MiMo-V2.6-Pro | 132 | tensor | nvlink3 | infiniband_hdr | 280 | 1,477.75 us | 67.7 tok/s | 676.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 762.69 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-tensor-x4 | MiMo-V2.6-Pro | 4 | tensor | on_wafer | rom_wafer_serdes | 280 | 334.55 us | 298.9 tok/s | 2,989.0 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 140 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 65.05 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hybrid-x175 | MiMo-V2.6-Pro | 175 | hybrid | nvlink3 | infiniband_hdr | 161 | 768.00 us | 130.2 tok/s | 1,302.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.95 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | MiMo-V2.6-Pro | 5 | hybrid | on_wafer | rom_wafer_serdes | 144 | 270.34 us | 369.9 tok/s | 3,699.0 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 4 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.84 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x34-pipeline | MiMo-V2.6-Pro | 34 | pipeline | nvlink3 | infiniband_hdr | 33 | 83.77 us | 1,193.7 tok/s | 11,936.9 tok/s | 29 x point_to_point span 2 on nvlink3 (traversals 1.0) = 73.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 10.09 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x34-tensor | MiMo-V2.6-Pro | 34 | tensor | nvlink3 | infiniband_hdr | 280 | 1,448.60 us | 69.0 tok/s | 690.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 733.55 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x34-hybrid | MiMo-V2.6-Pro | 34 | hybrid | nvlink3 | infiniband_hdr | 144 | 725.14 us | 137.9 tok/s | 1,379.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 10.09 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x34-expert | MiMo-V2.6-Pro | 34 | expert | nvlink3 | infiniband_hdr | 280 | 1,004.15 us | 99.6 tok/s | 995.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 703.76 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 300.39 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-pipeline | MiMo-V2.6-Pro | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 139.64 us | 716.1 tok/s | 7,161.5 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.51 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.13 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-tensor | MiMo-V2.6-Pro | 56 | tensor | nvlink3 | infiniband_hdr | 280 | 1,460.40 us | 68.5 tok/s | 684.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 745.35 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-hybrid | MiMo-V2.6-Pro | 56 | hybrid | nvlink3 | infiniband_hdr | 146 | 730.18 us | 137.0 tok/s | 1,369.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.13 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-expert | MiMo-V2.6-Pro | 56 | expert | nvlink3 | infiniband_hdr | 280 | 996.18 us | 100.4 tok/s | 1,003.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 702.15 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 294.03 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x59-pipeline | MiMo-V2.6-Pro | 59 | pipeline | nvlink3 | infiniband_hdr | 58 | 147.24 us | 679.2 tok/s | 6,791.7 tok/s | 51 x point_to_point span 2 on nvlink3 (traversals 1.0) = 129.59 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.65 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x59-tensor | MiMo-V2.6-Pro | 59 | tensor | nvlink3 | infiniband_hdr | 280 | 1,464.09 us | 68.3 tok/s | 683.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 749.03 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x59-hybrid | MiMo-V2.6-Pro | 59 | hybrid | nvlink3 | infiniband_hdr | 147 | 732.70 us | 136.5 tok/s | 1,364.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.65 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x59-expert | MiMo-V2.6-Pro | 59 | expert | nvlink3 | infiniband_hdr | 280 | 995.68 us | 100.4 tok/s | 1,004.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 702.15 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 293.53 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x65-pipeline | MiMo-V2.6-Pro | 65 | pipeline | nvlink3 | infiniband_hdr | 64 | 162.47 us | 615.5 tok/s | 6,155.1 tok/s | 56 x point_to_point span 2 on nvlink3 (traversals 1.0) = 142.29 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x65-tensor | MiMo-V2.6-Pro | 65 | tensor | nvlink3 | infiniband_hdr | 280 | 1,466.95 us | 68.2 tok/s | 681.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 751.90 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x65-hybrid | MiMo-V2.6-Pro | 65 | hybrid | nvlink3 | infiniband_hdr | 148 | 735.22 us | 136.0 tok/s | 1,360.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x65-expert | MiMo-V2.6-Pro | 65 | expert | nvlink3 | infiniband_hdr | 280 | 994.55 us | 100.5 tok/s | 1,005.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.88 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 292.67 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x75-pipeline | MiMo-V2.6-Pro | 75 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x75-tensor | MiMo-V2.6-Pro | 75 | tensor | nvlink3 | infiniband_hdr | 280 | 1,469.25 us | 68.1 tok/s | 680.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 754.19 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x75-hybrid | MiMo-V2.6-Pro | 75 | hybrid | nvlink3 | infiniband_hdr | 149 | 737.75 us | 135.5 tok/s | 1,355.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 22.69 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x75-expert | MiMo-V2.6-Pro | 75 | expert | nvlink3 | infiniband_hdr | 280 | 993.21 us | 100.7 tok/s | 1,006.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.67 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 291.54 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-pipeline | MiMo-V2.6-Pro | 112 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-tensor | MiMo-V2.6-Pro | 112 | tensor | nvlink3 | infiniband_hdr | 280 | 1,475.15 us | 67.8 tok/s | 677.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 760.09 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-hybrid | MiMo-V2.6-Pro | 112 | hybrid | nvlink3 | infiniband_hdr | 153 | 747.83 us | 133.7 tok/s | 1,337.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 32.78 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-expert | MiMo-V2.6-Pro | 112 | expert | nvlink3 | infiniband_hdr | 280 | 990.19 us | 101.0 tok/s | 1,009.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.08 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 289.12 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x120-pipeline | MiMo-V2.6-Pro | 120 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x120-tensor | MiMo-V2.6-Pro | 120 | tensor | nvlink3 | infiniband_hdr | 280 | 1,476.13 us | 67.7 tok/s | 677.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 761.08 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x120-hybrid | MiMo-V2.6-Pro | 120 | hybrid | nvlink3 | infiniband_hdr | 154 | 750.35 us | 133.3 tok/s | 1,332.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.30 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x120-expert | MiMo-V2.6-Pro | 120 | expert | nvlink3 | infiniband_hdr | 280 | 989.79 us | 101.0 tok/s | 1,010.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.00 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.79 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x124-pipeline | MiMo-V2.6-Pro | 124 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x124-tensor | MiMo-V2.6-Pro | 124 | tensor | nvlink3 | infiniband_hdr | 280 | 1,476.99 us | 67.7 tok/s | 677.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 761.94 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x124-hybrid | MiMo-V2.6-Pro | 124 | hybrid | nvlink3 | infiniband_hdr | 155 | 752.88 us | 132.8 tok/s | 1,328.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 37.82 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x124-expert | MiMo-V2.6-Pro | 124 | expert | nvlink3 | infiniband_hdr | 280 | 989.64 us | 101.0 tok/s | 1,010.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.00 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.64 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x130-pipeline | MiMo-V2.6-Pro | 130 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x130-tensor | MiMo-V2.6-Pro | 130 | tensor | nvlink3 | infiniband_hdr | 280 | 1,477.75 us | 67.7 tok/s | 676.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 762.69 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | MiMo-V2.6-Pro | 130 | hybrid | nvlink3 | infiniband_hdr | 156 | 755.40 us | 132.4 tok/s | 1,323.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x130-expert | MiMo-V2.6-Pro | 130 | expert | nvlink3 | infiniband_hdr | 280 | 989.38 us | 101.1 tok/s | 1,010.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.94 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x133-pipeline | MiMo-V2.6-Pro | 133 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x133-tensor | MiMo-V2.6-Pro | 133 | tensor | nvlink3 | infiniband_hdr | 280 | 1,477.75 us | 67.7 tok/s | 676.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 762.69 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x133-hybrid | MiMo-V2.6-Pro | 133 | hybrid | nvlink3 | infiniband_hdr | 156 | 755.40 us | 132.4 tok/s | 1,323.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x133-expert | MiMo-V2.6-Pro | 133 | expert | nvlink3 | infiniband_hdr | 280 | 989.28 us | 101.1 tok/s | 1,010.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.94 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x134-pipeline | MiMo-V2.6-Pro | 134 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x134-tensor | MiMo-V2.6-Pro | 134 | tensor | nvlink3 | infiniband_hdr | 280 | 1,477.75 us | 67.7 tok/s | 676.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 762.69 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x134-hybrid | MiMo-V2.6-Pro | 134 | hybrid | nvlink3 | infiniband_hdr | 156 | 755.40 us | 132.4 tok/s | 1,323.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x134-expert | MiMo-V2.6-Pro | 134 | expert | nvlink3 | infiniband_hdr | 280 | 989.25 us | 101.1 tok/s | 1,010.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.94 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.31 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x137-pipeline | MiMo-V2.6-Pro | 137 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x137-tensor | MiMo-V2.6-Pro | 137 | tensor | nvlink3 | infiniband_hdr | 280 | 1,478.42 us | 67.6 tok/s | 676.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 763.37 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x137-hybrid | MiMo-V2.6-Pro | 137 | hybrid | nvlink3 | infiniband_hdr | 157 | 757.92 us | 131.9 tok/s | 1,319.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 42.87 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x137-expert | MiMo-V2.6-Pro | 137 | expert | nvlink3 | infiniband_hdr | 280 | 989.10 us | 101.1 tok/s | 1,011.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.89 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.22 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x145-pipeline | MiMo-V2.6-Pro | 145 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x145-tensor | MiMo-V2.6-Pro | 145 | tensor | nvlink3 | infiniband_hdr | 280 | 1,479.03 us | 67.6 tok/s | 676.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 763.97 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x145-hybrid | MiMo-V2.6-Pro | 145 | hybrid | nvlink3 | infiniband_hdr | 158 | 760.44 us | 131.5 tok/s | 1,315.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 45.39 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x145-expert | MiMo-V2.6-Pro | 145 | expert | nvlink3 | infiniband_hdr | 280 | 988.83 us | 101.1 tok/s | 1,011.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.84 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.00 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x156-pipeline | MiMo-V2.6-Pro | 156 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x156-tensor | MiMo-V2.6-Pro | 156 | tensor | nvlink3 | infiniband_hdr | 280 | 1,479.57 us | 67.6 tok/s | 675.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 764.52 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x156-hybrid | MiMo-V2.6-Pro | 156 | hybrid | nvlink3 | infiniband_hdr | 159 | 762.96 us | 131.1 tok/s | 1,310.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.91 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x156-expert | MiMo-V2.6-Pro | 156 | expert | nvlink3 | infiniband_hdr | 280 | 988.52 us | 101.2 tok/s | 1,011.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.79 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.73 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-pipeline | MiMo-V2.6-Pro | 168 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-tensor | MiMo-V2.6-Pro | 168 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.06 us | 67.6 tok/s | 675.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 765.01 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-hybrid | MiMo-V2.6-Pro | 168 | hybrid | nvlink3 | infiniband_hdr | 160 | 765.48 us | 130.6 tok/s | 1,306.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 50.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-expert | MiMo-V2.6-Pro | 168 | expert | nvlink3 | infiniband_hdr | 280 | 988.19 us | 101.2 tok/s | 1,011.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.72 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.48 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x173-pipeline | MiMo-V2.6-Pro | 173 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x173-tensor | MiMo-V2.6-Pro | 173 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.51 us | 67.5 tok/s | 675.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 765.45 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x173-hybrid | MiMo-V2.6-Pro | 173 | hybrid | nvlink3 | infiniband_hdr | 161 | 768.00 us | 130.2 tok/s | 1,302.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.95 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x173-expert | MiMo-V2.6-Pro | 173 | expert | nvlink3 | infiniband_hdr | 280 | 988.10 us | 101.2 tok/s | 1,012.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.72 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.38 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x174-pipeline | MiMo-V2.6-Pro | 174 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x174-tensor | MiMo-V2.6-Pro | 174 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.51 us | 67.5 tok/s | 675.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 765.45 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x174-hybrid | MiMo-V2.6-Pro | 174 | hybrid | nvlink3 | infiniband_hdr | 161 | 768.00 us | 130.2 tok/s | 1,302.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.95 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x174-expert | MiMo-V2.6-Pro | 174 | expert | nvlink3 | infiniband_hdr | 280 | 988.08 us | 101.2 tok/s | 1,012.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.72 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.36 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x186-pipeline | MiMo-V2.6-Pro | 186 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x186-tensor | MiMo-V2.6-Pro | 186 | tensor | nvlink3 | infiniband_hdr | 280 | 1,481.29 us | 67.5 tok/s | 675.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 766.24 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x186-hybrid | MiMo-V2.6-Pro | 186 | hybrid | nvlink3 | infiniband_hdr | 163 | 773.05 us | 129.4 tok/s | 1,293.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 57.99 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x186-expert | MiMo-V2.6-Pro | 186 | expert | nvlink3 | infiniband_hdr | 280 | 987.81 us | 101.2 tok/s | 1,012.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.65 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.16 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x201-pipeline | MiMo-V2.6-Pro | 201 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x201-tensor | MiMo-V2.6-Pro | 201 | tensor | nvlink3 | infiniband_hdr | 280 | 1,481.95 us | 67.5 tok/s | 674.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 766.90 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x201-hybrid | MiMo-V2.6-Pro | 201 | hybrid | nvlink3 | infiniband_hdr | 165 | 778.09 us | 128.5 tok/s | 1,285.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.04 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x201-expert | MiMo-V2.6-Pro | 201 | expert | nvlink3 | infiniband_hdr | 280 | 987.54 us | 101.3 tok/s | 1,012.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.60 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.94 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x207-pipeline | MiMo-V2.6-Pro | 207 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x207-tensor | MiMo-V2.6-Pro | 207 | tensor | nvlink3 | infiniband_hdr | 280 | 1,481.95 us | 67.5 tok/s | 674.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 766.90 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x207-hybrid | MiMo-V2.6-Pro | 207 | hybrid | nvlink3 | infiniband_hdr | 165 | 778.09 us | 128.5 tok/s | 1,285.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.04 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x207-expert | MiMo-V2.6-Pro | 207 | expert | nvlink3 | infiniband_hdr | 280 | 987.46 us | 101.3 tok/s | 1,012.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.60 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.86 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x208-pipeline | MiMo-V2.6-Pro | 208 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x208-tensor | MiMo-V2.6-Pro | 208 | tensor | nvlink3 | infiniband_hdr | 280 | 1,481.95 us | 67.5 tok/s | 674.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 766.90 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x208-hybrid | MiMo-V2.6-Pro | 208 | hybrid | nvlink3 | infiniband_hdr | 165 | 778.09 us | 128.5 tok/s | 1,285.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.04 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x208-expert | MiMo-V2.6-Pro | 208 | expert | nvlink3 | infiniband_hdr | 280 | 987.43 us | 101.3 tok/s | 1,012.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.58 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.85 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-pipeline | MiMo-V2.6-Pro | 224 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-tensor | MiMo-V2.6-Pro | 224 | tensor | nvlink3 | infiniband_hdr | 280 | 1,482.52 us | 67.5 tok/s | 674.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 767.47 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-hybrid | MiMo-V2.6-Pro | 224 | hybrid | nvlink3 | infiniband_hdr | 167 | 783.13 us | 127.7 tok/s | 1,276.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 68.08 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-expert | MiMo-V2.6-Pro | 224 | expert | nvlink3 | infiniband_hdr | 280 | 987.20 us | 101.3 tok/s | 1,013.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.54 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.66 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x231-pipeline | MiMo-V2.6-Pro | 231 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x231-tensor | MiMo-V2.6-Pro | 231 | tensor | nvlink3 | infiniband_hdr | 280 | 1,482.77 us | 67.4 tok/s | 674.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 767.72 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x231-hybrid | MiMo-V2.6-Pro | 231 | hybrid | nvlink3 | infiniband_hdr | 168 | 785.66 us | 127.3 tok/s | 1,272.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.60 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x231-expert | MiMo-V2.6-Pro | 231 | expert | nvlink3 | infiniband_hdr | 280 | 987.12 us | 101.3 tok/s | 1,013.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.54 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.58 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x249-pipeline | MiMo-V2.6-Pro | 249 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x249-tensor | MiMo-V2.6-Pro | 249 | tensor | nvlink3 | infiniband_hdr | 280 | 1,483.44 us | 67.4 tok/s | 674.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 32 on infiniband_hdr (traversals 2.0) = 768.39 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x249-hybrid | MiMo-V2.6-Pro | 249 | hybrid | nvlink3 | infiniband_hdr | 171 | 793.22 us | 126.1 tok/s | 1,260.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 31 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 78.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x249-expert | MiMo-V2.6-Pro | 249 | expert | nvlink3 | infiniband_hdr | 280 | 986.90 us | 101.3 tok/s | 1,013.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.49 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.41 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x280-pipeline | MiMo-V2.6-Pro | 280 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x280-tensor | MiMo-V2.6-Pro | 280 | tensor | nvlink3 | infiniband_hdr | 280 | 1,483.99 us | 67.4 tok/s | 673.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 768.94 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x280-hybrid | MiMo-V2.6-Pro | 280 | hybrid | nvlink3 | infiniband_hdr | 174 | 800.78 us | 124.9 tok/s | 1,248.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 85.73 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x280-expert | MiMo-V2.6-Pro | 280 | expert | nvlink3 | infiniband_hdr | 280 | 986.60 us | 101.4 tok/s | 1,013.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.43 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-pipeline | MiMo-V2.6-Pro | 335 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-tensor | MiMo-V2.6-Pro | 335 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.38 us | 48.7 tok/s | 487.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,338.32 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-hybrid | MiMo-V2.6-Pro | 335 | hybrid | nvlink3 | infiniband_hdr | 181 | 818.44 us | 122.2 tok/s | 1,221.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 103.38 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-expert | MiMo-V2.6-Pro | 335 | expert | nvlink3 | infiniband_hdr | 280 | 986.21 us | 101.4 tok/s | 1,014.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.37 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.84 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-pipeline | MiMo-V2.6-Pro | 336 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-tensor | MiMo-V2.6-Pro | 336 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.38 us | 48.7 tok/s | 487.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,338.32 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-hybrid | MiMo-V2.6-Pro | 336 | hybrid | nvlink3 | infiniband_hdr | 181 | 818.44 us | 122.2 tok/s | 1,221.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 103.38 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-expert | MiMo-V2.6-Pro | 336 | expert | nvlink3 | infiniband_hdr | 280 | 986.20 us | 101.4 tok/s | 1,014.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.36 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.84 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x346-pipeline | MiMo-V2.6-Pro | 346 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x346-tensor | MiMo-V2.6-Pro | 346 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.60 us | 48.7 tok/s | 486.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 44 on infiniband_hdr (traversals 4.0) = 1,338.55 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x346-hybrid | MiMo-V2.6-Pro | 346 | hybrid | nvlink3 | infiniband_hdr | 183 | 823.48 us | 121.4 tok/s | 1,214.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 43 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 108.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x346-expert | MiMo-V2.6-Pro | 346 | expert | nvlink3 | infiniband_hdr | 280 | 986.14 us | 101.4 tok/s | 1,014.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.35 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.79 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x373-pipeline | MiMo-V2.6-Pro | 373 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x373-tensor | MiMo-V2.6-Pro | 373 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.90 us | 48.7 tok/s | 486.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 1,338.85 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x373-hybrid | MiMo-V2.6-Pro | 373 | hybrid | nvlink3 | infiniband_hdr | 186 | 831.04 us | 120.3 tok/s | 1,203.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 46 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 115.99 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x373-expert | MiMo-V2.6-Pro | 373 | expert | nvlink3 | infiniband_hdr | 280 | 986.00 us | 101.4 tok/s | 1,014.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.33 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.68 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-pipeline | MiMo-V2.6-Pro | 448 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-tensor | MiMo-V2.6-Pro | 448 | tensor | nvlink3 | infiniband_hdr | 280 | 2,054.60 us | 48.7 tok/s | 486.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,339.55 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-hybrid | MiMo-V2.6-Pro | 448 | hybrid | nvlink3 | infiniband_hdr | 195 | 853.74 us | 117.1 tok/s | 1,171.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 138.68 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-expert | MiMo-V2.6-Pro | 448 | expert | nvlink3 | infiniband_hdr | 280 | 985.70 us | 101.5 tok/s | 1,014.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.27 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-pipeline | MiMo-V2.6-Pro | 672 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-tensor | MiMo-V2.6-Pro | 672 | tensor | nvlink3 | infiniband_hdr | 280 | 2,055.83 us | 48.6 tok/s | 486.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,340.78 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-hybrid | MiMo-V2.6-Pro | 672 | hybrid | nvlink3 | infiniband_hdr | 209 | 889.04 us | 112.5 tok/s | 1,124.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 69 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 173.98 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-expert | MiMo-V2.6-Pro | 672 | expert | nvlink3 | infiniband_hdr | 280 | 985.20 us | 101.5 tok/s | 1,015.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.18 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.02 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Pro | 1 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | 138,675 | 3,567.3 | 0.026 | 2,977.7 (166,260) | 3,567.3 (138,675) | 1.20x | layer_fixed_latency |
| MiMo-V2.6-Pro | 2 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 3,552.9 | 0.019 | 2,977.7 (166,260) | 3,552.9 (184,900) | 1.19x | layer_fixed_latency |
| MiMo-V2.6-Pro | 4 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 3,552.9 | 0.019 | 2,977.7 (166,260) | 3,552.9 (184,900) | 1.19x | layer_fixed_latency |
| MiMo-V2.6-Pro | 8 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 3,551.4 | 0.019 | 2,977.7 (166,260) | 3,551.4 (184,900) | 1.19x | layer_fixed_latency |
| MiMo-V2.6-Pro | 16 | wafer | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 3,611.2 | 0.007 | 2,977.7 (166,260) | 3,611.2 (554,700) | 1.21x | layer_fixed_latency |
| MiMo-V2.6-Pro | 32 | wafer | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 3,256.7 | 0.006 | 2,887.1 (185,005) | 3,256.7 (554,700) | 1.13x | layer_fixed_latency |
| MiMo-V2.6-Pro | 64 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 2,631.2 | 0.014 | 2,631.2 (185,005) | 2,723.8 (554,700) | 1.04x | layer_fixed_latency |
| MiMo-V2.6-Pro | 256 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill | 308,070 | 1,884.0 | 0.006 | 1,884.0 (308,070) | 1,182.9 (554,700) | 0.63x | compute |
| MiMo-V2.6-Pro | 1024 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 704.0 | 0.003 | 704.0 (277,100) | 345.9 (554,700) | 0.49x | compute |
| MiMo-V2.6-Pro | 4096 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 230.6 | 0.001 | 230.6 (308,070) | 89.5 (554,700) | 0.39x | compute |

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
| MiMo-V2.6-Pro | 384 | 1,383.7 MB | 303.5 mm2 | 54.63 mm2 (18.0%) | 116,538 mm2 | 20,977 mm2 | 124,143 mm2 = 152.3 reticles |

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
| MiMo-V2.6-Pro | 1 | sram | 346,251.7 | 25,720.0 | 25,720.0 | 13.46x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 2 | sram | 346,251.7 | 25,720.0 | 25,720.0 | 13.46x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 4 | sram | 346,251.7 | 25,720.0 | 25,720.0 | 13.46x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 8 | sram | 346,251.7 | 25,720.0 | 25,720.0 | 13.46x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 16 | sram | 346,251.7 | 25,720.0 | 34,760.2 | 13.46x | 1.35x | kv_read | weight_read | layer_fixed_latency |
| MiMo-V2.6-Pro | 32 | sram | 346,251.7 | 25,720.0 | 54,996.9 | 13.46x | 2.14x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 64 | sram | 346,251.7 | 25,720.0 | 84,821.7 | 13.46x | 3.30x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 256 | sram | 416,312.1 | 25,763.1 | 109,827.8 | 16.16x | 4.26x | weight_read | weight_read | kv_read |
| MiMo-V2.6-Pro | 1024 | sram | 748,729.7 | 26,021.7 | 163,124.5 | 28.77x | 6.27x | weight_read | weight_read | kv_read |
| MiMo-V2.6-Pro | 4096 | sram | 944,443.2 | 26,087.1 | 192,169.6 | 36.20x | 7.37x | compute | weight_read | kv_read |
| MiMo-V2.6-Pro | 1 | rom | 477,792.2 | 92,789.9 | 92,789.9 | 5.15x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 2 | rom | 477,792.2 | 92,789.9 | 92,789.9 | 5.15x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 4 | rom | 477,792.2 | 92,789.9 | 92,789.9 | 5.15x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 8 | rom | 477,792.2 | 92,789.9 | 92,789.9 | 5.15x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 16 | rom | 477,792.2 | 92,789.9 | 92,789.9 | 5.15x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 32 | rom | 477,792.2 | 92,789.9 | 92,789.9 | 5.15x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 64 | rom | 477,792.2 | 92,789.9 | 92,789.9 | 5.15x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 256 | rom | 482,307.6 | 93,352.8 | 118,387.8 | 5.17x | 1.27x | compute | weight_read | weight_read |
| MiMo-V2.6-Pro | 1024 | rom | 637,172.1 | 96,841.1 | 185,415.4 | 6.58x | 1.91x | compute | weight_read | kv_read |
| MiMo-V2.6-Pro | 4096 | rom | 679,219.8 | 97,752.7 | 221,080.0 | 6.95x | 2.26x | compute | weight_read | kv_read |

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
| MiMo-V2.6-Pro | 1 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 346,251.7 | 0.624 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 477,792.2 | 1.551 | weight_read | 1.38x |
| MiMo-V2.6-Pro | 1 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 25,720.0 | 0.139 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 1 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 1 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion | 184,900 | 1.00 | 1.00 | 25,720.0 | 0.139 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 1 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 2 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 346,251.7 | 0.624 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 2 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 477,792.2 | 1.551 | weight_read | 1.38x |
| MiMo-V2.6-Pro | 2 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 25,720.0 | 0.139 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 2 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 2 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion | 184,900 | 1.00 | 1.00 | 25,720.0 | 0.139 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 2 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 4 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 346,251.7 | 0.624 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 477,792.2 | 1.551 | weight_read | 1.38x |
| MiMo-V2.6-Pro | 4 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 25,720.0 | 0.139 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 4 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 4 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion | 184,900 | 1.00 | 1.00 | 25,720.0 | 0.139 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 4 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 8 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 346,251.7 | 0.624 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 8 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 477,792.2 | 1.551 | weight_read | 1.38x |
| MiMo-V2.6-Pro | 8 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 25,720.0 | 0.139 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 8 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 8 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion | 184,900 | 1.00 | 1.00 | 25,720.0 | 0.139 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 8 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 16 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 346,251.7 | 0.624 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 16 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 477,792.2 | 1.551 | weight_read | 1.38x |
| MiMo-V2.6-Pro | 16 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 25,720.0 | 0.139 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 16 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 16 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.16 | 34,760.2 | 0.376 | layer_fixed_latency | 0.10x |
| MiMo-V2.6-Pro | 16 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 32 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 346,251.7 | 0.624 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 32 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 477,792.2 | 1.551 | weight_read | 1.38x |
| MiMo-V2.6-Pro | 32 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 25,720.0 | 0.139 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 32 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 32 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.16 | 54,996.9 | 0.595 | weight_read | 0.16x |
| MiMo-V2.6-Pro | 32 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 64 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 346,251.7 | 0.624 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 64 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 477,792.2 | 1.551 | weight_read | 1.38x |
| MiMo-V2.6-Pro | 64 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 25,720.0 | 0.139 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 64 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 64 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 2.90 | 84,821.7 | 0.917 | weight_read | 0.24x |
| MiMo-V2.6-Pro | 64 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 92,789.9 | 0.502 | weight_read | 0.27x |
| MiMo-V2.6-Pro | 256 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 416,312.1 | 1.502 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 256 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill | 308,070 | 1.62 | 1.00 | 482,307.6 | 1.566 | compute | 1.16x |
| MiMo-V2.6-Pro | 256 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.13 | 25,763.1 | 0.139 | weight_read | 0.06x |
| MiMo-V2.6-Pro | 256 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.13 | 93,352.8 | 0.505 | weight_read | 0.22x |
| MiMo-V2.6-Pro | 256 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4-perregion | 184,900 | 1.00 | 2.99 | 109,827.8 | 0.594 | kv_read | 0.26x |
| MiMo-V2.6-Pro | 256 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x76-perregion-romfill | 61,940 | 1.15 | 3.57 | 118,387.8 | 1.911 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 1024 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378 | 308,070 | 1.00 | 1.00 | 748,729.7 | 2.430 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 637,172.1 | 2.068 | compute | 0.85x |
| MiMo-V2.6-Pro | 1024 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 4.51 | 26,021.7 | 0.141 | weight_read | 0.03x |
| MiMo-V2.6-Pro | 1024 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 4.51 | 96,841.1 | 0.524 | weight_read | 0.13x |
| MiMo-V2.6-Pro | 1024 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x66-perregion | 53,790 | 1.00 | 5.53 | 163,124.5 | 3.033 | kv_read | 0.22x |
| MiMo-V2.6-Pro | 1024 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x76-perregion-romfill | 61,940 | 1.15 | 5.21 | 185,415.4 | 2.993 | kv_read | 0.25x |
| MiMo-V2.6-Pro | 4096 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 1.00 | 1.00 | 944,443.2 | 3.066 | compute | 1.00x |
| MiMo-V2.6-Pro | 4096 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 679,219.8 | 2.205 | compute | 0.72x |
| MiMo-V2.6-Pro | 4096 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 18.04 | 26,087.1 | 0.141 | weight_read | 0.03x |
| MiMo-V2.6-Pro | 4096 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 18.04 | 97,752.7 | 0.529 | weight_read | 0.10x |
| MiMo-V2.6-Pro | 4096 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x66-perregion | 53,790 | 1.00 | 5.62 | 192,169.6 | 3.573 | kv_read | 0.20x |
| MiMo-V2.6-Pro | 4096 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x76-perregion-romfill | 61,940 | 1.15 | 5.21 | 221,080.0 | 3.569 | kv_read | 0.23x |

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
| MiMo-V2.6-Pro | 1 | 60 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 32 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 64 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 256 | 66 | 3.88 | 1.031 | 1.606 | 1.56x |
| MiMo-V2.6-Pro | 1024 | 66 | 15.52 | 1.160 | 2.860 | 2.47x |
| MiMo-V2.6-Pro | 4096 | 66 | 62.06 | 1.773 | 5.617 | 3.17x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Pro | 1 | 34 | 7.22 | 5.11 | 1.41x |
| MiMo-V2.6-Pro | 2 | 34 | 12.81 | 6.98 | 1.84x |
| MiMo-V2.6-Pro | 4 | 34 | 20.53 | 9.37 | 2.19x |
| MiMo-V2.6-Pro | 8 | 34 | 28.25 | 12.06 | 2.34x |
| MiMo-V2.6-Pro | 16 | 34 | 32.72 | 14.80 | 2.21x |
| MiMo-V2.6-Pro | 32 | 34 | 33.88 | 17.29 | 1.96x |
| MiMo-V2.6-Pro | 64 | 34 | 33.99 | 19.16 | 1.77x |
| MiMo-V2.6-Pro | 256 | 34 | 34.00 | 20.47 | 1.66x |
| MiMo-V2.6-Pro | 1024 | 34 | 34.00 | 20.49 | 1.66x |
| MiMo-V2.6-Pro | 1 | 56 | 7.52 | 5.76 | 1.31x |
| MiMo-V2.6-Pro | 2 | 56 | 13.90 | 8.00 | 1.74x |
| MiMo-V2.6-Pro | 4 | 56 | 23.97 | 11.25 | 2.13x |
| MiMo-V2.6-Pro | 8 | 56 | 36.84 | 15.03 | 2.45x |
| MiMo-V2.6-Pro | 16 | 56 | 48.26 | 19.16 | 2.52x |
| MiMo-V2.6-Pro | 32 | 56 | 54.12 | 23.13 | 2.34x |
| MiMo-V2.6-Pro | 64 | 56 | 55.67 | 26.26 | 2.12x |
| MiMo-V2.6-Pro | 256 | 56 | 55.94 | 28.52 | 1.96x |
| MiMo-V2.6-Pro | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| MiMo-V2.6-Pro | 4096 | 56 | 55.94 | 28.56 | 1.96x |
| MiMo-V2.6-Pro | 1 | 59 | 7.54 | 5.82 | 1.30x |
| MiMo-V2.6-Pro | 2 | 59 | 13.99 | 8.10 | 1.73x |
| MiMo-V2.6-Pro | 4 | 59 | 24.28 | 11.45 | 2.12x |
| MiMo-V2.6-Pro | 8 | 59 | 37.67 | 15.35 | 2.45x |
| MiMo-V2.6-Pro | 16 | 59 | 49.97 | 19.65 | 2.54x |
| MiMo-V2.6-Pro | 32 | 59 | 56.64 | 23.80 | 2.38x |
| MiMo-V2.6-Pro | 64 | 59 | 58.54 | 27.09 | 2.16x |
| MiMo-V2.6-Pro | 256 | 59 | 58.91 | 29.48 | 2.00x |
| MiMo-V2.6-Pro | 1024 | 59 | 58.92 | 29.52 | 2.00x |
| MiMo-V2.6-Pro | 4096 | 59 | 58.92 | 29.52 | 2.00x |
| MiMo-V2.6-Pro | 1 | 65 | 7.58 | 5.94 | 1.28x |
| MiMo-V2.6-Pro | 2 | 65 | 14.15 | 8.31 | 1.70x |
| MiMo-V2.6-Pro | 4 | 65 | 24.81 | 11.82 | 2.10x |
| MiMo-V2.6-Pro | 8 | 65 | 39.17 | 15.96 | 2.45x |
| MiMo-V2.6-Pro | 16 | 65 | 53.16 | 20.57 | 2.58x |
| MiMo-V2.6-Pro | 32 | 65 | 61.49 | 25.07 | 2.45x |
| MiMo-V2.6-Pro | 64 | 65 | 64.21 | 28.68 | 2.24x |
| MiMo-V2.6-Pro | 256 | 65 | 64.83 | 31.31 | 2.07x |
| MiMo-V2.6-Pro | 1024 | 65 | 64.83 | 31.35 | 2.07x |
| MiMo-V2.6-Pro | 4096 | 65 | 64.83 | 31.35 | 2.07x |
| MiMo-V2.6-Pro | 1 | 75 | 7.64 | 6.12 | 1.25x |
| MiMo-V2.6-Pro | 2 | 75 | 14.36 | 8.62 | 1.67x |
| MiMo-V2.6-Pro | 4 | 75 | 25.54 | 12.37 | 2.06x |
| MiMo-V2.6-Pro | 8 | 75 | 41.27 | 16.85 | 2.45x |
| MiMo-V2.6-Pro | 16 | 75 | 57.83 | 21.96 | 2.63x |
| MiMo-V2.6-Pro | 32 | 75 | 69.01 | 27.01 | 2.55x |
| MiMo-V2.6-Pro | 64 | 75 | 73.35 | 31.12 | 2.36x |
| MiMo-V2.6-Pro | 256 | 75 | 74.56 | 34.15 | 2.18x |
| MiMo-V2.6-Pro | 1024 | 75 | 74.57 | 34.20 | 2.18x |
| MiMo-V2.6-Pro | 4096 | 75 | 74.57 | 34.20 | 2.18x |
| MiMo-V2.6-Pro | 1 | 112 | 7.75 | 6.57 | 1.18x |
| MiMo-V2.6-Pro | 2 | 112 | 14.83 | 9.53 | 1.56x |
| MiMo-V2.6-Pro | 4 | 112 | 27.20 | 13.79 | 1.97x |
| MiMo-V2.6-Pro | 8 | 112 | 46.33 | 19.40 | 2.39x |
| MiMo-V2.6-Pro | 16 | 112 | 70.17 | 26.03 | 2.70x |
| MiMo-V2.6-Pro | 32 | 112 | 91.30 | 32.86 | 2.78x |
| MiMo-V2.6-Pro | 64 | 112 | 103.24 | 38.61 | 2.67x |
| MiMo-V2.6-Pro | 256 | 112 | 108.37 | 42.96 | 2.52x |
| MiMo-V2.6-Pro | 1024 | 112 | 108.42 | 43.03 | 2.52x |
| MiMo-V2.6-Pro | 4096 | 112 | 108.42 | 43.03 | 2.52x |
| MiMo-V2.6-Pro | 1 | 120 | 7.77 | 6.64 | 1.17x |
| MiMo-V2.6-Pro | 2 | 120 | 14.89 | 9.70 | 1.54x |
| MiMo-V2.6-Pro | 4 | 120 | 27.43 | 14.02 | 1.96x |
| MiMo-V2.6-Pro | 8 | 120 | 47.08 | 19.86 | 2.37x |
| MiMo-V2.6-Pro | 16 | 120 | 72.13 | 26.76 | 2.70x |
| MiMo-V2.6-Pro | 32 | 120 | 95.16 | 33.91 | 2.81x |
| MiMo-V2.6-Pro | 64 | 120 | 108.87 | 39.99 | 2.72x |
| MiMo-V2.6-Pro | 256 | 120 | 115.10 | 44.60 | 2.58x |
| MiMo-V2.6-Pro | 1024 | 120 | 115.17 | 44.68 | 2.58x |
| MiMo-V2.6-Pro | 4096 | 120 | 115.17 | 44.68 | 2.58x |
| MiMo-V2.6-Pro | 1 | 124 | 7.78 | 6.67 | 1.17x |
| MiMo-V2.6-Pro | 2 | 124 | 14.92 | 9.78 | 1.53x |
| MiMo-V2.6-Pro | 4 | 124 | 27.54 | 14.13 | 1.95x |
| MiMo-V2.6-Pro | 8 | 124 | 47.42 | 20.08 | 2.36x |
| MiMo-V2.6-Pro | 16 | 124 | 73.04 | 27.11 | 2.69x |
| MiMo-V2.6-Pro | 32 | 124 | 96.99 | 34.42 | 2.82x |
| MiMo-V2.6-Pro | 64 | 124 | 111.58 | 40.65 | 2.74x |
| MiMo-V2.6-Pro | 256 | 124 | 118.39 | 45.40 | 2.61x |
| MiMo-V2.6-Pro | 1024 | 124 | 118.47 | 45.47 | 2.61x |
| MiMo-V2.6-Pro | 4096 | 124 | 118.47 | 45.47 | 2.61x |
| MiMo-V2.6-Pro | 1 | 130 | 7.79 | 6.71 | 1.16x |
| MiMo-V2.6-Pro | 2 | 130 | 14.96 | 9.90 | 1.51x |
| MiMo-V2.6-Pro | 4 | 130 | 27.69 | 14.28 | 1.94x |
| MiMo-V2.6-Pro | 8 | 130 | 47.90 | 20.40 | 2.35x |
| MiMo-V2.6-Pro | 16 | 130 | 74.33 | 27.63 | 2.69x |
| MiMo-V2.6-Pro | 32 | 130 | 99.61 | 35.16 | 2.83x |
| MiMo-V2.6-Pro | 64 | 130 | 115.52 | 41.61 | 2.78x |
| MiMo-V2.6-Pro | 256 | 130 | 123.21 | 46.55 | 2.65x |
| MiMo-V2.6-Pro | 1024 | 130 | 123.30 | 46.63 | 2.64x |
| MiMo-V2.6-Pro | 4096 | 130 | 123.30 | 46.63 | 2.64x |
| MiMo-V2.6-Pro | 1 | 133 | 7.79 | 6.74 | 1.16x |
| MiMo-V2.6-Pro | 2 | 133 | 14.98 | 9.95 | 1.51x |
| MiMo-V2.6-Pro | 4 | 133 | 27.76 | 14.35 | 1.93x |
| MiMo-V2.6-Pro | 8 | 133 | 48.13 | 20.55 | 2.34x |
| MiMo-V2.6-Pro | 16 | 133 | 74.94 | 27.87 | 2.69x |
| MiMo-V2.6-Pro | 32 | 133 | 100.87 | 35.52 | 2.84x |
| MiMo-V2.6-Pro | 64 | 133 | 117.43 | 42.08 | 2.79x |
| MiMo-V2.6-Pro | 256 | 133 | 125.57 | 47.11 | 2.67x |
| MiMo-V2.6-Pro | 1024 | 133 | 125.67 | 47.19 | 2.66x |
| MiMo-V2.6-Pro | 4096 | 133 | 125.67 | 47.19 | 2.66x |
| MiMo-V2.6-Pro | 1 | 134 | 7.79 | 6.74 | 1.16x |
| MiMo-V2.6-Pro | 2 | 134 | 14.99 | 9.97 | 1.50x |
| MiMo-V2.6-Pro | 4 | 134 | 27.78 | 14.38 | 1.93x |
| MiMo-V2.6-Pro | 8 | 134 | 48.20 | 20.61 | 2.34x |
| MiMo-V2.6-Pro | 16 | 134 | 75.14 | 27.96 | 2.69x |
| MiMo-V2.6-Pro | 32 | 134 | 101.28 | 35.64 | 2.84x |
| MiMo-V2.6-Pro | 64 | 134 | 118.06 | 42.24 | 2.80x |
| MiMo-V2.6-Pro | 256 | 134 | 126.35 | 47.30 | 2.67x |
| MiMo-V2.6-Pro | 1024 | 134 | 126.45 | 47.38 | 2.67x |
| MiMo-V2.6-Pro | 4096 | 134 | 126.45 | 47.38 | 2.67x |
| MiMo-V2.6-Pro | 1 | 137 | 7.80 | 6.76 | 1.15x |
| MiMo-V2.6-Pro | 2 | 137 | 15.00 | 10.02 | 1.50x |
| MiMo-V2.6-Pro | 4 | 137 | 27.84 | 14.45 | 1.93x |
| MiMo-V2.6-Pro | 8 | 137 | 48.42 | 20.76 | 2.33x |
| MiMo-V2.6-Pro | 16 | 137 | 75.72 | 28.20 | 2.69x |
| MiMo-V2.6-Pro | 32 | 137 | 102.50 | 35.99 | 2.85x |
| MiMo-V2.6-Pro | 64 | 137 | 119.92 | 42.70 | 2.81x |
| MiMo-V2.6-Pro | 256 | 137 | 128.67 | 47.85 | 2.69x |
| MiMo-V2.6-Pro | 1024 | 137 | 128.78 | 47.93 | 2.69x |
| MiMo-V2.6-Pro | 4096 | 137 | 128.78 | 47.93 | 2.69x |
| MiMo-V2.6-Pro | 1 | 145 | 7.81 | 6.82 | 1.15x |
| MiMo-V2.6-Pro | 2 | 145 | 15.05 | 10.17 | 1.48x |
| MiMo-V2.6-Pro | 4 | 145 | 28.01 | 14.63 | 1.91x |
| MiMo-V2.6-Pro | 8 | 145 | 48.96 | 21.15 | 2.31x |
| MiMo-V2.6-Pro | 16 | 145 | 77.19 | 28.82 | 2.68x |
| MiMo-V2.6-Pro | 32 | 145 | 105.59 | 36.90 | 2.86x |
| MiMo-V2.6-Pro | 64 | 145 | 124.71 | 43.89 | 2.84x |
| MiMo-V2.6-Pro | 256 | 145 | 134.71 | 49.28 | 2.73x |
| MiMo-V2.6-Pro | 1024 | 145 | 134.83 | 49.36 | 2.73x |
| MiMo-V2.6-Pro | 4096 | 145 | 134.83 | 49.36 | 2.73x |
| MiMo-V2.6-Pro | 1 | 156 | 7.82 | 6.88 | 1.14x |
| MiMo-V2.6-Pro | 2 | 156 | 15.10 | 10.35 | 1.46x |
| MiMo-V2.6-Pro | 4 | 156 | 28.21 | 14.86 | 1.90x |
| MiMo-V2.6-Pro | 8 | 156 | 49.61 | 21.67 | 2.29x |
| MiMo-V2.6-Pro | 16 | 156 | 79.01 | 29.62 | 2.67x |
| MiMo-V2.6-Pro | 32 | 156 | 109.50 | 38.08 | 2.88x |
| MiMo-V2.6-Pro | 64 | 156 | 130.92 | 45.45 | 2.88x |
| MiMo-V2.6-Pro | 256 | 156 | 142.65 | 51.15 | 2.79x |
| MiMo-V2.6-Pro | 1024 | 156 | 142.80 | 51.24 | 2.79x |
| MiMo-V2.6-Pro | 4096 | 156 | 142.80 | 51.24 | 2.79x |
| MiMo-V2.6-Pro | 1 | 168 | 7.84 | 6.95 | 1.13x |
| MiMo-V2.6-Pro | 2 | 168 | 15.15 | 10.53 | 1.44x |
| MiMo-V2.6-Pro | 4 | 168 | 28.40 | 15.10 | 1.88x |
| MiMo-V2.6-Pro | 8 | 168 | 50.25 | 22.20 | 2.26x |
| MiMo-V2.6-Pro | 16 | 168 | 80.79 | 30.42 | 2.66x |
| MiMo-V2.6-Pro | 32 | 168 | 113.39 | 39.29 | 2.89x |
| MiMo-V2.6-Pro | 64 | 168 | 137.21 | 47.05 | 2.92x |
| MiMo-V2.6-Pro | 256 | 168 | 150.85 | 53.09 | 2.84x |
| MiMo-V2.6-Pro | 1024 | 168 | 151.03 | 53.19 | 2.84x |
| MiMo-V2.6-Pro | 4096 | 168 | 151.03 | 53.19 | 2.84x |
| MiMo-V2.6-Pro | 1 | 173 | 7.84 | 6.97 | 1.12x |
| MiMo-V2.6-Pro | 2 | 173 | 15.17 | 10.61 | 1.43x |
| MiMo-V2.6-Pro | 4 | 173 | 28.47 | 15.19 | 1.87x |
| MiMo-V2.6-Pro | 8 | 173 | 50.49 | 22.41 | 2.25x |
| MiMo-V2.6-Pro | 16 | 173 | 81.47 | 30.74 | 2.65x |
| MiMo-V2.6-Pro | 32 | 173 | 114.90 | 39.77 | 2.89x |
| MiMo-V2.6-Pro | 64 | 173 | 139.69 | 47.69 | 2.93x |
| MiMo-V2.6-Pro | 256 | 173 | 154.13 | 53.87 | 2.86x |
| MiMo-V2.6-Pro | 1024 | 173 | 154.32 | 53.96 | 2.86x |
| MiMo-V2.6-Pro | 4096 | 173 | 154.32 | 53.96 | 2.86x |
| MiMo-V2.6-Pro | 1 | 174 | 7.84 | 6.97 | 1.12x |
| MiMo-V2.6-Pro | 2 | 174 | 15.18 | 10.62 | 1.43x |
| MiMo-V2.6-Pro | 4 | 174 | 28.48 | 15.21 | 1.87x |
| MiMo-V2.6-Pro | 8 | 174 | 50.53 | 22.45 | 2.25x |
| MiMo-V2.6-Pro | 16 | 174 | 81.60 | 30.80 | 2.65x |
| MiMo-V2.6-Pro | 32 | 174 | 115.20 | 39.86 | 2.89x |
| MiMo-V2.6-Pro | 64 | 174 | 140.18 | 47.82 | 2.93x |
| MiMo-V2.6-Pro | 256 | 174 | 154.78 | 54.02 | 2.87x |
| MiMo-V2.6-Pro | 1024 | 174 | 154.97 | 54.12 | 2.86x |
| MiMo-V2.6-Pro | 4096 | 174 | 154.97 | 54.12 | 2.86x |
| MiMo-V2.6-Pro | 1 | 186 | 7.85 | 7.03 | 1.12x |
| MiMo-V2.6-Pro | 2 | 186 | 15.22 | 10.79 | 1.41x |
| MiMo-V2.6-Pro | 4 | 186 | 28.64 | 15.42 | 1.86x |
| MiMo-V2.6-Pro | 8 | 186 | 51.05 | 22.92 | 2.23x |
| MiMo-V2.6-Pro | 16 | 186 | 83.10 | 31.51 | 2.64x |
| MiMo-V2.6-Pro | 32 | 186 | 118.57 | 40.95 | 2.90x |
| MiMo-V2.6-Pro | 64 | 186 | 145.81 | 49.28 | 2.96x |
| MiMo-V2.6-Pro | 256 | 186 | 162.31 | 55.80 | 2.91x |
| MiMo-V2.6-Pro | 1024 | 186 | 162.53 | 55.91 | 2.91x |
| MiMo-V2.6-Pro | 4096 | 186 | 162.53 | 55.91 | 2.91x |
| MiMo-V2.6-Pro | 1 | 201 | 7.86 | 7.09 | 1.11x |
| MiMo-V2.6-Pro | 2 | 201 | 15.26 | 10.99 | 1.39x |
| MiMo-V2.6-Pro | 4 | 201 | 28.81 | 15.68 | 1.84x |
| MiMo-V2.6-Pro | 8 | 201 | 51.63 | 23.47 | 2.20x |
| MiMo-V2.6-Pro | 16 | 201 | 84.77 | 32.33 | 2.62x |
| MiMo-V2.6-Pro | 32 | 201 | 122.39 | 42.22 | 2.90x |
| MiMo-V2.6-Pro | 64 | 201 | 152.29 | 51.01 | 2.99x |
| MiMo-V2.6-Pro | 256 | 201 | 171.13 | 57.91 | 2.95x |
| MiMo-V2.6-Pro | 1024 | 201 | 171.39 | 58.02 | 2.95x |
| MiMo-V2.6-Pro | 4096 | 201 | 171.39 | 58.02 | 2.95x |
| MiMo-V2.6-Pro | 1 | 207 | 7.87 | 7.11 | 1.11x |
| MiMo-V2.6-Pro | 2 | 207 | 15.28 | 11.06 | 1.38x |
| MiMo-V2.6-Pro | 4 | 207 | 28.87 | 15.77 | 1.83x |
| MiMo-V2.6-Pro | 8 | 207 | 51.84 | 23.67 | 2.19x |
| MiMo-V2.6-Pro | 16 | 207 | 85.38 | 32.64 | 2.62x |
| MiMo-V2.6-Pro | 32 | 207 | 123.81 | 42.71 | 2.90x |
| MiMo-V2.6-Pro | 64 | 207 | 154.73 | 51.67 | 2.99x |
| MiMo-V2.6-Pro | 256 | 207 | 174.49 | 58.73 | 2.97x |
| MiMo-V2.6-Pro | 1024 | 207 | 174.76 | 58.84 | 2.97x |
| MiMo-V2.6-Pro | 4096 | 207 | 174.76 | 58.84 | 2.97x |
| MiMo-V2.6-Pro | 1 | 208 | 7.87 | 7.11 | 1.11x |
| MiMo-V2.6-Pro | 2 | 208 | 15.28 | 11.07 | 1.38x |
| MiMo-V2.6-Pro | 4 | 208 | 28.88 | 15.79 | 1.83x |
| MiMo-V2.6-Pro | 8 | 208 | 51.87 | 23.70 | 2.19x |
| MiMo-V2.6-Pro | 16 | 208 | 85.48 | 32.69 | 2.61x |
| MiMo-V2.6-Pro | 32 | 208 | 124.04 | 42.78 | 2.90x |
| MiMo-V2.6-Pro | 64 | 208 | 155.13 | 51.77 | 3.00x |
| MiMo-V2.6-Pro | 256 | 208 | 175.04 | 58.86 | 2.97x |
| MiMo-V2.6-Pro | 1024 | 208 | 175.31 | 58.97 | 2.97x |
| MiMo-V2.6-Pro | 4096 | 208 | 175.31 | 58.97 | 2.97x |
| MiMo-V2.6-Pro | 1 | 224 | 7.88 | 7.17 | 1.10x |
| MiMo-V2.6-Pro | 2 | 224 | 15.32 | 11.26 | 1.36x |
| MiMo-V2.6-Pro | 4 | 224 | 29.02 | 16.04 | 1.81x |
| MiMo-V2.6-Pro | 8 | 224 | 52.37 | 24.21 | 2.16x |
| MiMo-V2.6-Pro | 16 | 224 | 86.96 | 33.46 | 2.60x |
| MiMo-V2.6-Pro | 32 | 224 | 127.51 | 44.02 | 2.90x |
| MiMo-V2.6-Pro | 64 | 224 | 161.19 | 53.46 | 3.02x |
| MiMo-V2.6-Pro | 256 | 224 | 183.50 | 60.94 | 3.01x |
| MiMo-V2.6-Pro | 1024 | 224 | 183.81 | 61.05 | 3.01x |
| MiMo-V2.6-Pro | 4096 | 224 | 183.81 | 61.05 | 3.01x |
| MiMo-V2.6-Pro | 1 | 231 | 7.88 | 7.19 | 1.10x |
| MiMo-V2.6-Pro | 2 | 231 | 15.33 | 11.34 | 1.35x |
| MiMo-V2.6-Pro | 4 | 231 | 29.08 | 16.14 | 1.80x |
| MiMo-V2.6-Pro | 8 | 231 | 52.57 | 24.42 | 2.15x |
| MiMo-V2.6-Pro | 16 | 231 | 87.55 | 33.78 | 2.59x |
| MiMo-V2.6-Pro | 32 | 231 | 128.92 | 44.54 | 2.89x |
| MiMo-V2.6-Pro | 64 | 231 | 163.68 | 54.17 | 3.02x |
| MiMo-V2.6-Pro | 256 | 231 | 187.01 | 61.81 | 3.03x |
| MiMo-V2.6-Pro | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| MiMo-V2.6-Pro | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| MiMo-V2.6-Pro | 1 | 249 | 7.89 | 7.24 | 1.09x |
| MiMo-V2.6-Pro | 2 | 249 | 15.37 | 11.52 | 1.33x |
| MiMo-V2.6-Pro | 4 | 249 | 29.22 | 16.41 | 1.78x |
| MiMo-V2.6-Pro | 8 | 249 | 53.04 | 24.91 | 2.13x |
| MiMo-V2.6-Pro | 16 | 249 | 88.94 | 34.57 | 2.57x |
| MiMo-V2.6-Pro | 32 | 249 | 132.26 | 45.83 | 2.89x |
| MiMo-V2.6-Pro | 64 | 249 | 169.65 | 55.93 | 3.03x |
| MiMo-V2.6-Pro | 256 | 249 | 195.52 | 63.96 | 3.06x |
| MiMo-V2.6-Pro | 1024 | 249 | 195.90 | 64.09 | 3.06x |
| MiMo-V2.6-Pro | 4096 | 249 | 195.90 | 64.09 | 3.06x |
| MiMo-V2.6-Pro | 1 | 280 | 7.90 | 7.31 | 1.08x |
| MiMo-V2.6-Pro | 2 | 280 | 15.42 | 11.81 | 1.31x |
| MiMo-V2.6-Pro | 4 | 280 | 29.41 | 16.83 | 1.75x |
| MiMo-V2.6-Pro | 8 | 280 | 53.71 | 25.64 | 2.09x |
| MiMo-V2.6-Pro | 16 | 280 | 90.98 | 35.83 | 2.54x |
| MiMo-V2.6-Pro | 32 | 280 | 137.22 | 47.90 | 2.86x |
| MiMo-V2.6-Pro | 64 | 280 | 178.71 | 58.73 | 3.04x |
| MiMo-V2.6-Pro | 256 | 280 | 208.68 | 67.35 | 3.10x |
| MiMo-V2.6-Pro | 1024 | 280 | 209.13 | 67.50 | 3.10x |
| MiMo-V2.6-Pro | 4096 | 280 | 209.13 | 67.50 | 3.10x |
| MiMo-V2.6-Pro | 1 | 335 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Pro | 2 | 335 | 15.49 | 12.24 | 1.27x |
| MiMo-V2.6-Pro | 4 | 335 | 29.66 | 17.53 | 1.69x |
| MiMo-V2.6-Pro | 8 | 335 | 54.61 | 26.66 | 2.05x |
| MiMo-V2.6-Pro | 16 | 335 | 93.75 | 37.88 | 2.48x |
| MiMo-V2.6-Pro | 32 | 335 | 144.17 | 51.16 | 2.82x |
| MiMo-V2.6-Pro | 64 | 335 | 191.76 | 62.99 | 3.04x |
| MiMo-V2.6-Pro | 256 | 335 | 228.15 | 72.67 | 3.14x |
| MiMo-V2.6-Pro | 1024 | 335 | 228.71 | 72.82 | 3.14x |
| MiMo-V2.6-Pro | 4096 | 335 | 228.71 | 72.82 | 3.14x |
| MiMo-V2.6-Pro | 1 | 336 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Pro | 2 | 336 | 15.49 | 12.24 | 1.26x |
| MiMo-V2.6-Pro | 4 | 336 | 29.67 | 17.54 | 1.69x |
| MiMo-V2.6-Pro | 8 | 336 | 54.62 | 26.67 | 2.05x |
| MiMo-V2.6-Pro | 16 | 336 | 93.80 | 37.91 | 2.47x |
| MiMo-V2.6-Pro | 32 | 336 | 144.27 | 51.21 | 2.82x |
| MiMo-V2.6-Pro | 64 | 336 | 191.97 | 63.06 | 3.04x |
| MiMo-V2.6-Pro | 256 | 336 | 228.47 | 72.76 | 3.14x |
| MiMo-V2.6-Pro | 1024 | 336 | 229.03 | 72.91 | 3.14x |
| MiMo-V2.6-Pro | 4096 | 336 | 229.03 | 72.91 | 3.14x |
| MiMo-V2.6-Pro | 1 | 346 | 7.92 | 7.43 | 1.07x |
| MiMo-V2.6-Pro | 2 | 346 | 15.50 | 12.31 | 1.26x |
| MiMo-V2.6-Pro | 4 | 346 | 29.71 | 17.66 | 1.68x |
| MiMo-V2.6-Pro | 8 | 346 | 54.76 | 26.83 | 2.04x |
| MiMo-V2.6-Pro | 16 | 346 | 94.21 | 38.26 | 2.46x |
| MiMo-V2.6-Pro | 32 | 346 | 145.34 | 51.74 | 2.81x |
| MiMo-V2.6-Pro | 64 | 346 | 194.00 | 63.75 | 3.04x |
| MiMo-V2.6-Pro | 256 | 346 | 231.56 | 73.65 | 3.14x |
| MiMo-V2.6-Pro | 1024 | 346 | 232.14 | 73.81 | 3.14x |
| MiMo-V2.6-Pro | 4096 | 346 | 232.14 | 73.81 | 3.14x |
| MiMo-V2.6-Pro | 1 | 373 | 7.93 | 7.47 | 1.06x |
| MiMo-V2.6-Pro | 2 | 373 | 15.52 | 12.48 | 1.24x |
| MiMo-V2.6-Pro | 4 | 373 | 29.80 | 17.97 | 1.66x |
| MiMo-V2.6-Pro | 8 | 373 | 55.08 | 27.22 | 2.02x |
| MiMo-V2.6-Pro | 16 | 373 | 95.24 | 39.18 | 2.43x |
| MiMo-V2.6-Pro | 32 | 373 | 147.96 | 53.07 | 2.79x |
| MiMo-V2.6-Pro | 64 | 373 | 199.07 | 65.53 | 3.04x |
| MiMo-V2.6-Pro | 256 | 373 | 239.33 | 75.99 | 3.15x |
| MiMo-V2.6-Pro | 1024 | 373 | 239.95 | 76.15 | 3.15x |
| MiMo-V2.6-Pro | 4096 | 373 | 239.95 | 76.15 | 3.15x |
| MiMo-V2.6-Pro | 1 | 448 | 7.94 | 7.55 | 1.05x |
| MiMo-V2.6-Pro | 2 | 448 | 15.57 | 12.88 | 1.21x |
| MiMo-V2.6-Pro | 4 | 448 | 30.00 | 18.77 | 1.60x |
| MiMo-V2.6-Pro | 8 | 448 | 55.80 | 28.11 | 1.99x |
| MiMo-V2.6-Pro | 16 | 448 | 97.49 | 41.50 | 2.35x |
| MiMo-V2.6-Pro | 32 | 448 | 153.83 | 56.17 | 2.74x |
| MiMo-V2.6-Pro | 64 | 448 | 210.61 | 70.02 | 3.01x |
| MiMo-V2.6-Pro | 256 | 448 | 257.32 | 81.76 | 3.15x |
| MiMo-V2.6-Pro | 1024 | 448 | 258.06 | 81.95 | 3.15x |
| MiMo-V2.6-Pro | 4096 | 448 | 258.06 | 81.95 | 3.15x |
| MiMo-V2.6-Pro | 1 | 672 | 7.96 | 7.69 | 1.03x |
| MiMo-V2.6-Pro | 2 | 672 | 15.66 | 13.65 | 1.15x |
| MiMo-V2.6-Pro | 4 | 672 | 30.33 | 20.68 | 1.47x |
| MiMo-V2.6-Pro | 8 | 672 | 57.00 | 30.02 | 1.90x |
| MiMo-V2.6-Pro | 16 | 672 | 101.38 | 46.51 | 2.18x |
| MiMo-V2.6-Pro | 32 | 672 | 164.27 | 62.86 | 2.61x |
| MiMo-V2.6-Pro | 64 | 672 | 231.89 | 80.75 | 2.87x |
| MiMo-V2.6-Pro | 256 | 672 | 291.68 | 94.44 | 3.09x |
| MiMo-V2.6-Pro | 1024 | 672 | 292.67 | 94.67 | 3.09x |
| MiMo-V2.6-Pro | 4096 | 672 | 292.67 | 94.67 | 3.09x |

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
| gpu | MiMo-V2.6-Pro | 1 | 472.25 | 13.6% |
| rom | MiMo-V2.6-Pro | 1 | 158.58 | 57.7% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| MiMo-V2.6-Pro | sram | interleaved | 128 B | 1.00x |
| MiMo-V2.6-Pro | hbm | interleaved | 32 B | 1.00x |

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
| MiMo-V2.6-Pro | 1 | 60 | 58.58% | 326.18 | 9.28 |
| MiMo-V2.6-Pro | 2 | 2 | 0.54% | 5.73 | 9.28 |
| MiMo-V2.6-Pro | 4 | 2 | 0.54% | 5.73 | 9.28 |
| MiMo-V2.6-Pro | 8 | 2 | 0.54% | 5.73 | 9.28 |
| MiMo-V2.6-Pro | 16 | 2 | 0.54% | 5.73 | 9.28 |
| MiMo-V2.6-Pro | 32 | 2 | 0.54% | 5.73 | 9.28 |
| MiMo-V2.6-Pro | 64 | 2 | 0.54% | 5.73 | 9.28 |

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
| MiMo-V2.6-Pro | 1 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 193.6 | 25,553.3 |
| MiMo-V2.6-Pro | 2 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 193.6 | 25,553.3 |
| MiMo-V2.6-Pro | 4 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 193.6 | 25,553.3 |
| MiMo-V2.6-Pro | 8 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 193.6 | 25,553.3 |
| MiMo-V2.6-Pro | 16 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 193.6 | 25,553.3 |
| MiMo-V2.6-Pro | 32 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 193.6 | 25,553.3 |
| MiMo-V2.6-Pro | 64 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 193.6 | 25,553.3 |
| MiMo-V2.6-Pro | 256 | 4.00% | 49.5 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 101.1 | 25,870.4 |
| MiMo-V2.6-Pro | 1024 | 15.07% | 108.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 25.5 | 26,130.8 |
| MiMo-V2.6-Pro | 4096 | 47.97% | 283.1 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 6.4 | 26,196.6 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 2 |
| gpu | infeasible | 1 |
| gpu | link_latency | 571 |
| gpu | weight_read | 666 |
| rom | compute | 566 |
| rom | infeasible | 1746 |
| rom | kv_read | 201 |
| rom | layer_fixed_latency | 373 |
| rom | link_latency | 1003 |
| rom | weight_read | 401 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 1 |
| rom | CAPACITY | 1746 |

## Mechanical consistency audit

**FAIL** over 119,063 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x122', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x126', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x135', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x139', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x147', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x176', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x234', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x351', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x122', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x126', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x135', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x139', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x147', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x176', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x234', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x351', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x122', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x126', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x135', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x139', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x147', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x176', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x234', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x351', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x122', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x126', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x135', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x139', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x147', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x176', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x234', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x351', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-tensor-x122', 'MiMo-V2.6-Pro', 1)

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

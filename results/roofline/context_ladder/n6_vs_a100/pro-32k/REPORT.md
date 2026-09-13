# Area-constrained roofline: n6_vs_a100-pro-32k

> CONTEXT-LADDER RUNG of n6_vs_a100: DeepSeek-V4-Pro-0813 at 32,768 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 382x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 4 devices. On the GPU side the correction reaches 596x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 168 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Pro-0813 takes 4 x 46,225 mm2 (184,900 mm2, wafer, KV in HBM) at 2,376 tok/s per user and 13 tok/s per 1,000 mm2, holding 7,489 sessions, against 224 copies of one unified HBM die at the same silicon: 6.6x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Pro-0813 on 184,900 mm2 of ROM silicon at 2,376 tok/s per user against 185,024 mm2 of a100_sxm_80gb-x224-tensor at 358 tok/s: **6.6x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 46,070. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 283.85x to it.** At 554,700 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 1.11 tok/s and the same silicon running tensor delivers 314 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.90x (DeepSeek-V4-Pro-0813, ROM binding on `link_latency`) to 112.32x (DeepSeek-V4-Pro-0813, ROM binding on `link_latency`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Pro-0813 engages 4.4% of its ROM array at batch 1 and 4.8% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 79 to 15,987 tok/s, and its rate with every slot occupied from 15,944 to 15,987. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 203 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,823 us over NVLink, capping per-user decode at 548 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 1,481.1 us and cap it at 675 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 8 of 8 operating points and an array 0; on tokens per second per square millimetre the same points go 0 to the array and 8 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 0 of 1260 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 16.6x of aggregate throughput (DeepSeek-V4-Pro-0813). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 7.56x, on DeepSeek-V4-Pro-0813 at batch 256, where the busiest region carries 2.85x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 16 of 16 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 68% of its cooling budget. The companion study at the other node does have power-limited points.


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

### DeepSeek-V4-Pro-0813 at 32,768 tokens

**Recommended: `ROM-N6-native-HBMKV-wafer-hybrid-x4`** -- 4 x 46,225 mm2 wafers, 184,900 mm2 total, `hybrid`-parallel, KV in HBM, spare silicon to `sram`.

- **2,375.7 tok/s per user** (0.42 ms/token), binding on `link_latency`
- **12.8 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 9,503 tok/s aggregate with every slot full, over 7,489 resident sessions (fill limited by `pipeline_slots`)
- 12,199 W at 0.066 W/mm2, 1,283.8 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 224 copies of one unified HBM die -- `a100_sxm_80gb-x224-tensor`, 185,024 mm2, area ratio 0.9993 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 184,900 | 185,024 | 0.9993 |
| user tok/s | 2,375.7 | 358.4 | 6.63x |
| aggregate tok/s | 9,503 | 358 | 26.51x |
| resident sessions | 7,489 | 46,070 | -- |
| J/token | 1.2838 | 94.4205 | 73.6x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 7,489 sessions against one that holds 46,070 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x293-tensor` at 242,018 mm2 and 362.9 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 12.8 | 1 | 6.63x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 12.8 | 1 | 6.63x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-tensor-x188` | 153,220 | 713.8 | 4.7 | 1 | 2.01x |
| **after -- this report's rule** | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 12.8 | 7,489 | 6.63x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-HBMKV-wafer-hybrid-x4` **<-- recommended** | 184,900 | 4 | 2,375.7 | 9,503 | 12.8 | 7,489 | `link_latency` | 12,199 | 1,283.8 | `a100_sxm_80gb-x224-tensor` | 6.63x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 84 | densest | `ROM-N6-native-SRAMKV-array-tensor-x191` | 155,665 | 725.9 | 4.7 | 1 |
| array | 84 | fastest | `ROM-N6-native-SRAMKV-array-tensor-x191` | 155,665 | 725.9 | 4.7 | 1 |
| array | 84 | smallest | `ROM-N6-native-SRAMKV-array-tensor-x188` | 153,220 | 713.8 | 4.7 | 1 |
| wafer | 48 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 12.8 | 1 |
| wafer | 48 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 12.8 | 1 |
| wafer | 48 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 12.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-tensor-x191` | 155,665 | 725.9 | 726 | 1 | 9,563 | 13,173.9 | `link_latency` | `a100_sxm_80gb-x188-tensor` | 354.9 | 38,232 | 80,678.4 | 1.002 | 2.05x | 6.1x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 2,376 | 1 | 11,474 | 4,829.5 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 358.4 | 46,070 | 94,420.5 | 0.999 | 6.63x | 19.6x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-tensor-x227` | 185,005 | 725.1 | 725 | 1 | 11,460 | 15,805.8 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 358.4 | 46,070 | 94,420.5 | 1.000 | 2.02x | 6.0x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | -- | 1 | -- | 4,829.5 | -- | -- | -- | -- | -- | 1.001 | 3.28x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-tensor-x227` | 185,005 | 626.1 | 1,252 | 49,423 | 14,670 | 11,715.1 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 307.6 | 46,070 | 55,343.0 | 1.000 | 2.04x | 4.7x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 9,503 | 7,489 | 12,199 | 1,283.8 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 307.6 | 46,070 | 55,343.0 | 0.999 | 7.72x | 43.1x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-tensor-x227` | 185,005 | 626.1 | 1,252 | 49,423 | 14,670 | 11,715.1 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 307.6 | 46,070 | 55,343.0 | 1.000 | 2.04x | 4.7x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | -- | 7,489 | -- | 1,283.8 | -- | -- | -- | -- | -- | 1.001 | 3.79x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hybrid-x206` | 167,890 | 581.5 | 15,119 | 44,851 | 12,296 | 813.3 | `compute` | `a100_sxm_80gb-x203-tensor` | 230.7 | 41,498 | 33,799.9 | 1.001 | 2.52x | 41.6x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | 9,503 | 7,489 | 12,199 | 1,283.8 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 233.9 | 46,070 | 36,613.6 | 0.999 | 10.16x | 28.5x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x227` | 185,005 | 547.5 | 15,879 | 49,423 | 15,093 | 950.5 | `weight_read` | `a100_sxm_80gb-x224-tensor` | 233.9 | 46,070 | 36,613.6 | 1.000 | 2.34x | 38.5x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,375.7 | -- | 7,489 | -- | 1,283.8 | -- | -- | -- | -- | -- | 1.001 | 4.34x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hybrid-x206` | 167,890 | 581.5 | 15,119 | 44,851 | 12,296 | 813.3 | `compute` | `a100_sxm_80gb-x203-tensor` | 170.1 | 41,498 | 23,189.6 | 1.001 | 3.42x | 28.5x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,374.1 | 18,993 | 7,489 | 12,391 | 652.4 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 172.0 | 46,070 | 25,153.9 | 0.999 | 13.80x | 38.6x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x227` | 185,005 | 547.5 | 15,879 | 49,423 | 15,093 | 950.5 | `weight_read` | `a100_sxm_80gb-x224-tensor` | 172.0 | 46,070 | 25,153.9 | 1.000 | 3.18x | 26.5x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,374.1 | -- | 7,489 | -- | 652.4 | -- | -- | -- | -- | -- | 1.001 | 4.34x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hybrid-x206` | 167,890 | 581.5 | 15,119 | 44,851 | 12,296 | 813.3 | `compute` | `a100_sxm_80gb-x203-tensor` | 116.4 | 41,498 | 17,138.5 | 1.001 | 5.00x | 21.1x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,370.9 | 37,934 | 7,489 | 12,771 | 336.7 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 118.0 | 46,070 | 18,523.1 | 0.999 | 20.09x | 55.0x |
| 16 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x227` | 185,005 | 547.5 | 15,879 | 49,423 | 15,093 | 950.5 | `weight_read` | `a100_sxm_80gb-x224-tensor` | 118.0 | 46,070 | 18,523.1 | 1.000 | 4.64x | 19.5x |
| 16 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,370.9 | -- | 7,489 | -- | 336.7 | -- | -- | -- | -- | -- | 1.001 | 4.33x wafer/array | -- |
| 32 | array | `ROM-N6-native-HBMKV-array-hybrid-x227` | 185,005 | 546.6 | 17,490 | 49,423 | 15,125 | 864.8 | `weight_read` | `a100_sxm_80gb-x224-tensor` | 76.1 | 46,070 | 14,450.2 | 1.000 | 7.18x | 16.7x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,016.9 | 64,540 | 7,489 | 13,287 | 205.9 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 76.1 | 46,070 | 14,450.2 | 0.999 | 26.49x | 70.2x |
| 32 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x227` | 185,005 | 546.6 | 17,490 | 49,423 | 15,125 | 864.8 | `weight_read` | `a100_sxm_80gb-x224-tensor` | 76.1 | 46,070 | 14,450.2 | 1.000 | 7.18x | 16.7x |
| 32 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 2,016.9 | -- | 7,489 | -- | 205.9 | -- | -- | -- | -- | -- | 1.001 | 3.69x wafer/array | -- |
| 64 | array | `ROM-N6-native-HBMKV-array-hybrid-x227` | 185,005 | 536.4 | 34,331 | 49,423 | 15,462 | 450.4 | `weight_read` | `a100_sxm_80gb-x224-tensor` | 46.5 | 46,070 | 11,776.6 | 1.000 | 11.52x | 26.1x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 1,951.9 | 124,920 | 11,234 | 28,162 | 225.4 | `link_latency` | `a100_sxm_80gb-x336-tensor` | 47.2 | 70,455 | 16,984.4 | 0.999 | 41.37x | 75.3x |
| 64 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x340` | 277,100 | 413.5 | 26,466 | 74,025 | 30,258 | 1,143.3 | `weight_read` | `a100_sxm_80gb-x335-tensor` | 47.2 | 70,237 | 16,941.2 | 1.001 | 8.77x | 14.8x |
| 64 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | 1,951.9 | -- | 11,234 | -- | 225.4 | -- | -- | -- | -- | -- | 0.999 | 4.72x wafer/array | -- |
| 256 | array | `ROM-N6-native-HBMKV-array-hybrid-x297` | 242,055 | 416.0 | 106,491 | 64,663 | 26,159 | 245.6 | `weight_read` | `a100_sxm_80gb-x293-tensor` | 15.5 | 61,093 | 11,035.4 | 1.000 | 26.87x | 44.9x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 1,758.1 | 450,076 | 22,469 | 60,597 | 134.6 | `link_latency` | `a100_sxm_80gb-x672-tensor` | 15.7 | 143,610 | 24,575.3 | 0.999 | 112.32x | 182.5x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-64 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | wafer | HBM | 7,489 |
| 256 | `ROM-N6-native-HBMKV-wafer-hybrid-x6` | 277,350 | wafer | HBM | 11,234 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Pro-0813 | HBM | rom | 203, 206, 227, 248, 297, 340, 396 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 203, 206, 227, 248, 297, 340, 396 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 188, 191, 227, 230, 276, 340, 368 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 188, 191, 227, 230, 276, 340, 368 |

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

- **0 of 1,260 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 68% of its cooling budget, and the busiest wafer-scale ROM design 26%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 24 | 0 | 58.4% | 68.1% | 0.330 | 62% |
| gpu | wafer (>=40,000 mm2) | 480 | 0 | 38.6% | 54.0% | 0.261 | 93% |
| rom | wafer (>=40,000 mm2) | 756 | 0 | 16.6% | 26.3% | 0.132 | 98% |

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
| DeepSeek-V4-Pro-0813 | 1 | 184,900 | `DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 4.829509 | 11,473.6 | link_latency | `DSV4-Pro/a100_sxm_80gb-x224-tensor` | 94.420501 | 33,843.1 | link_latency | 19.55x |
| DeepSeek-V4-Pro-0813 | 2 | 184,900 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4` | 1.283758 | 12,199.4 | link_latency | `DSV4-Pro/a100_sxm_80gb-x224-tensor` | 55.343010 | 34,044.6 | link_latency | 43.11x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4` | 1.283758 | 12,199.4 | link_latency | `DSV4-Pro/a100_sxm_80gb-x224-tensor` | 36.613639 | 34,252.5 | weight_read | 28.52x |
| DeepSeek-V4-Pro-0813 | 8 | 184,900 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4` | 0.652387 | 12,390.7 | link_latency | `DSV4-Pro/a100_sxm_80gb-x224-tensor` | 25.153894 | 34,611.7 | link_latency | 38.56x |
| DeepSeek-V4-Pro-0813 | 16 | 184,900 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4` | 0.336656 | 12,770.7 | link_latency | `DSV4-Pro/a100_sxm_80gb-x224-tensor` | 18.523125 | 34,981.5 | link_latency | 55.02x |
| DeepSeek-V4-Pro-0813 | 32 | 184,900 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4` | 0.205870 | 13,286.9 | link_latency | `DSV4-Pro/a100_sxm_80gb-x224-tensor` | 14.450225 | 35,206.1 | link_latency | 70.19x |
| DeepSeek-V4-Pro-0813 | 64 | 277,350 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6` | 0.225439 | 28,162.0 | link_latency | `DSV4-Pro/a100_sxm_80gb-x336-tensor` | 16.984386 | 51,291.2 | link_latency | 75.34x |
| DeepSeek-V4-Pro-0813 | 256 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.134638 | 60,597.1 | link_latency | `DSV4-Pro/a100_sxm_80gb-x672-tensor` | 24.575339 | 98,473.1 | link_latency | 182.53x |

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
| DeepSeek-V4-Pro-0813 | 32,768 | 1,600 B | 892.7 GB | 4.46 | 0.110 GB | 0.331 GB | 359.0 |

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
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 14,625.7 | wafer-pipeline | 2,375.7 | wafer-hybrid | 6.16x | 617.2 | pipeline | 358.4 | tensor | 1.72x | 23.70x | 6.63x | 0.28x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 14,625.7 | wafer-pipeline | 1,969.6 | wafer-hybrid | 7.43x | 637.4 | pipeline | 309.0 | tensor | 2.06x | 22.94x | 6.37x | 0.28x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 16,981.9 | wafer-pipeline | 1,928.3 | wafer-hybrid | 8.81x | 648.2 | pipeline | 311.4 | tensor | 2.08x | 26.20x | 6.19x | 0.24x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 20,291.8 | wafer-pipeline | 1,855.5 | wafer-hybrid | 10.94x | 659.3 | pipeline | 313.8 | tensor | 2.10x | 30.78x | 5.91x | 0.19x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.19x to 0.28x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x4 | 184,900 | 2,375.7 | 2,375.7 | link_latency | DSV4-Pro/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 1,323.01 | 358.4 | 358.4 | link_latency | 6.63x | 6.63x | 771.69x | 6.63x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x188 | 153,220 | 713.8 | 713.8 | link_latency | DSV4-Pro/a100_sxm_80gb-x185-tensor | 152,810 | 1.00x | tensor | 1,321.76 | 354.5 | 354.5 | weight_read | 2.01x | 2.01x | 195.76x | 2.01x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,375.7 | 9,502.9 | link_latency | DSV4-Pro/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 1,540.69 | 307.6 | 615.2 | link_latency | 7.72x | 15.45x | 771.69x | 7.72x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x203 | 165,445 | 594.9 | 1,189.8 | link_latency | DSV4-Pro/a100_sxm_80gb-x200-tensor | 165,200 | 1.00x | tensor | 1,538.90 | 303.9 | 607.7 | weight_read | 1.96x | 1.96x | 174.73x | 1.96x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,375.7 | 9,502.9 | link_latency | DSV4-Pro/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 1,976.07 | 233.9 | 935.5 | weight_read | 10.16x | 10.16x | 771.69x | 10.16x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x203 | 165,445 | 446.7 | 1,786.6 | link_latency | DSV4-Pro/a100_sxm_80gb-x200-tensor | 165,200 | 1.00x | tensor | 1,972.47 | 230.3 | 921.2 | weight_read | 1.94x | 1.94x | 131.18x | 1.94x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,374.1 | 18,992.9 | link_latency | DSV4-Pro/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 2,846.82 | 172.0 | 1,376.0 | link_latency | 13.80x | 13.80x | 771.16x | 13.80x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x203 | 165,445 | 431.6 | 11,222.3 | compute | DSV4-Pro/a100_sxm_80gb-x200-tensor | 165,200 | 1.00x | tensor | 2,839.62 | 169.8 | 1,358.7 | link_latency | 2.54x | 8.26x | 126.77x | 2.54x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,370.9 | 37,934.1 | link_latency | DSV4-Pro/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 4,588.31 | 118.0 | 1,888.5 | link_latency | 20.09x | 20.09x | 770.11x | 20.09x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x203 | 165,445 | 431.6 | 11,222.3 | compute | DSV4-Pro/a100_sxm_80gb-x200-tensor | 165,200 | 1.00x | tensor | 4,573.92 | 116.2 | 1,858.8 | link_latency | 3.72x | 6.04x | 126.77x | 3.72x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,016.9 | 64,540.1 | link_latency | DSV4-Pro/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 8,071.31 | 76.1 | 2,436.4 | link_latency | 26.49x | 26.49x | 655.13x | 26.49x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x203 | 165,445 | 371.1 | 11,874.1 | compute | DSV4-Pro/a100_sxm_80gb-x200-tensor | 165,200 | 1.00x | tensor | 8,042.52 | 75.0 | 2,399.9 | link_latency | 4.95x | 4.95x | 108.98x | 4.95x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1,951.9 | 124,920.5 | link_latency | DSV4-Pro/a100_sxm_80gb-x336-tensor | 277,536 | 1.00x | tensor | 15,692.52 | 47.2 | 3,019.9 | link_latency | 41.37x | 41.37x | 917.14x | 41.37x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x203 | 165,445 | 212.2 | 13,583.8 | compute | DSV4-Pro/a100_sxm_80gb-x200-tensor | 165,200 | 1.00x | tensor | 14,979.72 | 46.0 | 2,942.7 | link_latency | 4.62x | 4.62x | 62.34x | 4.62x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,758.1 | 450,075.7 | link_latency | DSV4-Pro/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 58,607.78 | 15.7 | 4,007.0 | link_latency | 112.32x | 112.32x | 1590.31x | 112.32x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x203 | 165,445 | 62.4 | 15,986.7 | compute | DSV4-Pro/a100_sxm_80gb-x200-tensor | 165,200 | 1.00x | tensor | 56,602.93 | 15.3 | 3,920.6 | link_latency | 4.08x | 4.08x | 19.14x | 4.08x |

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
| DeepSeek-V4-Pro-0813 | 14 | 11,564 | 21.3 | 217.8 | 136.2 | tensor | 1,225.56 | 26.7% | weight_read |
| DeepSeek-V4-Pro-0813 | 56 | 46,256 | 9.5 | 312.2 | 72.2 | tensor | 1,300.52 | 40.6% | weight_read |
| DeepSeek-V4-Pro-0813 | 112 | 92,512 | 5.6 | 341.0 | 43.3 | tensor | 1,315.51 | 44.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 168 | 138,768 | 4.0 | 352.3 | 31.1 | tensor | 1,320.51 | 46.5% | weight_read |
| DeepSeek-V4-Pro-0813 | 185 | 152,810 | 3.6 | 354.5 | 27.6 | tensor | 1,321.76 | 46.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 188 | 155,288 | 3.6 | 354.9 | 27.6 | tensor | 1,321.76 | 46.9% | weight_read |
| DeepSeek-V4-Pro-0813 | 200 | 165,200 | 3.4 | 356.2 | 26.7 | tensor | 1,322.11 | 47.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 203 | 167,678 | 3.4 | 356.5 | 25.8 | tensor | 1,322.43 | 47.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 224 | 185,024 | 3.1 | 358.4 | 24.2 | tensor | 1,323.01 | 47.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 227 | 187,502 | 3.0 | 358.7 | 23.4 | tensor | 1,323.27 | 47.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 245 | 202,370 | 2.8 | 360.0 | 22.1 | tensor | 1,323.73 | 47.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 272 | 224,672 | 2.6 | 361.8 | 20.4 | tensor | 1,324.33 | 47.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 293 | 242,018 | 2.4 | 362.9 | 18.9 | tensor | 1,324.83 | 48.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 335 | 276,710 | 2.1 | 309.0 | 16.8 | tensor | 1,820.83 | 56.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 336 | 277,536 | 2.1 | 309.0 | 16.8 | tensor | 1,820.83 | 56.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 363 | 299,838 | 2.0 | 309.7 | 15.5 | tensor | 1,821.26 | 56.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 371 | 306,446 | 1.9 | 309.9 | 15.2 | tensor | 1,821.36 | 56.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 391 | 322,966 | 1.8 | 310.3 | 14.6 | tensor | 1,821.54 | 56.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 392 | 323,792 | 1.8 | 310.3 | 14.6 | tensor | 1,821.54 | 56.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 448 | 370,048 | 1.6 | 311.4 | 12.9 | tensor | 1,822.07 | 56.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 672 | 555,072 | 1.1 | 313.8 | 8.8 | tensor | 1,823.32 | 57.2% | link_latency |

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
| DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x191 | DeepSeek-V4-Pro-0813 | 191 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x4 | DeepSeek-V4-Pro-0813 | 4 | pipeline | on_wafer | inter_wafer | 60 | 12.47 us | 8,018.9 tok/s | 80,188.6 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x188 | DeepSeek-V4-Pro-0813 | 188 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer | inter_wafer | 244 | 1,481.09 us | 67.5 tok/s | 675.2 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on inter_wafer (traversals 2.0) = 1,246.23 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x191 | DeepSeek-V4-Pro-0813 | 191 | hybrid | nvlink3 | infiniband_hdr | 145 | 685.18 us | 145.9 tok/s | 1,459.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 59.88 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x4 | DeepSeek-V4-Pro-0813 | 4 | hybrid | on_wafer | inter_wafer | 125 | 250.14 us | 399.8 tok/s | 3,997.8 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 3 x point_to_point span 2 on inter_wafer (traversals 1.0) = 15.29 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x206 | DeepSeek-V4-Pro-0813 | 206 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4 | DeepSeek-V4-Pro-0813 | 4 | pipeline | on_wafer | inter_wafer | 60 | 12.47 us | 8,018.9 tok/s | 80,188.6 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x203 | DeepSeek-V4-Pro-0813 | 203 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer | inter_wafer | 244 | 1,481.09 us | 67.5 tok/s | 675.2 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on inter_wafer (traversals 2.0) = 1,246.23 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x206 | DeepSeek-V4-Pro-0813 | 206 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | DeepSeek-V4-Pro-0813 | 4 | hybrid | on_wafer | inter_wafer | 125 | 250.14 us | 399.8 tok/s | 3,997.8 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 3 x point_to_point span 2 on inter_wafer (traversals 1.0) = 15.29 us |
| DSV4-Pro/a100_sxm_80gb-x14-pipeline | DeepSeek-V4-Pro-0813 | 14 | pipeline | nvlink3 | infiniband_hdr | 13 | 33.18 us | 3,014.1 tok/s | 30,141.5 tok/s | 12 x point_to_point span 2 on nvlink3 (traversals 1.0) = 30.57 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.60 us |
| DSV4-Pro/a100_sxm_80gb-x14-tensor | DeepSeek-V4-Pro-0813 | 14 | tensor | nvlink3 | infiniband_hdr | 244 | 1,225.56 us | 81.6 tok/s | 816.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 600.26 us |
| DSV4-Pro/a100_sxm_80gb-x14-hybrid | DeepSeek-V4-Pro-0813 | 14 | hybrid | nvlink3 | infiniband_hdr | 123 | 627.91 us | 159.3 tok/s | 1,592.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.60 us |
| DSV4-Pro/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 140.46 us | 711.9 tok/s | 7,119.4 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.84 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink3 | infiniband_hdr | 244 | 1,300.52 us | 76.9 tok/s | 768.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 675.22 us |
| DSV4-Pro/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink3 | infiniband_hdr | 128 | 640.92 us | 156.0 tok/s | 1,560.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Pro-0813 | 112 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink3 | infiniband_hdr | 244 | 1,315.51 us | 76.0 tok/s | 760.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 690.21 us |
| DSV4-Pro/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink3 | infiniband_hdr | 135 | 659.15 us | 151.7 tok/s | 1,517.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| DSV4-Pro/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Pro-0813 | 168 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Pro-0813 | 168 | tensor | nvlink3 | infiniband_hdr | 244 | 1,320.51 us | 75.7 tok/s | 757.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 695.20 us |
| DSV4-Pro/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Pro-0813 | 168 | hybrid | nvlink3 | infiniband_hdr | 142 | 677.37 us | 147.6 tok/s | 1,476.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.07 us |
| DSV4-Pro/a100_sxm_80gb-x185-pipeline | DeepSeek-V4-Pro-0813 | 185 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x185-tensor | DeepSeek-V4-Pro-0813 | 185 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/a100_sxm_80gb-x185-hybrid | DeepSeek-V4-Pro-0813 | 185 | hybrid | nvlink3 | infiniband_hdr | 145 | 685.18 us | 145.9 tok/s | 1,459.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 59.88 us |
| DSV4-Pro/a100_sxm_80gb-x188-pipeline | DeepSeek-V4-Pro-0813 | 188 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x188-tensor | DeepSeek-V4-Pro-0813 | 188 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/a100_sxm_80gb-x188-hybrid | DeepSeek-V4-Pro-0813 | 188 | hybrid | nvlink3 | infiniband_hdr | 145 | 685.18 us | 145.9 tok/s | 1,459.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 59.88 us |
| DSV4-Pro/a100_sxm_80gb-x200-pipeline | DeepSeek-V4-Pro-0813 | 200 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x200-tensor | DeepSeek-V4-Pro-0813 | 200 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.11 us | 75.6 tok/s | 756.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 696.80 us |
| DSV4-Pro/a100_sxm_80gb-x200-hybrid | DeepSeek-V4-Pro-0813 | 200 | hybrid | nvlink3 | infiniband_hdr | 146 | 687.79 us | 145.4 tok/s | 1,453.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 24 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 62.48 us |
| DSV4-Pro/a100_sxm_80gb-x203-pipeline | DeepSeek-V4-Pro-0813 | 203 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x203-tensor | DeepSeek-V4-Pro-0813 | 203 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x203-hybrid | DeepSeek-V4-Pro-0813 | 203 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Pro-0813 | 224 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Pro-0813 | 224 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.01 us | 75.6 tok/s | 755.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 697.70 us |
| DSV4-Pro/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Pro-0813 | 224 | hybrid | nvlink3 | infiniband_hdr | 149 | 695.60 us | 143.8 tok/s | 1,437.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| DSV4-Pro/a100_sxm_80gb-x227-pipeline | DeepSeek-V4-Pro-0813 | 227 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x227-tensor | DeepSeek-V4-Pro-0813 | 227 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.27 us | 75.6 tok/s | 755.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 697.96 us |
| DSV4-Pro/a100_sxm_80gb-x227-hybrid | DeepSeek-V4-Pro-0813 | 227 | hybrid | nvlink3 | infiniband_hdr | 150 | 698.20 us | 143.2 tok/s | 1,432.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 72.90 us |
| DSV4-Pro/a100_sxm_80gb-x245-pipeline | DeepSeek-V4-Pro-0813 | 245 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x245-tensor | DeepSeek-V4-Pro-0813 | 245 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.73 us | 75.5 tok/s | 755.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 698.43 us |
| DSV4-Pro/a100_sxm_80gb-x245-hybrid | DeepSeek-V4-Pro-0813 | 245 | hybrid | nvlink3 | infiniband_hdr | 152 | 703.41 us | 142.2 tok/s | 1,421.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 78.10 us |
| DSV4-Pro/a100_sxm_80gb-x272-pipeline | DeepSeek-V4-Pro-0813 | 272 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x272-tensor | DeepSeek-V4-Pro-0813 | 272 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.33 us | 75.5 tok/s | 755.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 34 on infiniband_hdr (traversals 2.0) = 699.03 us |
| DSV4-Pro/a100_sxm_80gb-x272-hybrid | DeepSeek-V4-Pro-0813 | 272 | hybrid | nvlink3 | infiniband_hdr | 155 | 711.22 us | 140.6 tok/s | 1,406.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 85.91 us |
| DSV4-Pro/a100_sxm_80gb-x293-pipeline | DeepSeek-V4-Pro-0813 | 293 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x293-tensor | DeepSeek-V4-Pro-0813 | 293 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.83 us | 75.5 tok/s | 754.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 37 on infiniband_hdr (traversals 2.0) = 699.53 us |
| DSV4-Pro/a100_sxm_80gb-x293-hybrid | DeepSeek-V4-Pro-0813 | 293 | hybrid | nvlink3 | infiniband_hdr | 158 | 719.03 us | 139.1 tok/s | 1,390.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 36 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 93.72 us |
| DSV4-Pro/a100_sxm_80gb-x335-pipeline | DeepSeek-V4-Pro-0813 | 335 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x335-tensor | DeepSeek-V4-Pro-0813 | 335 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x335-hybrid | DeepSeek-V4-Pro-0813 | 335 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Pro-0813 | 336 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Pro-0813 | 336 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Pro-0813 | 336 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x363-pipeline | DeepSeek-V4-Pro-0813 | 363 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x363-tensor | DeepSeek-V4-Pro-0813 | 363 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.26 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 46 on infiniband_hdr (traversals 4.0) = 1,195.96 us |
| DSV4-Pro/a100_sxm_80gb-x363-hybrid | DeepSeek-V4-Pro-0813 | 363 | hybrid | nvlink3 | infiniband_hdr | 167 | 742.46 us | 134.7 tok/s | 1,346.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 45 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 117.15 us |
| DSV4-Pro/a100_sxm_80gb-x371-pipeline | DeepSeek-V4-Pro-0813 | 371 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x371-tensor | DeepSeek-V4-Pro-0813 | 371 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.36 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 1,196.05 us |
| DSV4-Pro/a100_sxm_80gb-x371-hybrid | DeepSeek-V4-Pro-0813 | 371 | hybrid | nvlink3 | infiniband_hdr | 168 | 745.06 us | 134.2 tok/s | 1,342.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 46 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 119.76 us |
| DSV4-Pro/a100_sxm_80gb-x391-pipeline | DeepSeek-V4-Pro-0813 | 391 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x391-tensor | DeepSeek-V4-Pro-0813 | 391 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.54 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,196.24 us |
| DSV4-Pro/a100_sxm_80gb-x391-hybrid | DeepSeek-V4-Pro-0813 | 391 | hybrid | nvlink3 | infiniband_hdr | 170 | 750.27 us | 133.3 tok/s | 1,332.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| DSV4-Pro/a100_sxm_80gb-x392-pipeline | DeepSeek-V4-Pro-0813 | 392 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x392-tensor | DeepSeek-V4-Pro-0813 | 392 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.54 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,196.24 us |
| DSV4-Pro/a100_sxm_80gb-x392-hybrid | DeepSeek-V4-Pro-0813 | 392 | hybrid | nvlink3 | infiniband_hdr | 170 | 750.27 us | 133.3 tok/s | 1,332.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| DSV4-Pro/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Pro-0813 | 448 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Pro-0813 | 448 | tensor | nvlink3 | infiniband_hdr | 244 | 1,822.07 us | 54.9 tok/s | 548.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,196.77 us |
| DSV4-Pro/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Pro-0813 | 448 | hybrid | nvlink3 | infiniband_hdr | 177 | 768.49 us | 130.1 tok/s | 1,301.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 143.19 us |
| DSV4-Pro/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Pro-0813 | 672 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Pro-0813 | 672 | tensor | nvlink3 | infiniband_hdr | 244 | 1,823.32 us | 54.8 tok/s | 548.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,198.02 us |
| DSV4-Pro/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Pro-0813 | 672 | hybrid | nvlink3 | infiniband_hdr | 182 | 781.51 us | 128.0 tok/s | 1,279.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 156.21 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x4 | 184,900 | 2,375.7 | 0.013 | 713.8 (153,220) | 2,375.7 (184,900) | 3.33x | link_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,375.7 | 0.013 | 594.9 (165,445) | 2,375.7 (184,900) | 3.99x | link_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,375.7 | 0.013 | 581.5 (167,890) | 2,375.7 (184,900) | 4.09x | link_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,374.1 | 0.013 | 581.5 (167,890) | 2,374.1 (184,900) | 4.08x | link_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,370.9 | 0.013 | 581.5 (167,890) | 2,370.9 (184,900) | 4.08x | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 2,016.9 | 0.011 | 546.6 (185,005) | 2,016.9 (184,900) | 3.69x | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1,951.9 | 0.007 | 536.4 (185,005) | 1,951.9 (277,350) | 3.64x | link_latency |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,758.1 | 0.003 | 416.0 (242,055) | 1,758.1 (554,700) | 4.23x | link_latency |

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
| DeepSeek-V4-Pro-0813 | 384 | 2,140.8 MB | 469.5 mm2 | 84.51 mm2 (18.0%) | 180,295 mm2 | 32,453 mm2 | 195,796 mm2 = 240.2 reticles |

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
| DeepSeek-V4-Pro-0813 | 1 | sram | 26,083.1 | 26,061.7 | 26,061.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 26,083.1 | 26,061.7 | 26,061.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 26,083.1 | 26,061.7 | 26,061.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 26,083.1 | 26,061.7 | 26,061.7 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 37,934.1 | 26,061.7 | 27,225.1 | 1.46x | 1.04x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 64,540.1 | 26,061.7 | 45,964.8 | 2.48x | 1.76x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 124,920.5 | 26,061.7 | 75,772.2 | 4.79x | 2.91x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 416,103.9 | 26,061.7 | 196,914.3 | 15.97x | 7.56x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 51,379.6 | 27,161.9 | 27,161.9 | 1.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 51,379.6 | 27,161.9 | 27,161.9 | 1.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 51,379.6 | 27,161.9 | 27,161.9 | 1.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 51,379.6 | 27,161.9 | 27,161.9 | 1.89x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 51,379.6 | 27,161.9 | 27,808.7 | 1.89x | 1.02x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | rom | 64,540.1 | 27,161.9 | 47,093.4 | 2.38x | 1.73x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 124,920.5 | 27,161.9 | 77,855.6 | 4.60x | 2.87x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 450,075.7 | 27,161.9 | 203,237.3 | 16.57x | 7.48x | link_latency | weight_read | weight_read |

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
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 51,379.6 | 0.093 | weight_read | 1.97x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 51,379.6 | 0.093 | weight_read | 1.97x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 51,379.6 | 0.093 | weight_read | 1.97x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,083.1 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 51,379.6 | 0.093 | weight_read | 1.97x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perregion-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 1.04x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 37,934.1 | 0.205 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 1.97 | 1.00 | 51,379.6 | 0.093 | weight_read | 1.35x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 0.69x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 0.72x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 1.13 | 27,225.1 | 0.084 | weight_read | 0.72x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion-romfill | 323,575 | 1.04 | 1.13 | 27,808.7 | 0.086 | link_latency | 0.73x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 64,540.1 | 0.349 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 1.00 | 1.00 | 64,540.1 | 0.349 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 0.40x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 0.42x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 1.53 | 45,964.8 | 0.142 | weight_read | 0.71x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion-romfill | 323,575 | 1.04 | 1.53 | 47,093.4 | 0.146 | weight_read | 0.73x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 124,920.5 | 0.450 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 1.00 | 1.00 | 124,920.5 | 0.450 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 0.21x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 0.22x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 2.08 | 75,772.2 | 0.234 | weight_read | 0.61x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion-romfill | 323,575 | 1.04 | 2.08 | 77,855.6 | 0.241 | weight_read | 0.62x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 416,103.9 | 1.125 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1.97 | 1.00 | 450,075.7 | 0.811 | link_latency | 1.08x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream | 323,575 | 1.00 | 1.00 | 26,061.7 | 0.081 | weight_read | 0.06x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x7-perstream-romfill | 323,575 | 1.04 | 1.00 | 27,161.9 | 0.084 | weight_read | 0.07x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion | 323,575 | 1.00 | 3.72 | 196,914.3 | 0.609 | weight_read | 0.47x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x7-perregion-romfill | 323,575 | 1.04 | 3.72 | 203,237.3 | 0.628 | weight_read | 0.49x |

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
| DeepSeek-V4-Pro-0813 | 1 | 376 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 376 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 398 | 1.00 | 1.000 | 1.000 | 1.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 1 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4-Pro-0813 | 2 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4-Pro-0813 | 4 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4-Pro-0813 | 8 | 14 | 5.03 | 3.56 | 1.41x |
| DeepSeek-V4-Pro-0813 | 16 | 14 | 5.57 | 3.75 | 1.49x |
| DeepSeek-V4-Pro-0813 | 32 | 14 | 8.88 | 4.84 | 1.83x |
| DeepSeek-V4-Pro-0813 | 64 | 14 | 12.06 | 6.05 | 1.99x |
| DeepSeek-V4-Pro-0813 | 256 | 14 | 13.99 | 8.40 | 1.66x |
| DeepSeek-V4-Pro-0813 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4-Pro-0813 | 256 | 56 | 21.37 | 10.48 | 2.04x |
| DeepSeek-V4-Pro-0813 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 4 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 8 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 16 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 32 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 64 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 256 | 112 | 12.84 | 8.85 | 1.45x |
| DeepSeek-V4-Pro-0813 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 168 | 8.89 | 7.62 | 1.17x |
| DeepSeek-V4-Pro-0813 | 1 | 185 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 185 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4-Pro-0813 | 4 | 185 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4-Pro-0813 | 8 | 185 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4-Pro-0813 | 16 | 185 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4-Pro-0813 | 32 | 185 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4-Pro-0813 | 64 | 185 | 5.92 | 5.58 | 1.06x |
| DeepSeek-V4-Pro-0813 | 256 | 185 | 8.12 | 7.20 | 1.13x |
| DeepSeek-V4-Pro-0813 | 1 | 188 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 188 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4-Pro-0813 | 4 | 188 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4-Pro-0813 | 8 | 188 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4-Pro-0813 | 16 | 188 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4-Pro-0813 | 32 | 188 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4-Pro-0813 | 64 | 188 | 5.92 | 5.59 | 1.06x |
| DeepSeek-V4-Pro-0813 | 256 | 188 | 7.99 | 7.13 | 1.12x |
| DeepSeek-V4-Pro-0813 | 1 | 200 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 200 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4-Pro-0813 | 4 | 200 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4-Pro-0813 | 8 | 200 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4-Pro-0813 | 16 | 200 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4-Pro-0813 | 32 | 200 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4-Pro-0813 | 64 | 200 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4-Pro-0813 | 256 | 200 | 7.54 | 6.85 | 1.10x |
| DeepSeek-V4-Pro-0813 | 1 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 4 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 8 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 16 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 32 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 64 | 203 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4-Pro-0813 | 256 | 203 | 7.43 | 6.78 | 1.10x |
| DeepSeek-V4-Pro-0813 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 224 | 6.76 | 6.32 | 1.07x |
| DeepSeek-V4-Pro-0813 | 1 | 227 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 227 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 227 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 227 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 227 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 227 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 227 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 227 | 6.67 | 6.25 | 1.07x |
| DeepSeek-V4-Pro-0813 | 1 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 245 | 6.20 | 5.90 | 1.05x |
| DeepSeek-V4-Pro-0813 | 1 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4-Pro-0813 | 8 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4-Pro-0813 | 16 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4-Pro-0813 | 32 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4-Pro-0813 | 64 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4-Pro-0813 | 256 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4-Pro-0813 | 1 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 8 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 16 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 32 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 64 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 256 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 363 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 363 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 363 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 363 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 363 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 363 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 363 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 363 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 371 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 371 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 371 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 371 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 371 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 371 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 371 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 371 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 4 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 8 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 16 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 32 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 64 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 256 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 4 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 8 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 16 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 32 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 64 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 256 | 672 | 5.98 | 5.88 | 1.02x |

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
| gpu | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 0.6% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 4.2% |

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
| DeepSeek-V4-Pro-0813 | 1 | 376 | 33.73% | 393.18 | 3.10 |
| DeepSeek-V4-Pro-0813 | 2 | 376 | 33.73% | 393.18 | 3.10 |
| DeepSeek-V4-Pro-0813 | 4 | 7 | 0.97% | 12.01 | 3.10 |
| DeepSeek-V4-Pro-0813 | 8 | 7 | 0.97% | 12.01 | 3.10 |
| DeepSeek-V4-Pro-0813 | 16 | 7 | 0.97% | 12.01 | 3.10 |
| DeepSeek-V4-Pro-0813 | 32 | 7 | 0.97% | 12.01 | 3.10 |
| DeepSeek-V4-Pro-0813 | 64 | 7 | 0.97% | 12.01 | 3.10 |

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
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 78.5 | 15,944.0 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 78.5 | 15,944.0 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 78.5 | 15,944.0 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 78.5 | 15,944.0 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 78.5 | 15,944.0 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 78.5 | 15,944.0 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 4.44% | 1,150.91 TB/s | 25,902.15 TB/s | 78.5 | 15,944.0 |
| DeepSeek-V4-Pro-0813 | 256 | 1.97% | 43.0 GB | 4.82% | 1,247.25 TB/s | 25,902.15 TB/s | 62.4 | 15,986.7 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | link_latency | 133 |
| gpu | weight_read | 371 |
| rom | compute | 79 |
| rom | infeasible | 588 |
| rom | link_latency | 325 |
| rom | weight_read | 352 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 588 |

## Mechanical consistency audit

**PASS** over 39,273 checks.

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 70 |
| derived | 41 |
| assumed | 59 |

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

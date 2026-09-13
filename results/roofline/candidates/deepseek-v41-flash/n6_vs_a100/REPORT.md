# Area-constrained roofline: n6_vs_a100-deepseek-v41-flash

> CANDIDATE MODEL under n6_vs_a100: DeepSeek-V4.1-Flash at 200,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 490x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 2 devices. On the GPU side the correction reaches 547x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 107 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash takes 2 x 46,225 mm2 (92,450 mm2, wafer, KV in HBM) at 4,070 tok/s per user and 44 tok/s per 1,000 mm2, holding 6,853 sessions, against 112 copies of one unified HBM die at the same silicon: 5.7x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash on 92,450 mm2 of ROM silicon at 4,070 tok/s per user against 92,512 mm2 of a100_sxm_80gb-x112-tensor at 719 tok/s: **5.7x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 41,801. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 193.94x to it.** At 554,700 mm2 on DeepSeek-V4.1-Flash the pipeline-only GPU delivers 3.15 tok/s and the same silicon running tensor delivers 611 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.68x (DeepSeek-V4.1-Flash, ROM binding on `link_latency`) to 80.41x (DeepSeek-V4.1-Flash, ROM binding on `link_latency`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash engages 2.6% of its ROM array at batch 1 and 3.6% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 228 to 51,699 tok/s, and its rate with every slot occupied from 26,024 to 51,699. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 114 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,154 us over NVLink, capping per-user decode at 867 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 962.2 us and cap it at 1,039 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 8 of 8 operating points and an array 0; on tokens per second per square millimetre the same points go 0 to the array and 8 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 0 of 1642 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 25.6x of aggregate throughput (DeepSeek-V4.1-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 10.38x, on DeepSeek-V4.1-Flash at batch 256, where the busiest region carries 3.13x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 16 of 16 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 71% of its cooling budget. The companion study at the other node does have power-limited points.


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

### DeepSeek-V4.1-Flash at 200,000 tokens

**Recommended: `ROM-N6-native-HBMKV-wafer-hybrid-x2`** -- 2 x 46,225 mm2 wafers, 92,450 mm2 total, `hybrid`-parallel, KV in HBM, spare silicon to `sram`.

- **4,069.8 tok/s per user** (0.25 ms/token), binding on `link_latency`
- **44.0 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 8,140 tok/s aggregate with every slot full, over 6,853 resident sessions (fill limited by `pipeline_slots`)
- 4,969 W at 0.054 W/mm2, 610.4 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 112 copies of one unified HBM die -- `a100_sxm_80gb-x112-tensor`, 92,512 mm2, area ratio 0.9993 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 92,450 | 92,512 | 0.9993 |
| user tok/s | 4,069.8 | 719.2 | 5.66x |
| aggregate tok/s | 8,140 | 719 | 11.32x |
| resident sessions | 6,853 | 41,801 | -- |
| J/token | 0.6104 | 23.8650 | 39.1x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 6,853 sessions against one that holds 41,801 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x311-tensor` at 256,886 mm2 and 751.8 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 44.0 | 1 | 5.66x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 44.0 | 1 | 5.66x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-tensor-x108` | 88,020 | 1,139.2 | 12.9 | 1 | 1.59x |
| **after -- this report's rule** | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 44.0 | 6,853 | 5.66x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-HBMKV-wafer-hybrid-x2` **<-- recommended** | 92,450 | 2 | 4,069.8 | 8,140 | 44.0 | 6,853 | `link_latency` | 4,969 | 610.4 | `a100_sxm_80gb-x112-tensor` | 5.66x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 114 | densest | `ROM-N6-native-SRAMKV-array-tensor-x108` | 88,020 | 1,139.2 | 12.9 | 1 |
| array | 114 | fastest | `ROM-N6-native-SRAMKV-array-tensor-x315-romfill` | 256,725 | 1,160.7 | 4.5 | 1 |
| array | 114 | smallest | `ROM-N6-native-SRAMKV-array-tensor-x108` | 88,020 | 1,139.2 | 12.9 | 1 |
| wafer | 72 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 44.0 | 1 |
| wafer | 72 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 44.0 | 1 |
| wafer | 72 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 44.0 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-tensor-x315-romfill` | 256,725 | 1,160.7 | 1,161 | 1 | 23,046 | 19,855.7 | `link_latency` | `a100_sxm_80gb-x311-tensor` | 751.8 | 121,091 | 61,104.7 | 0.999 | 1.54x | 3.1x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 4,070 | 1 | 4,642 | 1,140.6 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 719.2 | 41,801 | 23,865.0 | 0.999 | 5.66x | 20.9x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-tensor-x109` | 88,835 | 1,147.3 | 1,147 | 1 | 5,457 | 4,756.7 | `link_latency` | `a100_sxm_80gb-x108-tensor` | 717.3 | 40,207 | 23,119.0 | 0.996 | 1.60x | 4.9x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | -- | 1 | -- | 1,140.6 | -- | -- | -- | -- | -- | 0.961 | 3.55x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-tensor-x143` | 116,545 | 1,027.6 | 2,055 | 56,977 | 10,143 | 4,935.3 | `link_latency` | `a100_sxm_80gb-x141-tensor` | 627.3 | 53,356 | 17,154.9 | 1.001 | 1.64x | 3.5x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 8,140 | 6,853 | 4,969 | 610.4 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 612.2 | 41,801 | 14,133.6 | 0.999 | 6.65x | 23.2x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-tensor-x118` | 96,170 | 1,003.3 | 2,007 | 47,016 | 6,838 | 3,407.8 | `link_latency` | `a100_sxm_80gb-x116-tensor` | 614.5 | 43,395 | 14,555.7 | 1.004 | 1.63x | 4.3x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | -- | 6,853 | -- | 610.4 | -- | -- | -- | -- | -- | 1.040 | 4.06x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hybrid-x118` | 96,170 | 974.9 | 14,623 | 47,016 | 7,003 | 478.9 | `weight_read` | `a100_sxm_80gb-x116-tensor` | 480.4 | 43,395 | 9,412.6 | 1.004 | 2.03x | 19.7x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,059.7 | 16,239 | 6,853 | 5,051 | 311.1 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 478.7 | 41,801 | 9,140.8 | 0.999 | 8.48x | 29.4x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x118` | 96,170 | 974.9 | 14,623 | 47,016 | 7,003 | 478.9 | `weight_read` | `a100_sxm_80gb-x116-tensor` | 480.4 | 43,395 | 9,412.6 | 1.004 | 2.03x | 19.7x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,059.7 | -- | 6,853 | -- | 311.1 | -- | -- | -- | -- | -- | 1.040 | 4.16x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hybrid-x118` | 96,170 | 974.9 | 14,623 | 47,016 | 7,003 | 478.9 | `weight_read` | `a100_sxm_80gb-x116-tensor` | 360.2 | 43,395 | 6,381.5 | 1.004 | 2.71x | 13.3x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3,456.6 | 27,653 | 10,279 | 11,997 | 433.8 | `link_latency` | `a100_sxm_80gb-x168-tensor` | 376.9 | 64,114 | 8,615.7 | 0.999 | 9.17x | 19.9x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x170` | 138,550 | 762.8 | 16,782 | 67,735 | 13,904 | 828.5 | `weight_read` | `a100_sxm_80gb-x168-tensor` | 376.9 | 64,114 | 8,615.7 | 0.998 | 2.02x | 10.4x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3,456.6 | -- | 10,279 | -- | 433.8 | -- | -- | -- | -- | -- | 0.999 | 4.53x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hybrid-x118` | 96,170 | 974.0 | 15,585 | 47,016 | 7,013 | 450.0 | `weight_read` | `a100_sxm_80gb-x116-tensor` | 248.6 | 43,395 | 4,698.7 | 1.004 | 3.92x | 10.4x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3,452.3 | 55,236 | 10,279 | 12,277 | 222.3 | `link_latency` | `a100_sxm_80gb-x168-tensor` | 260.3 | 64,114 | 6,311.3 | 0.999 | 13.26x | 28.4x |
| 16 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x170` | 138,550 | 762.8 | 16,782 | 67,735 | 13,904 | 828.5 | `weight_read` | `a100_sxm_80gb-x168-tensor` | 260.3 | 64,114 | 6,311.3 | 0.998 | 2.93x | 7.6x |
| 16 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3,452.3 | -- | 10,279 | -- | 222.3 | -- | -- | -- | -- | -- | 0.999 | 4.53x wafer/array | -- |
| 32 | array | `ROM-N6-native-HBMKV-array-hybrid-x143` | 116,545 | 862.8 | 27,610 | 56,977 | 10,442 | 378.2 | `weight_read` | `a100_sxm_80gb-x141-tensor` | 164.8 | 53,356 | 4,273.3 | 1.001 | 5.24x | 11.3x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3,443.6 | 110,195 | 10,279 | 12,830 | 116.4 | `link_latency` | `a100_sxm_80gb-x168-tensor` | 168.2 | 64,114 | 4,919.4 | 0.999 | 20.48x | 42.3x |
| 32 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x170` | 138,550 | 758.7 | 24,277 | 67,735 | 13,980 | 575.8 | `weight_read` | `a100_sxm_80gb-x168-tensor` | 168.2 | 64,114 | 4,919.4 | 0.998 | 4.51x | 8.5x |
| 32 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | 3,443.6 | -- | 10,279 | -- | 116.4 | -- | -- | -- | -- | -- | 0.999 | 4.54x wafer/array | -- |
| 64 | array | `ROM-N6-native-HBMKV-array-hybrid-x143` | 116,545 | 844.5 | 54,049 | 56,977 | 10,710 | 198.2 | `weight_read` | `a100_sxm_80gb-x141-tensor` | 100.8 | 53,356 | 3,479.0 | 1.001 | 8.38x | 17.6x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 3,169.3 | 202,834 | 13,706 | 19,270 | 95.0 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 105.0 | 86,427 | 5,135.1 | 0.999 | 30.17x | 54.1x |
| 64 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x228-romfill` | 185,820 | 651.5 | 41,698 | 90,845 | 21,114 | 506.4 | `weight_read` | `a100_sxm_80gb-x225-tensor` | 105.0 | 86,825 | 5,158.4 | 1.000 | 6.21x | 10.2x |
| 64 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 3,169.3 | -- | 13,706 | -- | 95.0 | -- | -- | -- | -- | -- | 1.005 | 4.86x wafer/array | -- |
| 256 | array | `ROM-N6-native-HBMKV-array-hybrid-x170` | 138,550 | 676.3 | 173,129 | 67,735 | 15,479 | 89.4 | `weight_read` | `a100_sxm_80gb-x168-hybrid` | 35.0 | 64,114 | 3,223.6 | 0.998 | 19.32x | 36.1x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 2,715.4 | 695,139 | 41,119 | 58,634 | 84.3 | `link_latency` | `a100_sxm_80gb-x672-tensor` | 33.8 | 264,929 | 11,352.9 | 0.999 | 80.41x | 134.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-8 | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | wafer | HBM | 6,853 |
| 16-64 | `ROM-N6-native-HBMKV-wafer-hybrid-x3` | 138,675 | wafer | HBM | 10,279 |
| 256 | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | wafer | HBM | 13,706 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash | HBM | rom | 116, 118, 143, 170, 171, 227, 228, 340, 342 |
| DeepSeek-V4.1-Flash | HBM | sram | 116, 118, 143, 170, 171, 227, 228, 340, 342 |
| DeepSeek-V4.1-Flash | SRAM | rom | 108, 109, 113, 132, 158, 170, 210, 227, 315, 340 |
| DeepSeek-V4.1-Flash | SRAM | sram | 108, 109, 113, 132, 158, 170, 210, 227, 315, 340 |

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

- **0 of 1,642 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 71% of its cooling budget, and the busiest wafer-scale ROM design 28%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 16 | 0 | 63.6% | 70.7% | 0.342 | 57% |
| gpu | wafer (>=40,000 mm2) | 552 | 0 | 39.2% | 53.8% | 0.260 | 92% |
| rom | wafer (>=40,000 mm2) | 1,074 | 0 | 17.9% | 27.7% | 0.139 | 99% |

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
| DeepSeek-V4.1-Flash | 1 | 92,450 | `DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 1.140616 | 4,642.1 | link_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor` | 23.864989 | 17,162.7 | link_latency | 20.92x |
| DeepSeek-V4.1-Flash | 2 | 92,450 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 0.610440 | 4,968.8 | link_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor` | 14.133618 | 17,306.5 | link_latency | 23.15x |
| DeepSeek-V4.1-Flash | 4 | 92,450 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 0.311073 | 5,051.4 | link_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor` | 9.140807 | 17,504.0 | link_latency | 29.38x |
| DeepSeek-V4.1-Flash | 8 | 138,675 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3` | 0.433835 | 11,996.8 | link_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-tensor` | 8.615689 | 25,974.9 | link_latency | 19.86x |
| DeepSeek-V4.1-Flash | 16 | 138,675 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3` | 0.222260 | 12,276.8 | link_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-tensor` | 6.311265 | 26,286.5 | link_latency | 28.40x |
| DeepSeek-V4.1-Flash | 32 | 138,675 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3` | 0.116433 | 12,830.3 | link_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-tensor` | 4.919375 | 26,475.7 | link_latency | 42.25x |
| DeepSeek-V4.1-Flash | 64 | 138,675 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3` | 0.069000 | 13,702.9 | link_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-tensor` | 4.019690 | 26,383.2 | link_latency | 58.26x |
| DeepSeek-V4.1-Flash | 256 | 554,700 | `DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.084349 | 58,634.3 | link_latency | `DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-tensor` | 11.352916 | 98,139.6 | link_latency | 134.59x |

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
| DeepSeek-V4.1-Flash | 200,000 | 552 B | 510.3 GB | 7.40 | 0.047 GB | 0.181 GB | 278.7 |

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
| DeepSeek-V4.1-Flash | 2 | 92,450 | 18,789.4 | wafer-pipeline | 4,069.8 | wafer-hybrid | 4.62x | 1,502.1 | pipeline | 719.2 | tensor | 2.09x | 12.51x | 5.66x | 0.45x |
| DeepSeek-V4.1-Flash | 3 | 138,675 | 18,789.4 | wafer-pipeline | 3,459.3 | wafer-hybrid | 5.43x | 1,581.5 | pipeline | 735.6 | tensor | 2.15x | 11.88x | 4.70x | 0.40x |
| DeepSeek-V4.1-Flash | 4 | 184,900 | 20,893.6 | wafer-pipeline | 3,215.5 | wafer-hybrid | 6.50x | 1,625.3 | pipeline | 744.3 | tensor | 2.18x | 12.86x | 4.32x | 0.34x |
| DeepSeek-V4.1-Flash | 6 | 277,350 | 27,114.7 | wafer-pipeline | 3,114.1 | wafer-hybrid | 8.71x | 1,672.2 | pipeline | 605.2 | tensor | 2.76x | 16.21x | 5.15x | 0.32x |
| DeepSeek-V4.1-Flash | 8 | 369,800 | 31,856.3 | wafer-pipeline | 3,018.9 | wafer-hybrid | 10.55x | 1,697.0 | pipeline | 608.2 | tensor | 2.79x | 18.77x | 4.96x | 0.26x |
| DeepSeek-V4.1-Flash | 12 | 554,700 | 38,606.8 | wafer-pipeline | 2,844.9 | wafer-hybrid | 13.57x | 1,722.7 | pipeline | 611.3 | tensor | 2.82x | 22.41x | 4.65x | 0.21x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.21x to 0.45x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash | 1 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 4,069.8 | 4,069.8 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 823.25 | 719.2 | 719.2 | link_latency | 5.66x | 5.66x | 254.43x | 5.66x |
| DeepSeek-V4.1-Flash | 1 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-tensor-x108 | 88,020 | 1,139.2 | 1,139.2 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x107-tensor | 88,382 | 1.00x | tensor | 823.25 | 716.8 | 716.8 | link_latency | 1.59x | 1.59x | 68.61x | 1.59x |
| DeepSeek-V4.1-Flash | 2 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,069.8 | 8,139.7 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 921.70 | 612.2 | 1,224.5 | link_latency | 6.65x | 6.65x | 254.43x | 6.65x |
| DeepSeek-V4.1-Flash | 4 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,059.7 | 16,238.6 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 1,118.60 | 478.7 | 1,914.9 | link_latency | 8.48x | 8.48x | 253.79x | 8.48x |
| DeepSeek-V4.1-Flash | 8 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 3,456.6 | 27,652.9 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-tensor | 138,768 | 1.00x | tensor | 1,531.13 | 376.9 | 3,014.8 | link_latency | 9.17x | 9.17x | 304.55x | 9.17x |
| DeepSeek-V4.1-Flash | 8 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 3,090.2 | 24,721.8 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 1,512.40 | 358.7 | 2,869.9 | link_latency | 8.61x | 8.61x | 193.19x | 8.61x |
| DeepSeek-V4.1-Flash | 16 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 3,452.3 | 55,236.2 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-tensor | 138,768 | 1.00x | tensor | 2,337.45 | 260.3 | 4,165.0 | link_latency | 13.26x | 13.26x | 304.17x | 13.26x |
| DeepSeek-V4.1-Flash | 16 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 2,091.4 | 33,462.3 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 2,300.00 | 247.6 | 3,961.3 | link_latency | 8.45x | 8.45x | 130.75x | 8.45x |
| DeepSeek-V4.1-Flash | 32 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 3,443.6 | 110,195.2 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-tensor | 138,768 | 1.00x | tensor | 3,950.11 | 168.2 | 5,381.9 | link_latency | 20.48x | 20.48x | 303.41x | 20.48x |
| DeepSeek-V4.1-Flash | 32 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1,270.2 | 40,647.9 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 3,875.21 | 160.1 | 5,124.1 | link_latency | 7.93x | 7.93x | 79.41x | 7.93x |
| DeepSeek-V4.1-Flash | 64 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 3,169.3 | 202,834.4 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 7,250.31 | 105.0 | 6,722.4 | link_latency | 30.17x | 30.17x | 360.11x | 30.17x |
| DeepSeek-V4.1-Flash | 64 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 711.5 | 45,537.2 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 7,025.62 | 98.5 | 6,304.4 | link_latency | 7.22x | 7.22x | 44.48x | 7.22x |
| DeepSeek-V4.1-Flash | 256 | fastest | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,715.4 | 695,138.6 | link_latency | DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 27,750.84 | 33.8 | 8,644.4 | link_latency | 80.41x | 80.41x | 861.53x | 80.41x |
| DeepSeek-V4.1-Flash | 256 | smallest silicon | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2 | 92,450 | 201.9 | 51,698.9 | compute | DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | 92,512 | 1.00x | hybrid | 654.83 | 37.9 | 9,701.2 | weight_read | 5.33x | 5.33x | 16.89x | 5.33x |

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
| DeepSeek-V4.1-Flash | 8 | 6,608 | 79.9 | 505.5 | — | tensor | 407.17 | 20.6% | weight_read |
| DeepSeek-V4.1-Flash | 56 | 46,256 | 27.3 | 676.1 | 200.0 | tensor | 816.23 | 55.2% | link_latency |
| DeepSeek-V4.1-Flash | 107 | 88,382 | 16.6 | 716.8 | 120.3 | tensor | 823.25 | 59.0% | link_latency |
| DeepSeek-V4.1-Flash | 108 | 89,208 | 16.5 | 717.3 | 120.5 | tensor | 823.25 | 59.0% | link_latency |
| DeepSeek-V4.1-Flash | 111 | 91,686 | 16.1 | 718.7 | 121.0 | tensor | 823.25 | 59.2% | link_latency |
| DeepSeek-V4.1-Flash | 112 | 92,512 | 16.0 | 719.2 | 121.2 | tensor | 823.25 | 59.2% | link_latency |
| DeepSeek-V4.1-Flash | 114 | 94,164 | 15.8 | 719.8 | 113.8 | tensor | 823.72 | 59.3% | link_latency |
| DeepSeek-V4.1-Flash | 116 | 95,816 | 15.5 | 720.7 | 114.2 | tensor | 823.72 | 59.4% | link_latency |
| DeepSeek-V4.1-Flash | 130 | 107,380 | 14.1 | 725.7 | 103.1 | tensor | 824.49 | 59.8% | link_latency |
| DeepSeek-V4.1-Flash | 141 | 116,466 | 13.2 | 729.1 | 98.8 | tensor | 824.81 | 60.1% | link_latency |
| DeepSeek-V4.1-Flash | 156 | 128,856 | 12.1 | 732.9 | 90.6 | tensor | 825.36 | 60.5% | link_latency |
| DeepSeek-V4.1-Flash | 168 | 138,768 | 11.3 | 735.6 | 87.2 | tensor | 825.59 | 60.7% | link_latency |
| DeepSeek-V4.1-Flash | 169 | 139,594 | 11.3 | 735.7 | 83.4 | tensor | 825.80 | 60.8% | link_latency |
| DeepSeek-V4.1-Flash | 207 | 170,982 | 9.4 | 742.1 | 72.7 | tensor | 826.49 | 61.3% | link_latency |
| DeepSeek-V4.1-Flash | 212 | 175,112 | 9.2 | 742.7 | 70.2 | tensor | 826.63 | 61.4% | link_latency |
| DeepSeek-V4.1-Flash | 224 | 185,024 | 8.8 | 744.3 | 68.2 | tensor | 826.76 | 61.5% | link_latency |
| DeepSeek-V4.1-Flash | 225 | 185,850 | 8.8 | 744.3 | 65.9 | tensor | 826.88 | 61.5% | link_latency |
| DeepSeek-V4.1-Flash | 234 | 193,284 | 8.5 | 745.4 | 64.0 | tensor | 827.00 | 61.6% | link_latency |
| DeepSeek-V4.1-Flash | 311 | 256,886 | 6.5 | 751.8 | 50.7 | tensor | 827.75 | 62.2% | link_latency |
| DeepSeek-V4.1-Flash | 335 | 276,710 | 6.1 | 605.2 | 47.4 | tensor | 1,152.73 | 69.8% | link_latency |
| DeepSeek-V4.1-Flash | 336 | 277,536 | 6.1 | 605.2 | 47.5 | tensor | 1,152.73 | 69.8% | link_latency |
| DeepSeek-V4.1-Flash | 337 | 278,362 | 6.1 | 605.2 | 46.4 | tensor | 1,152.79 | 69.8% | link_latency |
| DeepSeek-V4.1-Flash | 448 | 370,048 | 4.6 | 608.2 | 36.4 | tensor | 1,153.32 | 70.1% | link_latency |
| DeepSeek-V4.1-Flash | 672 | 555,072 | 3.2 | 611.3 | 24.9 | tensor | 1,153.90 | 70.5% | link_latency |

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
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-pipeline-x109 | DeepSeek-V4.1-Flash | 109 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash | 2 | pipeline | on_wafer | inter_wafer | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-tensor-x108 | DeepSeek-V4.1-Flash | 108 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash | 2 | tensor | on_wafer | inter_wafer | 160 | 962.19 us | 103.9 tok/s | 1,039.3 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on inter_wafer (traversals 2.0) = 808.19 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-array-hybrid-x109 | DeepSeek-V4.1-Flash | 109 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash | 2 | hybrid | on_wafer | inter_wafer | 81 | 159.07 us | 628.7 tok/s | 6,286.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.07 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-pipeline-x118 | DeepSeek-V4.1-Flash | 118 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash | 2 | pipeline | on_wafer | inter_wafer | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-tensor-x116 | DeepSeek-V4.1-Flash | 116 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash | 2 | tensor | on_wafer | inter_wafer | 160 | 962.19 us | 103.9 tok/s | 1,039.3 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on inter_wafer (traversals 2.0) = 808.19 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hybrid-x118 | DeepSeek-V4.1-Flash | 118 | hybrid | nvlink3 | infiniband_hdr | 94 | 441.32 us | 226.6 tok/s | 2,265.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 34.15 us |
| DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash | 2 | hybrid | on_wafer | inter_wafer | 81 | 159.07 us | 628.7 tok/s | 6,286.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.07 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x8-pipeline | DeepSeek-V4.1-Flash | 8 | pipeline | nvlink3 | infiniband_hdr | 7 | 17.74 us | 5,637.3 tok/s | 56,373.2 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 17.74 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x8-tensor | DeepSeek-V4.1-Flash | 8 | tensor | nvlink3 | infiniband_hdr | 80 | 407.17 us | 245.6 tok/s | 2,456.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4.1-Flash | 56 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4.1-Flash | 56 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4.1-Flash | 56 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x107-pipeline | DeepSeek-V4.1-Flash | 107 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x107-tensor | DeepSeek-V4.1-Flash | 107 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x107-hybrid | DeepSeek-V4.1-Flash | 107 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x108-pipeline | DeepSeek-V4.1-Flash | 108 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x108-tensor | DeepSeek-V4.1-Flash | 108 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x108-hybrid | DeepSeek-V4.1-Flash | 108 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-pipeline | DeepSeek-V4.1-Flash | 111 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-tensor | DeepSeek-V4.1-Flash | 111 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x111-hybrid | DeepSeek-V4.1-Flash | 111 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4.1-Flash | 112 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4.1-Flash | 112 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4.1-Flash | 112 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x114-pipeline | DeepSeek-V4.1-Flash | 114 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x114-tensor | DeepSeek-V4.1-Flash | 114 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x114-hybrid | DeepSeek-V4.1-Flash | 114 | hybrid | nvlink3 | infiniband_hdr | 94 | 441.32 us | 226.6 tok/s | 2,265.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 34.15 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-pipeline | DeepSeek-V4.1-Flash | 116 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-tensor | DeepSeek-V4.1-Flash | 116 | tensor | nvlink3 | infiniband_hdr | 160 | 823.72 us | 121.4 tok/s | 1,214.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 416.55 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x116-hybrid | DeepSeek-V4.1-Flash | 116 | hybrid | nvlink3 | infiniband_hdr | 94 | 441.32 us | 226.6 tok/s | 2,265.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 34.15 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x130-pipeline | DeepSeek-V4.1-Flash | 130 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x130-tensor | DeepSeek-V4.1-Flash | 130 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x130-hybrid | DeepSeek-V4.1-Flash | 130 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-pipeline | DeepSeek-V4.1-Flash | 141 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-tensor | DeepSeek-V4.1-Flash | 141 | tensor | nvlink3 | infiniband_hdr | 160 | 824.81 us | 121.2 tok/s | 1,212.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 417.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x141-hybrid | DeepSeek-V4.1-Flash | 141 | hybrid | nvlink3 | infiniband_hdr | 97 | 448.64 us | 222.9 tok/s | 2,229.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 41.47 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x156-pipeline | DeepSeek-V4.1-Flash | 156 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x156-tensor | DeepSeek-V4.1-Flash | 156 | tensor | nvlink3 | infiniband_hdr | 160 | 825.36 us | 121.2 tok/s | 1,211.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 418.19 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x156-hybrid | DeepSeek-V4.1-Flash | 156 | hybrid | nvlink3 | infiniband_hdr | 99 | 453.52 us | 220.5 tok/s | 2,205.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 46.35 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-pipeline | DeepSeek-V4.1-Flash | 168 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-tensor | DeepSeek-V4.1-Flash | 168 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x168-hybrid | DeepSeek-V4.1-Flash | 168 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-pipeline | DeepSeek-V4.1-Flash | 169 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-tensor | DeepSeek-V4.1-Flash | 169 | tensor | nvlink3 | infiniband_hdr | 160 | 825.80 us | 121.1 tok/s | 1,210.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 418.64 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x169-hybrid | DeepSeek-V4.1-Flash | 169 | hybrid | nvlink3 | infiniband_hdr | 101 | 458.40 us | 218.2 tok/s | 2,181.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 51.23 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x207-pipeline | DeepSeek-V4.1-Flash | 207 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x207-tensor | DeepSeek-V4.1-Flash | 207 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x207-hybrid | DeepSeek-V4.1-Flash | 207 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x212-pipeline | DeepSeek-V4.1-Flash | 212 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x212-tensor | DeepSeek-V4.1-Flash | 212 | tensor | nvlink3 | infiniband_hdr | 160 | 826.63 us | 121.0 tok/s | 1,209.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 419.46 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x212-hybrid | DeepSeek-V4.1-Flash | 212 | hybrid | nvlink3 | infiniband_hdr | 106 | 470.60 us | 212.5 tok/s | 2,125.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 26 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.43 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-pipeline | DeepSeek-V4.1-Flash | 224 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-tensor | DeepSeek-V4.1-Flash | 224 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x224-hybrid | DeepSeek-V4.1-Flash | 224 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-pipeline | DeepSeek-V4.1-Flash | 225 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-tensor | DeepSeek-V4.1-Flash | 225 | tensor | nvlink3 | infiniband_hdr | 160 | 826.88 us | 120.9 tok/s | 1,209.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 419.71 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x225-hybrid | DeepSeek-V4.1-Flash | 225 | hybrid | nvlink3 | infiniband_hdr | 108 | 475.48 us | 210.3 tok/s | 2,103.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 68.31 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x234-pipeline | DeepSeek-V4.1-Flash | 234 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x234-tensor | DeepSeek-V4.1-Flash | 234 | tensor | nvlink3 | infiniband_hdr | 160 | 827.00 us | 120.9 tok/s | 1,209.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 30 on infiniband_hdr (traversals 2.0) = 419.83 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x234-hybrid | DeepSeek-V4.1-Flash | 234 | hybrid | nvlink3 | infiniband_hdr | 109 | 477.92 us | 209.2 tok/s | 2,092.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 29 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.75 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x311-pipeline | DeepSeek-V4.1-Flash | 311 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x311-tensor | DeepSeek-V4.1-Flash | 311 | tensor | nvlink3 | infiniband_hdr | 160 | 827.75 us | 120.8 tok/s | 1,208.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 39 on infiniband_hdr (traversals 2.0) = 420.58 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x311-hybrid | DeepSeek-V4.1-Flash | 311 | hybrid | nvlink3 | infiniband_hdr | 118 | 499.87 us | 200.1 tok/s | 2,000.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 38 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 92.70 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-pipeline | DeepSeek-V4.1-Flash | 335 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-tensor | DeepSeek-V4.1-Flash | 335 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x335-hybrid | DeepSeek-V4.1-Flash | 335 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-pipeline | DeepSeek-V4.1-Flash | 336 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-tensor | DeepSeek-V4.1-Flash | 336 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x336-hybrid | DeepSeek-V4.1-Flash | 336 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-pipeline | DeepSeek-V4.1-Flash | 337 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-tensor | DeepSeek-V4.1-Flash | 337 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.79 us | 86.7 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 43 on infiniband_hdr (traversals 4.0) = 745.62 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x337-hybrid | DeepSeek-V4.1-Flash | 337 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-pipeline | DeepSeek-V4.1-Flash | 448 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-tensor | DeepSeek-V4.1-Flash | 448 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.32 us | 86.7 tok/s | 867.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 746.15 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x448-hybrid | DeepSeek-V4.1-Flash | 448 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-pipeline | DeepSeek-V4.1-Flash | 672 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-tensor | DeepSeek-V4.1-Flash | 672 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.90 us | 86.7 tok/s | 866.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 746.73 us |
| DeepSeek-V4.1-Flash/a100_sxm_80gb-x672-hybrid | DeepSeek-V4.1-Flash | 672 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4.1-Flash | 1 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 4,069.8 | 0.044 | 1,139.2 (88,020) | 4,069.8 (92,450) | 3.57x | link_latency |
| DeepSeek-V4.1-Flash | 2 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,069.8 | 0.044 | 1,003.3 (96,170) | 4,069.8 (92,450) | 4.06x | link_latency |
| DeepSeek-V4.1-Flash | 4 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,059.7 | 0.044 | 974.9 (96,170) | 4,059.7 (92,450) | 4.16x | link_latency |
| DeepSeek-V4.1-Flash | 8 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 3,456.6 | 0.025 | 974.9 (96,170) | 3,456.6 (138,675) | 3.55x | link_latency |
| DeepSeek-V4.1-Flash | 16 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 3,452.3 | 0.025 | 974.0 (96,170) | 3,452.3 (138,675) | 3.54x | link_latency |
| DeepSeek-V4.1-Flash | 32 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 3,443.6 | 0.025 | 862.8 (116,545) | 3,443.6 (138,675) | 3.99x | link_latency |
| DeepSeek-V4.1-Flash | 64 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 3,103.0 | 0.022 | 844.5 (116,545) | 3,103.0 (138,675) | 3.67x | link_latency |
| DeepSeek-V4.1-Flash | 256 | wafer | wafer | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,715.4 | 0.005 | 676.3 (138,550) | 2,715.4 (554,700) | 4.02x | link_latency |

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
| DeepSeek-V4.1-Flash | 384 | 752.0 MB | 164.9 mm2 | 29.69 mm2 (18.0%) | 63,336 mm2 | 11,400 mm2 | 111,918 mm2 = 137.3 reticles |

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
| DeepSeek-V4.1-Flash | 1 | sram | 26,098.2 | 26,068.4 | 26,068.4 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | sram | 26,098.2 | 26,068.4 | 26,068.4 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | sram | 26,098.2 | 26,068.4 | 26,068.4 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 8 | sram | 27,652.9 | 26,068.4 | 26,068.4 | 1.06x | 1.00x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | sram | 55,236.2 | 26,068.4 | 40,115.2 | 2.12x | 1.54x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 32 | sram | 110,195.2 | 26,068.4 | 65,873.7 | 4.23x | 2.53x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | sram | 198,592.1 | 26,068.4 | 111,932.5 | 7.62x | 4.29x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 256 | sram | 590,694.2 | 26,073.5 | 270,585.4 | 22.66x | 10.38x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 1 | rom | 89,913.7 | 27,160.8 | 27,160.8 | 3.31x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 2 | rom | 89,913.7 | 27,160.8 | 27,160.8 | 3.31x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 4 | rom | 89,913.7 | 27,160.8 | 27,160.8 | 3.31x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 8 | rom | 89,913.7 | 27,160.8 | 27,160.8 | 3.31x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 16 | rom | 89,913.7 | 27,160.8 | 41,022.6 | 3.31x | 1.51x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 32 | rom | 110,195.2 | 27,160.8 | 67,583.8 | 4.06x | 2.49x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 64 | rom | 202,834.4 | 27,160.8 | 115,090.8 | 7.47x | 4.24x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash | 256 | rom | 695,138.6 | 27,166.3 | 279,561.3 | 25.59x | 10.29x | link_latency | weight_read | weight_read |

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
| DeepSeek-V4.1-Flash | 1 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,098.2 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 89,913.7 | 0.162 | weight_read | 3.45x |
| DeepSeek-V4.1-Flash | 1 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,068.4 | 0.141 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 1.04 | 1.00 | 27,160.8 | 0.147 | weight_read | 1.04x |
| DeepSeek-V4.1-Flash | 1 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion | 184,900 | 1.00 | 1.00 | 26,068.4 | 0.141 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 1 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 1.04 | 1.00 | 27,160.8 | 0.147 | weight_read | 1.04x |
| DeepSeek-V4.1-Flash | 2 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,098.2 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 2 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 89,913.7 | 0.162 | weight_read | 3.45x |
| DeepSeek-V4.1-Flash | 2 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,068.4 | 0.141 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 2 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 1.04 | 1.00 | 27,160.8 | 0.147 | weight_read | 1.04x |
| DeepSeek-V4.1-Flash | 2 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion | 184,900 | 1.00 | 1.00 | 26,068.4 | 0.141 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 2 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 1.04 | 1.00 | 27,160.8 | 0.147 | weight_read | 1.04x |
| DeepSeek-V4.1-Flash | 4 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,098.2 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 4 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 89,913.7 | 0.162 | weight_read | 3.45x |
| DeepSeek-V4.1-Flash | 4 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,068.4 | 0.141 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 4 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 1.04 | 1.00 | 27,160.8 | 0.147 | weight_read | 1.04x |
| DeepSeek-V4.1-Flash | 4 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion | 184,900 | 1.00 | 1.00 | 26,068.4 | 0.141 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 4 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 1.04 | 1.00 | 27,160.8 | 0.147 | weight_read | 1.04x |
| DeepSeek-V4.1-Flash | 8 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 27,652.9 | 0.199 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash | 8 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 89,913.7 | 0.162 | weight_read | 3.25x |
| DeepSeek-V4.1-Flash | 8 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,068.4 | 0.141 | weight_read | 0.94x |
| DeepSeek-V4.1-Flash | 8 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 1.04 | 1.00 | 27,160.8 | 0.147 | weight_read | 0.98x |
| DeepSeek-V4.1-Flash | 8 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion | 184,900 | 1.00 | 1.00 | 26,068.4 | 0.141 | weight_read | 0.94x |
| DeepSeek-V4.1-Flash | 8 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 1.04 | 1.00 | 27,160.8 | 0.147 | weight_read | 0.98x |
| DeepSeek-V4.1-Flash | 16 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 55,236.2 | 0.398 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash | 16 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3.45 | 1.00 | 89,913.7 | 0.162 | weight_read | 1.63x |
| DeepSeek-V4.1-Flash | 16 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,068.4 | 0.141 | weight_read | 0.47x |
| DeepSeek-V4.1-Flash | 16 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 1.04 | 1.00 | 27,160.8 | 0.147 | weight_read | 0.49x |
| DeepSeek-V4.1-Flash | 16 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x4-perregion | 184,900 | 1.00 | 1.43 | 40,115.2 | 0.217 | weight_read | 0.73x |
| DeepSeek-V4.1-Flash | 16 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4-perregion-romfill | 184,900 | 1.04 | 1.43 | 41,022.6 | 0.222 | weight_read | 0.74x |
| DeepSeek-V4.1-Flash | 32 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 110,195.2 | 0.795 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash | 32 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 1.00 | 1.00 | 110,195.2 | 0.795 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash | 32 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,068.4 | 0.141 | weight_read | 0.24x |
| DeepSeek-V4.1-Flash | 32 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 1.04 | 1.00 | 27,160.8 | 0.147 | weight_read | 0.25x |
| DeepSeek-V4.1-Flash | 32 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x4-perregion | 184,900 | 1.00 | 1.99 | 65,873.7 | 0.356 | weight_read | 0.60x |
| DeepSeek-V4.1-Flash | 32 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4-perregion-romfill | 184,900 | 1.04 | 1.99 | 67,583.8 | 0.366 | weight_read | 0.61x |
| DeepSeek-V4.1-Flash | 64 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 198,592.1 | 1.432 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash | 64 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 1.15 | 1.00 | 202,834.4 | 1.097 | link_latency | 1.02x |
| DeepSeek-V4.1-Flash | 64 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,068.4 | 0.141 | weight_read | 0.13x |
| DeepSeek-V4.1-Flash | 64 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 1.04 | 1.00 | 27,160.8 | 0.147 | weight_read | 0.14x |
| DeepSeek-V4.1-Flash | 64 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x4-perregion | 184,900 | 1.00 | 2.54 | 111,932.5 | 0.605 | weight_read | 0.56x |
| DeepSeek-V4.1-Flash | 64 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4-perregion-romfill | 184,900 | 1.04 | 2.54 | 115,090.8 | 0.622 | weight_read | 0.58x |
| DeepSeek-V4.1-Flash | 256 | batched | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 590,694.2 | 2.130 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash | 256 | batched | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3.45 | 1.00 | 695,138.6 | 1.253 | link_latency | 1.18x |
| DeepSeek-V4.1-Flash | 256 | per_stream | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.13 | 26,073.5 | 0.141 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash | 256 | per_stream | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 1.04 | 1.13 | 27,166.3 | 0.147 | weight_read | 0.05x |
| DeepSeek-V4.1-Flash | 256 | per_region | sram | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4-perregion | 184,900 | 1.00 | 4.92 | 270,585.4 | 1.463 | weight_read | 0.46x |
| DeepSeek-V4.1-Flash | 256 | per_region | rom | DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4-perregion-romfill | 184,900 | 1.04 | 4.92 | 279,561.3 | 1.512 | weight_read | 0.47x |

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
| DeepSeek-V4.1-Flash | 1 | 215 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 2 | 215 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 4 | 227 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 8 | 227 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 16 | 227 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 32 | 227 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 64 | 227 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash | 256 | 237 | 1.08 | 1.001 | 1.005 | 1.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash | 1 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4.1-Flash | 2 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4.1-Flash | 4 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4.1-Flash | 8 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4.1-Flash | 16 | 8 | 6.37 | 3.69 | 1.73x |
| DeepSeek-V4.1-Flash | 32 | 8 | 7.65 | 4.39 | 1.74x |
| DeepSeek-V4.1-Flash | 64 | 8 | 7.98 | 5.05 | 1.58x |
| DeepSeek-V4.1-Flash | 256 | 8 | 8.00 | 6.09 | 1.31x |
| DeepSeek-V4.1-Flash | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4.1-Flash | 256 | 56 | 21.37 | 10.48 | 2.04x |
| DeepSeek-V4.1-Flash | 1 | 107 | 5.86 | 5.32 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 107 | 5.86 | 5.32 | 1.10x |
| DeepSeek-V4.1-Flash | 4 | 107 | 5.86 | 5.32 | 1.10x |
| DeepSeek-V4.1-Flash | 8 | 107 | 5.86 | 5.32 | 1.10x |
| DeepSeek-V4.1-Flash | 16 | 107 | 5.86 | 5.32 | 1.10x |
| DeepSeek-V4.1-Flash | 32 | 107 | 5.86 | 5.32 | 1.10x |
| DeepSeek-V4.1-Flash | 64 | 107 | 5.86 | 5.32 | 1.10x |
| DeepSeek-V4.1-Flash | 256 | 107 | 13.36 | 8.94 | 1.49x |
| DeepSeek-V4.1-Flash | 1 | 108 | 5.86 | 5.33 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 108 | 5.86 | 5.33 | 1.10x |
| DeepSeek-V4.1-Flash | 4 | 108 | 5.86 | 5.33 | 1.10x |
| DeepSeek-V4.1-Flash | 8 | 108 | 5.86 | 5.33 | 1.10x |
| DeepSeek-V4.1-Flash | 16 | 108 | 5.86 | 5.33 | 1.10x |
| DeepSeek-V4.1-Flash | 32 | 108 | 5.86 | 5.33 | 1.10x |
| DeepSeek-V4.1-Flash | 64 | 108 | 5.86 | 5.33 | 1.10x |
| DeepSeek-V4.1-Flash | 256 | 108 | 13.25 | 8.92 | 1.49x |
| DeepSeek-V4.1-Flash | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash | 4 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash | 8 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash | 16 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash | 32 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash | 64 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash | 256 | 111 | 12.94 | 8.86 | 1.46x |
| DeepSeek-V4.1-Flash | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash | 4 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash | 8 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash | 16 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash | 32 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash | 64 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash | 256 | 112 | 12.84 | 8.85 | 1.45x |
| DeepSeek-V4.1-Flash | 1 | 114 | 5.87 | 5.36 | 1.10x |
| DeepSeek-V4.1-Flash | 2 | 114 | 5.87 | 5.36 | 1.10x |
| DeepSeek-V4.1-Flash | 4 | 114 | 5.87 | 5.36 | 1.10x |
| DeepSeek-V4.1-Flash | 8 | 114 | 5.87 | 5.36 | 1.10x |
| DeepSeek-V4.1-Flash | 16 | 114 | 5.87 | 5.36 | 1.10x |
| DeepSeek-V4.1-Flash | 32 | 114 | 5.87 | 5.36 | 1.10x |
| DeepSeek-V4.1-Flash | 64 | 114 | 5.87 | 5.36 | 1.10x |
| DeepSeek-V4.1-Flash | 256 | 114 | 12.64 | 8.81 | 1.44x |
| DeepSeek-V4.1-Flash | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash | 2 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash | 4 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash | 8 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash | 16 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash | 32 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash | 64 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4.1-Flash | 256 | 116 | 12.45 | 8.77 | 1.42x |
| DeepSeek-V4.1-Flash | 1 | 130 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash | 2 | 130 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash | 4 | 130 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash | 8 | 130 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash | 16 | 130 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash | 32 | 130 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash | 64 | 130 | 5.89 | 5.43 | 1.08x |
| DeepSeek-V4.1-Flash | 256 | 130 | 11.25 | 8.49 | 1.33x |
| DeepSeek-V4.1-Flash | 1 | 141 | 5.89 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash | 2 | 141 | 5.89 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash | 4 | 141 | 5.89 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash | 8 | 141 | 5.89 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash | 16 | 141 | 5.89 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash | 32 | 141 | 5.89 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash | 64 | 141 | 5.89 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash | 256 | 141 | 10.45 | 8.25 | 1.27x |
| DeepSeek-V4.1-Flash | 1 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash | 4 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash | 8 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash | 16 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash | 32 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash | 64 | 156 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4.1-Flash | 256 | 156 | 9.53 | 7.91 | 1.20x |
| DeepSeek-V4.1-Flash | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash | 4 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash | 8 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash | 16 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash | 32 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash | 64 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash | 256 | 168 | 8.89 | 7.62 | 1.17x |
| DeepSeek-V4.1-Flash | 1 | 169 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4.1-Flash | 2 | 169 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4.1-Flash | 4 | 169 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4.1-Flash | 8 | 169 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4.1-Flash | 16 | 169 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4.1-Flash | 32 | 169 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4.1-Flash | 64 | 169 | 5.91 | 5.55 | 1.07x |
| DeepSeek-V4.1-Flash | 256 | 169 | 8.84 | 7.59 | 1.16x |
| DeepSeek-V4.1-Flash | 1 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4.1-Flash | 4 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4.1-Flash | 8 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4.1-Flash | 16 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4.1-Flash | 32 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4.1-Flash | 64 | 207 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4.1-Flash | 256 | 207 | 7.29 | 6.69 | 1.09x |
| DeepSeek-V4.1-Flash | 1 | 212 | 5.93 | 5.63 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 212 | 5.93 | 5.63 | 1.05x |
| DeepSeek-V4.1-Flash | 4 | 212 | 5.93 | 5.63 | 1.05x |
| DeepSeek-V4.1-Flash | 8 | 212 | 5.93 | 5.63 | 1.05x |
| DeepSeek-V4.1-Flash | 16 | 212 | 5.93 | 5.63 | 1.05x |
| DeepSeek-V4.1-Flash | 32 | 212 | 5.93 | 5.63 | 1.05x |
| DeepSeek-V4.1-Flash | 64 | 212 | 5.93 | 5.63 | 1.05x |
| DeepSeek-V4.1-Flash | 256 | 212 | 7.13 | 6.58 | 1.08x |
| DeepSeek-V4.1-Flash | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 4 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 8 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 16 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 32 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 64 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 256 | 224 | 6.76 | 6.32 | 1.07x |
| DeepSeek-V4.1-Flash | 1 | 225 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 225 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 4 | 225 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 8 | 225 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 16 | 225 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 32 | 225 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 64 | 225 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash | 256 | 225 | 6.73 | 6.30 | 1.07x |
| DeepSeek-V4.1-Flash | 1 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash | 2 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash | 4 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash | 8 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash | 16 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash | 32 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash | 64 | 234 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4.1-Flash | 256 | 234 | 6.48 | 6.11 | 1.06x |
| DeepSeek-V4.1-Flash | 1 | 311 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4.1-Flash | 2 | 311 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4.1-Flash | 4 | 311 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4.1-Flash | 8 | 311 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4.1-Flash | 16 | 311 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4.1-Flash | 32 | 311 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4.1-Flash | 64 | 311 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4.1-Flash | 256 | 311 | 5.95 | 5.74 | 1.04x |
| DeepSeek-V4.1-Flash | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 2 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 4 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 8 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 16 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 32 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 64 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 256 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 2 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 4 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 8 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 16 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 32 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 64 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 256 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 1 | 337 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 2 | 337 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 4 | 337 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 8 | 337 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 16 | 337 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 32 | 337 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 64 | 337 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 256 | 337 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash | 2 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash | 4 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash | 8 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash | 16 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash | 32 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash | 64 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash | 256 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash | 2 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash | 4 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash | 8 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash | 16 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash | 32 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash | 64 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash | 256 | 672 | 5.98 | 5.88 | 1.02x |

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
| gpu | DeepSeek-V4.1-Flash | 1 | 10.05 | 0.8% |
| rom | DeepSeek-V4.1-Flash | 1 | 10.05 | 4.1% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash | sram | interleaved | 128 B | 1.77x |
| DeepSeek-V4.1-Flash | hbm | interleaved | 32 B | 1.34x |

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
| DeepSeek-V4.1-Flash | 1 | 215 | 26.51% | 241.60 | 4.24 |
| DeepSeek-V4.1-Flash | 2 | 215 | 26.51% | 241.60 | 4.24 |
| DeepSeek-V4.1-Flash | 4 | 4 | 0.94% | 9.00 | 4.24 |
| DeepSeek-V4.1-Flash | 8 | 4 | 0.94% | 9.00 | 4.24 |
| DeepSeek-V4.1-Flash | 16 | 4 | 0.94% | 9.00 | 4.24 |
| DeepSeek-V4.1-Flash | 32 | 4 | 0.94% | 9.00 | 4.24 |
| DeepSeek-V4.1-Flash | 64 | 4 | 0.94% | 9.00 | 4.24 |

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
| DeepSeek-V4.1-Flash | 1 | 1.56% | 13.0 GB | 2.55% | 378.21 TB/s | 14,805.75 TB/s | 228.3 | 26,024.2 |
| DeepSeek-V4.1-Flash | 2 | 1.56% | 13.0 GB | 2.55% | 378.21 TB/s | 14,805.75 TB/s | 228.3 | 26,024.2 |
| DeepSeek-V4.1-Flash | 4 | 1.56% | 13.0 GB | 2.55% | 378.21 TB/s | 14,805.75 TB/s | 228.3 | 26,024.2 |
| DeepSeek-V4.1-Flash | 8 | 1.56% | 13.0 GB | 2.55% | 378.21 TB/s | 14,805.75 TB/s | 228.3 | 26,024.2 |
| DeepSeek-V4.1-Flash | 16 | 1.56% | 13.0 GB | 2.55% | 378.21 TB/s | 14,805.75 TB/s | 228.3 | 26,024.2 |
| DeepSeek-V4.1-Flash | 32 | 1.56% | 13.0 GB | 2.55% | 378.21 TB/s | 14,805.75 TB/s | 228.3 | 26,024.2 |
| DeepSeek-V4.1-Flash | 64 | 1.56% | 13.0 GB | 2.55% | 378.21 TB/s | 14,805.75 TB/s | 228.3 | 26,024.2 |
| DeepSeek-V4.1-Flash | 256 | 3.47% | 18.6 GB | 3.64% | 538.42 TB/s | 14,805.75 TB/s | 201.9 | 51,698.9 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | link_latency | 183 |
| gpu | weight_read | 385 |
| rom | compute | 63 |
| rom | infeasible | 798 |
| rom | link_latency | 442 |
| rom | weight_read | 569 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 798 |

## Mechanical consistency audit

**PASS** over 51,749 checks.

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

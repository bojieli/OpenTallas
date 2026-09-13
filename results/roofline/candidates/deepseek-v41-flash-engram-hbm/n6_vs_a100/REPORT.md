# Area-constrained roofline: n6_vs_a100-deepseek-v41-flash-engram-hbm

> CANDIDATE MODEL under n6_vs_a100: DeepSeek-V4.1-Flash-engram-hbm at 200,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 490x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 2 devices. On the GPU side the correction reaches 817x (a100_sxm_80gb-x1007-pipeline, 1,007 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 103 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4.1-Flash-engram-hbm takes 2 x 46,225 mm2 (92,450 mm2, wafer, KV in HBM) at 4,070 tok/s per user and 44 tok/s per 1,000 mm2, holding 5,731 sessions, against 112 copies of one unified HBM die at the same silicon: 5.7x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4.1-Flash-engram-hbm on 277,350 mm2 of ROM silicon at 3,708 tok/s per user against 277,536 mm2 of a100_sxm_80gb-x336-tensor at 605 tok/s: **6.1x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 19,437 resident sessions against the GPU cluster's 131,052. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 193.94x to it.** At 554,700 mm2 on DeepSeek-V4.1-Flash-engram-hbm the pipeline-only GPU delivers 3.15 tok/s and the same silicon running tensor delivers 611 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.74x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `link_latency`) to 89.97x (DeepSeek-V4.1-Flash-engram-hbm, ROM binding on `link_latency`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4.1-Flash-engram-hbm engages 4.2% of its ROM array at batch 1 and 8.0% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 339 to 24,690 tok/s, and its rate with every slot occupied from 24,051 to 24,690. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 71 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,154 us over NVLink, capping per-user decode at 866 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 964.9 us and cap it at 1,036 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 8 of 8 operating points and an array 0; on tokens per second per square millimetre the same points go 0 to the array and 8 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 6 of 1969 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 23.0x of aggregate throughput (DeepSeek-V4.1-Flash-engram-hbm). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 11.62x, on DeepSeek-V4.1-Flash-engram-hbm at batch 256, where the busiest region carries 3.18x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 16 of 16 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4.1-Flash-engram-hbm at 200,000 tokens

**Recommended: `ROM-N6-native-HBMKV-wafer-hybrid-x2`** -- 2 x 46,225 mm2 wafers, 92,450 mm2 total, `hybrid`-parallel, KV in HBM, spare silicon to `sram`.

- **4,069.8 tok/s per user** (0.25 ms/token), binding on `link_latency`
- **44.0 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 8,140 tok/s aggregate with every slot full, over 5,731 resident sessions (fill limited by `pipeline_slots`)
- 8,453 W at 0.091 W/mm2, 1,038.5 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 112 copies of one unified HBM die -- `a100_sxm_80gb-x112-tensor`, 92,512 mm2, area ratio 0.9993 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 92,450 | 92,512 | 0.9993 |
| user tok/s | 4,069.8 | 719.2 | 5.66x |
| aggregate tok/s | 8,140 | 719 | 11.32x |
| resident sessions | 5,731 | 41,801 | -- |
| J/token | 1.0385 | 23.8650 | 23.0x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 5,731 sessions against one that holds 41,801 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x280-tensor` at 231,280 mm2 and 749.7 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 44.0 | 5,731 | 5.66x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 44.0 | 5,731 | 5.66x |
| smallest feasible machine | `ROM-N6-native-HBMKV-array-hybrid-x71` | 57,865 | 1,254.4 | 21.7 | 27,167 | 1.81x |
| **after -- this report's rule** | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 44.0 | 5,731 | 5.66x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-HBMKV-wafer-hybrid-x2` **<-- recommended** | 92,450 | 2 | 4,069.8 | 8,140 | 44.0 | 5,731 | `link_latency` | 8,453 | 1,038.5 | `a100_sxm_80gb-x112-tensor` | 5.66x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 114 | densest | `ROM-N6-native-HBMKV-array-hybrid-x72` | 58,680 | 1,279.8 | 21.8 | 27,565 |
| array | 114 | fastest | `ROM-N6-native-HBMKV-array-hybrid-x72` | 58,680 | 1,279.8 | 21.8 | 27,565 |
| array | 114 | smallest | `ROM-N6-native-HBMKV-array-hybrid-x71` | 57,865 | 1,254.4 | 21.7 | 27,167 |
| wafer | 69 | densest | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 44.0 | 5,731 |
| wafer | 69 | fastest | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 44.0 | 5,731 |
| wafer | 69 | smallest | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 44.0 | 5,731 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hybrid-x72` | 58,680 | 1,279.8 | 11,518 | 27,565 | 4,365 | 379.0 | `link_latency` | `a100_sxm_80gb-x71-tensor` | 693.2 | 25,465 | 16,167.1 | 1.001 | 1.85x | 42.7x |
| 1 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 8,140 | 5,731 | 8,453 | 1,038.5 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 719.2 | 41,801 | 23,865.0 | 0.999 | 5.66x | 23.0x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-tensor-x113` | 92,095 | 1,146.7 | 1,147 | 43,902 | 9,657 | 8,421.8 | `link_latency` | `a100_sxm_80gb-x111-tensor` | 718.7 | 41,403 | 23,678.5 | 1.004 | 1.60x | 2.8x |
| 1 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | -- | 5,731 | -- | 1,038.5 | -- | -- | -- | -- | -- | 0.996 | 3.55x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hybrid-x72` | 58,680 | 1,279.8 | 11,518 | 27,565 | 4,365 | 379.0 | `link_latency` | `a100_sxm_80gb-x71-tensor` | 578.3 | 25,465 | 9,790.9 | 1.001 | 2.21x | 25.8x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | 8,140 | 5,731 | 8,453 | 1,038.5 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 612.2 | 41,801 | 14,133.6 | 0.999 | 6.65x | 13.6x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-tensor-x113` | 92,095 | 1,029.9 | 2,060 | 43,902 | 9,666 | 4,692.6 | `link_latency` | `a100_sxm_80gb-x111-tensor` | 611.6 | 41,403 | 14,029.9 | 1.004 | 1.68x | 3.0x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,069.8 | -- | 5,731 | -- | 1,038.5 | -- | -- | -- | -- | -- | 0.996 | 3.95x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hybrid-x72` | 58,680 | 1,279.8 | 11,518 | 27,565 | 4,365 | 379.0 | `link_latency` | `a100_sxm_80gb-x71-tensor` | 453.2 | 25,465 | 6,351.5 | 1.001 | 2.82x | 16.8x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,068.7 | 16,275 | 5,731 | 8,532 | 524.2 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 478.7 | 41,801 | 9,140.8 | 0.999 | 8.50x | 17.4x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x113` | 92,095 | 974.9 | 14,623 | 43,902 | 9,823 | 671.7 | `weight_read` | `a100_sxm_80gb-x111-tensor` | 478.2 | 41,403 | 9,074.7 | 1.004 | 2.04x | 13.5x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,068.7 | -- | 5,731 | -- | 524.2 | -- | -- | -- | -- | -- | 0.996 | 4.17x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hybrid-x72` | 58,680 | 1,279.8 | 11,518 | 27,565 | 4,365 | 379.0 | `link_latency` | `a100_sxm_80gb-x71-tensor` | 334.5 | 25,465 | 4,400.9 | 1.001 | 3.83x | 11.6x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,066.4 | 32,532 | 5,731 | 8,687 | 267.0 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 358.7 | 41,801 | 6,204.6 | 0.999 | 11.34x | 23.2x |
| 8 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x113` | 92,095 | 974.9 | 14,623 | 43,902 | 9,823 | 671.7 | `weight_read` | `a100_sxm_80gb-x111-tensor` | 358.2 | 41,403 | 6,162.3 | 1.004 | 2.72x | 9.2x |
| 8 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,066.4 | -- | 5,731 | -- | 267.0 | -- | -- | -- | -- | -- | 0.996 | 4.17x wafer/array | -- |
| 16 | array | `ROM-N6-native-HBMKV-array-hybrid-x87` | 70,905 | 1,152.1 | 18,434 | 33,542 | 6,418 | 348.1 | `link_latency` | `a100_sxm_80gb-x86-tensor` | 237.7 | 31,442 | 3,752.4 | 0.998 | 4.85x | 10.8x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,061.9 | 64,991 | 5,731 | 8,996 | 138.4 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 247.6 | 41,801 | 4,569.6 | 0.999 | 16.41x | 33.0x |
| 16 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x113` | 92,095 | 974.0 | 15,585 | 43,902 | 9,832 | 630.9 | `weight_read` | `a100_sxm_80gb-x111-tensor` | 247.2 | 41,403 | 4,539.3 | 1.004 | 3.94x | 7.2x |
| 16 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,061.9 | -- | 5,731 | -- | 138.4 | -- | -- | -- | -- | -- | 0.996 | 4.17x wafer/array | -- |
| 32 | array | `ROM-N6-native-HBMKV-array-hybrid-x87` | 70,905 | 1,130.8 | 36,184 | 33,542 | 6,587 | 182.0 | `link_latency` | `a100_sxm_80gb-x86-tensor` | 154.0 | 31,442 | 2,932.8 | 0.998 | 7.34x | 16.1x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,052.9 | 129,694 | 5,731 | 9,604 | 74.1 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 160.1 | 41,801 | 3,568.2 | 0.999 | 25.31x | 48.2x |
| 32 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x113` | 92,095 | 961.2 | 30,757 | 43,902 | 9,977 | 324.4 | `weight_read` | `a100_sxm_80gb-x111-tensor` | 159.9 | 41,403 | 3,544.8 | 1.004 | 6.01x | 10.9x |
| 32 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,052.9 | -- | 5,731 | -- | 74.1 | -- | -- | -- | -- | -- | 0.996 | 4.22x wafer/array | -- |
| 64 | array | `ROM-N6-native-HBMKV-array-hybrid-x87` | 70,905 | 1,090.4 | 69,783 | 33,542 | 6,907 | 99.0 | `link_latency` | `a100_sxm_80gb-x86-tensor` | 95.3 | 31,442 | 2,359.2 | 0.998 | 11.44x | 23.8x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 3,808.0 | 243,714 | 12,584 | 19,543 | 80.2 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 105.0 | 86,427 | 5,135.1 | 0.999 | 36.25x | 64.0x |
| 64 | array @ wafer area | `ROM-N6-native-HBMKV-array-hybrid-x227-romfill` | 185,005 | 885.3 | 56,658 | 89,324 | 21,160 | 373.5 | `weight_read` | `a100_sxm_80gb-x224-tensor` | 105.0 | 86,427 | 5,135.1 | 1.000 | 8.43x | 13.7x |
| 64 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 3,808.0 | -- | 12,584 | -- | 80.2 | -- | -- | -- | -- | -- | 1.001 | 4.30x wafer/array | -- |
| 256 | array | `ROM-N6-native-HBMKV-array-hybrid-x340-romfill` | 277,100 | 817.6 | 209,316 | 80,160 | 30,511 | 145.8 | `link_latency` | `a100_sxm_80gb-x335-tensor` | 33.5 | 130,654 | 5,775.1 | 1.001 | 24.43x | 39.6x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,038.1 | 777,756 | 39,997 | 59,007 | 75.9 | `link_latency` | `a100_sxm_80gb-x672-tensor` | 33.8 | 264,929 | 11,352.9 | 0.999 | 89.97x | 149.6x |

**One design wins at every batch this study evaluates.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1-256 | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | wafer | HBM | 5,731 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | rom | 71, 72, 87, 104, 113, 138, 170, 207, 227, 276, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | HBM | sram | 71, 72, 87, 104, 113, 138, 170, 207, 227, 276, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | rom | 166, 167, 170, 205, 227, 246, 328, 340 |
| DeepSeek-V4.1-Flash-engram-hbm | SRAM | sram | 166, 167, 170, 205, 227, 246, 328, 340 |

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

- **0 of 1,969 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 71% of its cooling budget, and the busiest wafer-scale ROM design 30%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 16 | 0 | 63.6% | 70.7% | 0.342 | 57% |
| gpu | wafer (>=40,000 mm2) | 720 | 0 | 38.8% | 53.8% | 0.260 | 93% |
| rom | wafer (>=40,000 mm2) | 1,233 | 0 | 18.8% | 29.7% | 0.148 | 99% |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 92,450 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.038539 | 8,453.4 | link_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor` | 23.864992 | 17,162.7 | link_latency | 22.98x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 92,450 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 1.038539 | 8,453.4 | link_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor` | 14.133621 | 17,306.5 | link_latency | 13.61x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 92,450 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 0.524216 | 8,531.5 | link_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor` | 9.140810 | 17,504.0 | link_latency | 17.44x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 92,450 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 0.267039 | 8,687.2 | link_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor` | 6.204590 | 17,806.8 | link_latency | 23.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 92,450 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 0.138419 | 8,996.0 | link_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor` | 4.569610 | 18,101.7 | link_latency | 33.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 92,450 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2` | 0.074052 | 9,604.0 | link_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor` | 3.568190 | 18,283.9 | link_latency | 48.19x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 138,675 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 0.064161 | 15,150.0 | link_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-tensor` | 4.019693 | 26,383.2 | link_latency | 62.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 554,700 | `DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.075869 | 59,007.3 | link_latency | `DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-tensor` | 11.352920 | 98,139.7 | link_latency | 149.64x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 200,000 | 552 B | 307.5 GB | 4.46 | 0.047 GB | 0.181 GB | 278.7 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 92,450 | 18,789.4 | wafer-pipeline | 4,069.8 | wafer-hybrid | 4.62x | 1,502.1 | pipeline | 719.2 | tensor | 2.09x | 12.51x | 5.66x | 0.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 3 | 138,675 | 23,989.8 | wafer-pipeline | 3,929.9 | wafer-hybrid | 6.10x | 1,581.5 | pipeline | 735.6 | tensor | 2.15x | 15.17x | 5.34x | 0.35x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 184,900 | 28,575.5 | wafer-pipeline | 3,853.1 | wafer-hybrid | 7.42x | 1,625.3 | pipeline | 744.3 | tensor | 2.18x | 17.58x | 5.18x | 0.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 6 | 277,350 | 35,328.7 | wafer-pipeline | 3,708.3 | wafer-hybrid | 9.53x | 1,672.2 | pipeline | 605.2 | tensor | 2.76x | 21.13x | 6.13x | 0.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 369,800 | 40,062.7 | wafer-pipeline | 3,573.9 | wafer-hybrid | 11.21x | 1,697.0 | pipeline | 608.2 | tensor | 2.79x | 23.61x | 5.88x | 0.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 12 | 554,700 | 46,261.7 | wafer-pipeline | 3,332.5 | wafer-hybrid | 13.88x | 1,722.7 | pipeline | 611.3 | tensor | 2.82x | 26.85x | 5.45x | 0.20x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.20x to 0.45x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,069.8 | 8,139.7 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 823.25 | 719.2 | 719.2 | link_latency | 5.66x | 11.32x | 254.43x | 5.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hybrid-x71 | 57,865 | 1,254.4 | 11,289.7 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-tensor | 57,820 | 1.00x | tensor | 819.35 | 692.2 | 692.2 | link_latency | 1.81x | 16.31x | 54.17x | 1.81x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,069.8 | 8,139.7 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 921.70 | 612.2 | 1,224.5 | link_latency | 6.65x | 6.65x | 254.43x | 6.65x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hybrid-x71 | 57,865 | 1,254.4 | 11,289.7 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-tensor | 57,820 | 1.00x | tensor | 913.90 | 577.0 | 1,154.1 | link_latency | 2.17x | 9.78x | 54.17x | 2.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,068.7 | 16,274.8 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 1,118.60 | 478.7 | 1,914.9 | link_latency | 8.50x | 8.50x | 254.36x | 8.50x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hybrid-x71 | 57,865 | 1,254.4 | 11,289.7 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-tensor | 57,820 | 1.00x | tensor | 1,103.00 | 452.2 | 1,808.7 | link_latency | 2.77x | 6.24x | 54.17x | 2.77x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,066.4 | 32,531.6 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 1,512.40 | 358.7 | 2,869.9 | link_latency | 11.34x | 11.34x | 254.22x | 11.34x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hybrid-x71 | 57,865 | 1,254.4 | 11,289.7 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-tensor | 57,820 | 1.00x | tensor | 1,481.19 | 333.6 | 2,668.5 | link_latency | 3.76x | 4.23x | 54.17x | 3.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,061.9 | 64,990.9 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 2,300.00 | 247.6 | 3,961.3 | link_latency | 16.41x | 16.41x | 253.94x | 16.41x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hybrid-x71 | 57,865 | 921.1 | 14,737.7 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-tensor | 57,820 | 1.00x | tensor | 2,237.59 | 229.5 | 3,671.8 | link_latency | 4.01x | 4.01x | 39.77x | 4.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,052.9 | 129,693.7 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 3,875.21 | 160.1 | 5,124.1 | link_latency | 25.31x | 25.31x | 253.37x | 25.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hybrid-x71 | 57,865 | 573.1 | 18,337.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-tensor | 57,820 | 1.00x | tensor | 3,750.38 | 148.8 | 4,761.5 | link_latency | 3.85x | 3.85x | 24.74x | 3.85x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 3,808.0 | 243,713.9 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 7,250.31 | 105.0 | 6,722.4 | link_latency | 36.25x | 36.25x | 432.68x | 36.25x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-pipeline-x71 | 57,865 | 338.8 | 24,051.3 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-tensor | 57,820 | 1.00x | tensor | 6,775.96 | 92.7 | 5,929.7 | link_latency | 3.66x | 4.06x | 14.63x | 3.66x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | fastest | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,038.1 | 777,756.2 | link_latency | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 27,750.84 | 33.8 | 8,644.4 | link_latency | 89.97x | 89.97x | 963.93x | 89.97x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | smallest silicon | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-pipeline-x71 | 57,865 | 96.4 | 24,689.9 | compute | DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | 57,820 | 1.00x | hybrid | 713.34 | 38.6 | 9,882.0 | weight_read | 2.50x | 2.50x | 7.16x | 2.50x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 6,608 | 79.9 | 505.5 | — | tensor | 407.17 | 20.6% | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 56 | 46,256 | 27.3 | 676.1 | 200.0 | tensor | 816.23 | 55.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 70 | 57,820 | 23.2 | 692.2 | 167.4 | tensor | 819.35 | 56.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 71 | 58,646 | 22.9 | 693.2 | 167.9 | tensor | 819.35 | 56.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 86 | 71,036 | 19.8 | 705.1 | 145.0 | tensor | 821.34 | 57.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 103 | 85,078 | 17.1 | 715.0 | 128.2 | tensor | 822.71 | 58.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 111 | 91,686 | 16.1 | 718.7 | 121.0 | tensor | 823.25 | 59.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 112 | 92,512 | 16.0 | 719.2 | 121.2 | tensor | 823.25 | 59.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 136 | 112,336 | 13.6 | 727.7 | 103.8 | tensor | 824.49 | 60.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 142 | 117,292 | 13.1 | 729.4 | 98.9 | tensor | 824.81 | 60.2% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 150 | 123,900 | 12.5 | 731.5 | 94.6 | tensor | 825.10 | 60.4% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 164 | 135,464 | 11.6 | 734.7 | 87.0 | tensor | 825.59 | 60.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 165 | 136,290 | 11.5 | 734.9 | 87.0 | tensor | 825.59 | 60.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 168 | 138,768 | 11.3 | 735.6 | 87.2 | tensor | 825.59 | 60.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 202 | 166,852 | 9.7 | 741.3 | 72.5 | tensor | 826.49 | 61.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 204 | 168,504 | 9.6 | 741.7 | 72.5 | tensor | 826.49 | 61.3% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 224 | 185,024 | 8.8 | 744.3 | 68.2 | tensor | 826.76 | 61.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 243 | 200,718 | 8.2 | 746.3 | 62.2 | tensor | 827.10 | 61.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 211,456 | 7.8 | 747.6 | 60.6 | tensor | 827.20 | 61.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 272 | 224,672 | 7.4 | 749.0 | 57.4 | tensor | 827.38 | 62.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 280 | 231,280 | 7.2 | 749.7 | 55.9 | tensor | 827.46 | 62.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 324 | 267,624 | 6.3 | 604.8 | 48.5 | tensor | 1,152.67 | 69.7% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 335 | 276,710 | 6.1 | 605.2 | 47.4 | tensor | 1,152.73 | 69.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 336 | 277,536 | 6.1 | 605.2 | 47.5 | tensor | 1,152.73 | 69.8% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 377 | 311,402 | 5.5 | 606.5 | 42.0 | tensor | 1,153.02 | 69.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 380 | 313,880 | 5.4 | 606.6 | 42.0 | tensor | 1,153.02 | 69.9% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 392 | 323,792 | 5.3 | 606.9 | 41.2 | tensor | 1,153.07 | 70.0% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 448 | 370,048 | 4.6 | 608.2 | 36.4 | tensor | 1,153.32 | 70.1% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 616 | 508,816 | 3.4 | 610.7 | 27.0 | tensor | 1,153.80 | 70.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 672 | 555,072 | 3.2 | 611.3 | 24.9 | tensor | 1,153.90 | 70.5% | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 1007 | 831,782 | 2.1 | 613.3 | 16.9 | tensor | 1,154.29 | 70.8% | link_latency |

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
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-pipeline-x167 | DeepSeek-V4.1-Flash-engram-hbm | 167 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-pipeline-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | pipeline | on_wafer | inter_wafer | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-tensor-x166 | DeepSeek-V4.1-Flash-engram-hbm | 166 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-tensor-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | tensor | on_wafer | inter_wafer | 160 | 964.92 us | 103.6 tok/s | 1,036.4 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 3 on inter_wafer (traversals 2.0) = 810.92 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-array-hybrid-x167 | DeepSeek-V4.1-Flash-engram-hbm | 167 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | DeepSeek-V4.1-Flash-engram-hbm | 3 | hybrid | on_wafer | inter_wafer | 82 | 164.14 us | 609.2 tok/s | 6,092.5 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 2 x point_to_point span 2 on inter_wafer (traversals 1.0) = 10.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-pipeline-x72 | DeepSeek-V4.1-Flash-engram-hbm | 72 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | pipeline | on_wafer | inter_wafer | 39 | 4.88 us | 20,512.8 tok/s | 205,127.6 tok/s | 39 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.88 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-tensor-x71 | DeepSeek-V4.1-Flash-engram-hbm | 71 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-tensor-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | tensor | on_wafer | inter_wafer | 160 | 962.19 us | 103.9 tok/s | 1,039.3 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 80 x all_reduce span 2 on inter_wafer (traversals 2.0) = 808.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-array-hybrid-x72 | DeepSeek-V4.1-Flash-engram-hbm | 72 | hybrid | nvlink3 | infiniband_hdr | 88 | 426.68 us | 234.4 tok/s | 2,343.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.52 us |
| DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | DeepSeek-V4.1-Flash-engram-hbm | 2 | hybrid | on_wafer | inter_wafer | 81 | 159.07 us | 628.7 tok/s | 6,286.6 tok/s | 80 x all_reduce span 57 on on_wafer (traversals 15.4) = 154.00 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.07 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x8-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 8 | pipeline | nvlink3 | infiniband_hdr | 7 | 17.74 us | 5,637.3 tok/s | 56,373.2 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 17.74 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x8-tensor | DeepSeek-V4.1-Flash-engram-hbm | 8 | tensor | nvlink3 | infiniband_hdr | 80 | 407.17 us | 245.6 tok/s | 2,456.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 56 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-tensor | DeepSeek-V4.1-Flash-engram-hbm | 56 | tensor | nvlink3 | infiniband_hdr | 160 | 816.23 us | 122.5 tok/s | 1,225.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 409.06 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x56-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 56 | hybrid | nvlink3 | infiniband_hdr | 86 | 421.81 us | 237.1 tok/s | 2,370.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 70 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-tensor | DeepSeek-V4.1-Flash-engram-hbm | 70 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x70-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 70 | hybrid | nvlink3 | infiniband_hdr | 88 | 426.68 us | 234.4 tok/s | 2,343.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.52 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 71 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-tensor | DeepSeek-V4.1-Flash-engram-hbm | 71 | tensor | nvlink3 | infiniband_hdr | 160 | 819.35 us | 122.0 tok/s | 1,220.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 412.18 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x71-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 71 | hybrid | nvlink3 | infiniband_hdr | 88 | 426.68 us | 234.4 tok/s | 2,343.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.52 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 86 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-tensor | DeepSeek-V4.1-Flash-engram-hbm | 86 | tensor | nvlink3 | infiniband_hdr | 160 | 821.34 us | 121.8 tok/s | 1,217.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 414.17 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x86-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 86 | hybrid | nvlink3 | infiniband_hdr | 90 | 431.56 us | 231.7 tok/s | 2,317.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.40 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x103-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 103 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x103-tensor | DeepSeek-V4.1-Flash-engram-hbm | 103 | tensor | nvlink3 | infiniband_hdr | 160 | 822.71 us | 121.5 tok/s | 1,215.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 415.54 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x103-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 103 | hybrid | nvlink3 | infiniband_hdr | 92 | 436.44 us | 229.1 tok/s | 2,291.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 29.28 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x111-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 111 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x111-tensor | DeepSeek-V4.1-Flash-engram-hbm | 111 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x111-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 111 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 112 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-tensor | DeepSeek-V4.1-Flash-engram-hbm | 112 | tensor | nvlink3 | infiniband_hdr | 160 | 823.25 us | 121.5 tok/s | 1,214.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 416.08 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x112-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 112 | hybrid | nvlink3 | infiniband_hdr | 93 | 438.88 us | 227.9 tok/s | 2,278.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 31.71 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 136 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-tensor | DeepSeek-V4.1-Flash-engram-hbm | 136 | tensor | nvlink3 | infiniband_hdr | 160 | 824.49 us | 121.3 tok/s | 1,212.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 417.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x136-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 136 | hybrid | nvlink3 | infiniband_hdr | 96 | 446.20 us | 224.1 tok/s | 2,241.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.03 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x142-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 142 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x142-tensor | DeepSeek-V4.1-Flash-engram-hbm | 142 | tensor | nvlink3 | infiniband_hdr | 160 | 824.81 us | 121.2 tok/s | 1,212.4 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 417.64 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x142-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 142 | hybrid | nvlink3 | infiniband_hdr | 97 | 448.64 us | 222.9 tok/s | 2,229.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 41.47 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x150-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 150 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x150-tensor | DeepSeek-V4.1-Flash-engram-hbm | 150 | tensor | nvlink3 | infiniband_hdr | 160 | 825.10 us | 121.2 tok/s | 1,212.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 417.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x150-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 150 | hybrid | nvlink3 | infiniband_hdr | 98 | 451.08 us | 221.7 tok/s | 2,216.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 43.91 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x164-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 164 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x164-tensor | DeepSeek-V4.1-Flash-engram-hbm | 164 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x164-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 164 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x165-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 165 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x165-tensor | DeepSeek-V4.1-Flash-engram-hbm | 165 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x165-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 165 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 168 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-tensor | DeepSeek-V4.1-Flash-engram-hbm | 168 | tensor | nvlink3 | infiniband_hdr | 160 | 825.59 us | 121.1 tok/s | 1,211.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 418.42 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x168-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 168 | hybrid | nvlink3 | infiniband_hdr | 100 | 455.96 us | 219.3 tok/s | 2,193.2 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 48.79 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x202-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 202 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x202-tensor | DeepSeek-V4.1-Flash-engram-hbm | 202 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x202-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 202 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 204 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-tensor | DeepSeek-V4.1-Flash-engram-hbm | 204 | tensor | nvlink3 | infiniband_hdr | 160 | 826.49 us | 121.0 tok/s | 1,209.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 419.32 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x204-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 204 | hybrid | nvlink3 | infiniband_hdr | 105 | 468.16 us | 213.6 tok/s | 2,136.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.99 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 224 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-tensor | DeepSeek-V4.1-Flash-engram-hbm | 224 | tensor | nvlink3 | infiniband_hdr | 160 | 826.76 us | 121.0 tok/s | 1,209.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 419.59 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x224-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 224 | hybrid | nvlink3 | infiniband_hdr | 107 | 473.04 us | 211.4 tok/s | 2,114.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.87 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x243-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 243 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x243-tensor | DeepSeek-V4.1-Flash-engram-hbm | 243 | tensor | nvlink3 | infiniband_hdr | 160 | 827.10 us | 120.9 tok/s | 1,209.0 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 419.93 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x243-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 243 | hybrid | nvlink3 | infiniband_hdr | 110 | 480.36 us | 208.2 tok/s | 2,081.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 73.19 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x256-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 256 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x256-tensor | DeepSeek-V4.1-Flash-engram-hbm | 256 | tensor | nvlink3 | infiniband_hdr | 160 | 827.20 us | 120.9 tok/s | 1,208.9 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 32 on infiniband_hdr (traversals 2.0) = 420.03 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x256-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 256 | hybrid | nvlink3 | infiniband_hdr | 111 | 482.80 us | 207.1 tok/s | 2,071.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 31 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 75.63 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 272 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-tensor | DeepSeek-V4.1-Flash-engram-hbm | 272 | tensor | nvlink3 | infiniband_hdr | 160 | 827.38 us | 120.9 tok/s | 1,208.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 34 on infiniband_hdr (traversals 2.0) = 420.21 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x272-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 272 | hybrid | nvlink3 | infiniband_hdr | 113 | 487.67 us | 205.1 tok/s | 2,050.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 33 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 80.51 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x280-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 280 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x280-tensor | DeepSeek-V4.1-Flash-engram-hbm | 280 | tensor | nvlink3 | infiniband_hdr | 160 | 827.46 us | 120.9 tok/s | 1,208.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 420.30 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x280-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 280 | hybrid | nvlink3 | infiniband_hdr | 114 | 490.11 us | 204.0 tok/s | 2,040.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.95 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x324-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 324 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x324-tensor | DeepSeek-V4.1-Flash-engram-hbm | 324 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.67 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 41 on infiniband_hdr (traversals 4.0) = 745.51 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x324-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 324 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 335 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-tensor | DeepSeek-V4.1-Flash-engram-hbm | 335 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x335-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 335 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 336 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-tensor | DeepSeek-V4.1-Flash-engram-hbm | 336 | tensor | nvlink3 | infiniband_hdr | 160 | 1,152.73 us | 86.8 tok/s | 867.5 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 745.56 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x336-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 336 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x377-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 377 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x377-tensor | DeepSeek-V4.1-Flash-engram-hbm | 377 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.02 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 745.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x377-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 377 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x380-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 380 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x380-tensor | DeepSeek-V4.1-Flash-engram-hbm | 380 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.02 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 745.86 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x380-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 380 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x392-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 392 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x392-tensor | DeepSeek-V4.1-Flash-engram-hbm | 392 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.07 us | 86.7 tok/s | 867.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 745.90 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x392-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 392 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 448 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-tensor | DeepSeek-V4.1-Flash-engram-hbm | 448 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.32 us | 86.7 tok/s | 867.1 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 746.15 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x448-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 448 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x616-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 616 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x616-tensor | DeepSeek-V4.1-Flash-engram-hbm | 616 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.80 us | 86.7 tok/s | 866.7 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 77 on infiniband_hdr (traversals 4.0) = 746.63 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x616-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 616 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 672 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-tensor | DeepSeek-V4.1-Flash-engram-hbm | 672 | tensor | nvlink3 | infiniband_hdr | 160 | 1,153.90 us | 86.7 tok/s | 866.6 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 746.73 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x672-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 672 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x1007-pipeline | DeepSeek-V4.1-Flash-engram-hbm | 1007 | pipeline | nvlink3 | infiniband_hdr | 39 | 98.45 us | 1,015.7 tok/s | 10,157.1 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.76 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x1007-tensor | DeepSeek-V4.1-Flash-engram-hbm | 1007 | tensor | nvlink3 | infiniband_hdr | 160 | 1,154.29 us | 86.6 tok/s | 866.3 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 80 x all_reduce span 126 on infiniband_hdr (traversals 4.0) = 747.12 us |
| DeepSeek-V4.1-Flash-engram-hbm/a100_sxm_80gb-x1007-hybrid | DeepSeek-V4.1-Flash-engram-hbm | 1007 | hybrid | nvlink3 | infiniband_hdr | 119 | 502.31 us | 199.1 tok/s | 1,990.8 tok/s | 80 x all_reduce span 8 on nvlink3 (traversals 2.0) = 407.17 us; 39 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 95.14 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4.1-Flash-engram-hbm | 1 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,069.8 | 0.044 | 1,254.4 (57,865) | 4,069.8 (92,450) | 3.24x | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,069.8 | 0.044 | 1,254.4 (57,865) | 4,069.8 (92,450) | 3.24x | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,068.7 | 0.044 | 1,254.4 (57,865) | 4,068.7 (92,450) | 3.24x | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,066.4 | 0.044 | 1,254.4 (57,865) | 4,066.4 (92,450) | 3.24x | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,061.9 | 0.044 | 1,152.1 (70,905) | 4,061.9 (92,450) | 3.53x | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 4,052.9 | 0.044 | 1,130.8 (70,905) | 4,052.9 (92,450) | 3.58x | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 3,689.4 | 0.027 | 1,090.4 (70,905) | 3,689.4 (138,675) | 3.38x | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | wafer | wafer | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,038.1 | 0.005 | 781.2 (112,470) | 3,038.1 (554,700) | 3.89x | link_latency |

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
| DeepSeek-V4.1-Flash-engram-hbm | 384 | 752.0 MB | 164.9 mm2 | 29.69 mm2 (18.0%) | 63,336 mm2 | 11,400 mm2 | 67,448 mm2 = 82.8 reticles |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | sram | 26,098.2 | 26,053.8 | 26,053.8 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | sram | 26,098.2 | 26,053.8 | 26,053.8 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | sram | 26,098.2 | 26,053.8 | 26,053.8 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | sram | 32,531.6 | 26,053.8 | 26,053.8 | 1.25x | 1.00x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | sram | 64,990.9 | 26,053.8 | 43,719.5 | 2.49x | 1.68x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | sram | 129,693.7 | 26,053.8 | 75,224.9 | 4.98x | 2.89x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | sram | 219,290.0 | 26,053.8 | 124,709.7 | 8.42x | 4.79x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | sram | 590,694.2 | 26,073.5 | 303,100.5 | 22.66x | 11.62x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | rom | 149,001.6 | 33,762.0 | 33,762.0 | 4.41x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | rom | 149,001.6 | 33,762.0 | 33,762.0 | 4.41x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | rom | 149,001.6 | 33,762.0 | 33,762.0 | 4.41x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | rom | 149,001.6 | 33,762.0 | 33,762.0 | 4.41x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | rom | 149,001.6 | 33,762.0 | 49,655.6 | 4.41x | 1.47x | weight_read | weight_read | link_latency |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | rom | 149,001.6 | 33,762.0 | 86,906.8 | 4.41x | 2.57x | weight_read | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | rom | 243,713.9 | 33,762.0 | 146,703.8 | 7.22x | 4.35x | link_latency | weight_read | weight_read |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | rom | 777,756.2 | 33,795.1 | 368,967.0 | 23.01x | 10.92x | link_latency | weight_read | weight_read |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,098.2 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 149,001.6 | 0.269 | weight_read | 5.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,053.8 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.30 | 1.00 | 33,762.0 | 0.243 | weight_read | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,053.8 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 1.30 | 1.00 | 33,762.0 | 0.243 | weight_read | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,098.2 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 149,001.6 | 0.269 | weight_read | 5.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,053.8 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.30 | 1.00 | 33,762.0 | 0.243 | weight_read | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,053.8 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 1.30 | 1.00 | 33,762.0 | 0.243 | weight_read | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 26,098.2 | 0.047 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 149,001.6 | 0.269 | weight_read | 5.71x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,053.8 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.30 | 1.00 | 33,762.0 | 0.243 | weight_read | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,053.8 | 0.188 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 1.30 | 1.00 | 33,762.0 | 0.243 | weight_read | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 32,531.6 | 0.352 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 149,001.6 | 0.269 | weight_read | 4.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,053.8 | 0.188 | weight_read | 0.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.30 | 1.00 | 33,762.0 | 0.243 | weight_read | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 26,053.8 | 0.188 | weight_read | 0.80x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perregion-romfill | 138,675 | 1.30 | 1.00 | 33,762.0 | 0.243 | weight_read | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 64,990.9 | 0.703 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 149,001.6 | 0.269 | weight_read | 2.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,053.8 | 0.188 | weight_read | 0.40x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.30 | 1.00 | 33,762.0 | 0.243 | weight_read | 0.52x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 1.66 | 43,719.5 | 0.315 | weight_read | 0.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 1.30 | 1.66 | 49,655.6 | 0.358 | link_latency | 0.76x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 129,693.7 | 1.403 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 5.72 | 1.00 | 149,001.6 | 0.269 | weight_read | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,053.8 | 0.188 | weight_read | 0.20x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.30 | 1.00 | 33,762.0 | 0.243 | weight_read | 0.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 2.18 | 75,224.9 | 0.542 | weight_read | 0.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 1.30 | 2.18 | 86,906.8 | 0.627 | weight_read | 0.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 219,290.0 | 1.581 | link_latency | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 1.91 | 1.00 | 243,713.9 | 1.318 | link_latency | 1.11x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 26,053.8 | 0.188 | weight_read | 0.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.30 | 1.00 | 33,762.0 | 0.243 | weight_read | 0.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 2.93 | 124,709.7 | 0.899 | weight_read | 0.57x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 1.30 | 2.93 | 146,703.8 | 1.058 | weight_read | 0.67x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 590,694.2 | 2.130 | weight_read | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | batched | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 5.72 | 1.00 | 777,756.2 | 1.402 | link_latency | 1.32x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.50 | 26,073.5 | 0.188 | weight_read | 0.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_stream | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-pipeline-x3-perstream-romfill | 138,675 | 1.30 | 1.50 | 33,795.1 | 0.244 | weight_read | 0.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | sram | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 5.74 | 303,100.5 | 2.186 | weight_read | 0.51x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | per_region | rom | DeepSeek-V4.1-Flash-engram-hbm/ROM-N6-native-HBMKV-wafer-hybrid-x3-perregion-romfill | 138,675 | 1.30 | 5.74 | 368,967.0 | 2.661 | weight_read | 0.62x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 259 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 259 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 259 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 284 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 284 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 284 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 284 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 144 | 1.78 | 1.006 | 1.069 | 1.06x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 8 | 6.37 | 3.69 | 1.73x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 8 | 7.65 | 4.39 | 1.74x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 8 | 7.98 | 5.05 | 1.58x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 8 | 8.00 | 6.09 | 1.31x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 56 | 21.37 | 10.48 | 2.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 70 | 5.79 | 5.05 | 1.15x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 70 | 18.62 | 9.95 | 1.87x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 71 | 5.79 | 5.06 | 1.14x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 71 | 18.44 | 9.91 | 1.86x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 86 | 15.99 | 9.40 | 1.70x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 103 | 5.86 | 5.30 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 103 | 5.86 | 5.30 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 103 | 5.86 | 5.30 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 103 | 5.86 | 5.30 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 103 | 5.86 | 5.30 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 103 | 5.86 | 5.30 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 103 | 5.86 | 5.30 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 103 | 13.80 | 9.02 | 1.53x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 111 | 12.94 | 8.86 | 1.46x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 112 | 12.84 | 8.85 | 1.45x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 136 | 5.89 | 5.45 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 136 | 5.89 | 5.45 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 136 | 5.89 | 5.45 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 136 | 5.89 | 5.45 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 136 | 5.89 | 5.45 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 136 | 5.89 | 5.45 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 136 | 5.89 | 5.45 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 136 | 10.80 | 8.36 | 1.29x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 142 | 5.90 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 142 | 5.90 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 142 | 5.90 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 142 | 5.90 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 142 | 5.90 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 142 | 5.90 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 142 | 5.90 | 5.47 | 1.08x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 142 | 10.39 | 8.23 | 1.26x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 150 | 9.88 | 8.05 | 1.23x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 164 | 5.91 | 5.53 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 164 | 5.91 | 5.53 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 164 | 5.91 | 5.53 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 164 | 5.91 | 5.53 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 164 | 5.91 | 5.53 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 164 | 5.91 | 5.53 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 164 | 5.91 | 5.53 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 164 | 9.09 | 7.71 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 165 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 165 | 9.04 | 7.69 | 1.18x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 168 | 8.89 | 7.62 | 1.17x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 202 | 5.93 | 5.61 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 202 | 7.47 | 6.80 | 1.10x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 204 | 5.93 | 5.62 | 1.06x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 204 | 7.40 | 6.76 | 1.09x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 224 | 6.76 | 6.32 | 1.07x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 243 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 243 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 243 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 243 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 243 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 243 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 243 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 243 | 6.25 | 5.93 | 1.05x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 256 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 256 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 256 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 256 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 256 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 256 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 256 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 256 | 5.94 | 5.69 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 272 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 324 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 324 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 324 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 324 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 324 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 324 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 324 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 324 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 377 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 380 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 380 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 380 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 380 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 380 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 380 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 380 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 380 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 392 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 616 | 5.98 | 5.87 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 616 | 5.98 | 5.87 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 616 | 5.98 | 5.87 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 616 | 5.98 | 5.87 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 616 | 5.98 | 5.87 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 616 | 5.98 | 5.87 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 616 | 5.98 | 5.87 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 616 | 5.98 | 5.87 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 1007 | 5.99 | 5.93 | 1.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 1007 | 5.99 | 5.93 | 1.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 1007 | 5.99 | 5.93 | 1.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 1007 | 5.99 | 5.93 | 1.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 1007 | 5.99 | 5.93 | 1.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 1007 | 5.99 | 5.93 | 1.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 1007 | 5.99 | 5.93 | 1.01x |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 1007 | 5.99 | 5.93 | 1.01x |

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
| gpu | DeepSeek-V4.1-Flash-engram-hbm | 1 | 10.05 | 0.8% |
| rom | DeepSeek-V4.1-Flash-engram-hbm | 1 | 10.05 | 4.1% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| DeepSeek-V4.1-Flash-engram-hbm | sram | interleaved | 128 B | 1.77x |
| DeepSeek-V4.1-Flash-engram-hbm | hbm | interleaved | 32 B | 1.34x |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 166 | 0.09% | 0.63 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 259 | 0.09% | 0.97 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 259 | 0.09% | 0.97 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 5 | 0.07% | 0.90 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 5 | 0.07% | 0.90 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 5 | 0.07% | 0.90 | 4.24 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 5 | 0.07% | 0.90 | 4.24 |

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
| DeepSeek-V4.1-Flash-engram-hbm | 1 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 338.8 | 24,051.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 2 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 338.8 | 24,051.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 4 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 338.8 | 24,051.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 8 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 338.8 | 24,051.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 16 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 338.8 | 24,051.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 32 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 338.8 | 24,051.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 64 | 1.56% | 13.0 GB | 4.24% | 378.21 TB/s | 8,922.81 TB/s | 338.8 | 24,051.3 |
| DeepSeek-V4.1-Flash-engram-hbm | 256 | 5.52% | 24.5 GB | 7.95% | 709.80 TB/s | 8,922.81 TB/s | 96.4 | 24,689.9 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | link_latency | 239 |
| gpu | weight_read | 497 |
| rom | compute | 40 |
| rom | infeasible | 855 |
| rom | kv_read | 6 |
| rom | link_latency | 553 |
| rom | weight_read | 634 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 855 |

## Mechanical consistency audit

**PASS** over 61,091 checks.

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

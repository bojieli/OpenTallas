# Area-constrained roofline: n6_vs_a100-pro-200k

> CONTEXT-LADDER RUNG of n6_vs_a100: DeepSeek-V4-Pro-0813 at 200,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 481x (ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream, 795 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 96 devices. On the GPU side the correction reaches 121x (a100_sxm_80gb-x783-pipeline, 783 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 168 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Pro-0813 takes 196 x 815 mm2 (159,740 mm2, array, KV in SRAM) at 4,637 tok/s per user and 29 tok/s per 1,000 mm2, holding 1 session, against 193 copies of one unified HBM die at the same silicon: 6.8x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Pro-0813 on 322,740 mm2 of ROM silicon at 4,443 tok/s per user against 322,966 mm2 of a100_sxm_80gb-x391-tensor at 526 tok/s: **8.4x**, ROM binding on `compute` and the GPU on `link_latency`. It holds 14,417 resident sessions against the GPU cluster's 13,783. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 17.19x to it.** At 246,130 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 40.86 tok/s and the same silicon running tensor delivers 702 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4-Pro-0813, ROM binding on `link_latency`) to 2.19x (DeepSeek-V4-Pro-0813, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Pro-0813 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 156 to 33,092 tok/s, and its rate with every slot occupied from 32,996 to 33,092. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 211 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,824 us over NVLink, capping per-user decode at 548 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 316.2 us and cap it at 3,163 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 0 of 10 operating points and an array 10; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 71 of 3397 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 19.1x of aggregate throughput (DeepSeek-V4-Pro-0813). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 15.67x, on DeepSeek-V4-Pro-0813 at batch 4096, where the busiest region carries 3.12x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4-Pro-0813 at 200,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x196`** -- 196 x 815 mm2 reticle dies, 159,740 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **4,637.4 tok/s per user** (0.22 ms/token), binding on `link_latency`
- **29.0 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,637 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 9,890 W at 0.062 W/mm2, 2,132.7 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 193 copies of one unified HBM die -- `a100_sxm_80gb-x193-tensor`, 159,418 mm2, area ratio 1.0020 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 159,740 | 159,418 | 1.0020 |
| user tok/s | 4,637.4 | 682.3 | 6.80x |
| aggregate tok/s | 4,637 | 682 | 0.59x |
| resident sessions | 1 | 6,575 | -- |
| J/token | 2.1327 | 45.0692 | 21.1x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 6,575 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x298-tensor` at 246,148 mm2 and 702.2 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-array-hw-tensor-x195` | 158,925 | 4,577.6 | 28.8 | 1 | 6.71x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | 159,740 | 4,637.4 | 29.0 | 1 | 6.80x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x195` | 158,925 | 4,577.6 | 28.8 | 1 | 6.71x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | 159,740 | 4,637.4 | 29.0 | 1 | 6.80x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x196` **<-- recommended** | 159,740 | 196 | 4,637.4 | 4,637 | 29.0 | 1 | `link_latency` | 9,890 | 2,132.7 | `a100_sxm_80gb-x193-tensor` | 6.80x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 228 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | 159,740 | 4,637.4 | 29.0 | 1 |
| array | 228 | fastest | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | 159,740 | 4,637.4 | 29.0 | 1 |
| array | 228 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x195` | 158,925 | 4,577.6 | 28.8 | 1 |
| wafer | 36 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 3,484.8 | 18.8 | 1 |
| wafer | 36 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 3,734.7 | 13.5 | 1 |
| wafer | 36 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x4` | 184,900 | 3,484.8 | 18.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | 159,740 | 4,637.4 | 4,637 | 1 | 9,890 | 2,132.7 | `link_latency` | `a100_sxm_80gb-x193-tensor` | 682.3 | 6,575 | 45,069.2 | 1.002 | 6.80x | 21.1x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 3,734.7 | 3,735 | 1 | 24,841 | 6,651.4 | `link_latency` | `a100_sxm_80gb-x336-tensor` | 523.4 | 11,781 | 96,924.5 | 0.999 | 7.14x | 14.6x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-hybrid-x340` | 277,100 | 4,218.5 | 4,219 | 1 | 24,814 | 5,882.2 | `kv_read` | `a100_sxm_80gb-x335-tensor` | 523.3 | 11,745 | 96,659.1 | 1.001 | 8.06x | 16.4x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x6` | 277,350 | 3,734.7 | -- | 1 | -- | 6,651.4 | -- | -- | -- | -- | -- | 0.999 | 0.89x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 4,443.3 | 439,885 | 14,417 | 66,829 | 4,228.9 | `compute` | `a100_sxm_80gb-x391-tensor` | 466.7 | 13,783 | 63,284.3 | 0.999 | 9.52x | 15.0x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 3,483.1 | 48,764 | 4,383 | 83,468 | 11,574.6 | `link_latency` | `a100_sxm_80gb-x783-tensor` | 474.9 | 28,055 | 121,824.2 | 1.001 | 7.33x | 10.5x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 4,443.3 | 439,885 | 14,417 | 66,829 | 2,148.4 | `compute` | `a100_sxm_80gb-x391-tensor` | 381.1 | 13,783 | 39,116.0 | 0.999 | 11.66x | 18.2x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 3,483.1 | 48,764 | 4,383 | 83,468 | 5,821.2 | `link_latency` | `a100_sxm_80gb-x783-tensor` | 388.9 | 28,055 | 74,758.3 | 1.001 | 8.96x | 12.8x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 4,443.3 | 439,885 | 14,417 | 66,829 | 1,108.1 | `compute` | `a100_sxm_80gb-x391-tensor` | 279.1 | 13,783 | 26,977.1 | 0.999 | 15.92x | 24.3x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 3,483.1 | 48,764 | 4,383 | 83,468 | 2,944.5 | `link_latency` | `a100_sxm_80gb-x783-tensor` | 285.6 | 28,055 | 51,170.7 | 1.001 | 12.20x | 17.4x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 4,443.3 | 439,885 | 14,417 | 66,829 | 588.0 | `compute` | `a100_sxm_80gb-x391-hybrid` | 262.2 | 13,783 | 17,683.3 | 0.999 | 16.94x | 30.1x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 3,426.3 | 54,820 | 4,383 | 83,822 | 1,529.0 | `link_latency` | `a100_sxm_80gb-x783-hybrid` | 260.4 | 28,055 | 31,366.9 | 1.001 | 13.16x | 20.5x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 4,443.3 | 439,885 | 14,417 | 66,829 | 327.9 | `compute` | `a100_sxm_80gb-x391-hybrid` | 262.2 | 13,783 | 10,955.4 | 0.999 | 16.94x | 33.4x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 3,030.6 | 96,979 | 4,383 | 86,282 | 889.7 | `link_latency` | `a100_sxm_80gb-x783-hybrid` | 260.4 | 28,055 | 17,797.2 | 1.001 | 11.64x | 20.0x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 4,443.3 | 439,885 | 14,417 | 66,829 | 197.9 | `compute` | `a100_sxm_80gb-x391-hybrid` | 242.0 | 13,783 | 7,209.1 | 0.999 | 18.36x | 36.4x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 2,462.0 | 157,566 | 4,383 | 89,811 | 570.0 | `link_latency` | `a100_sxm_80gb-x783-hybrid` | 260.4 | 28,055 | 11,012.3 | 1.001 | 9.46x | 19.3x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | 1,849.6 | 473,493 | 14,417 | 66,672 | 140.8 | `compute` | `a100_sxm_80gb-x391-hybrid` | 123.5 | 13,783 | 3,689.8 | 0.999 | 14.98x | 18.1x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x14` | 647,150 | 1,158.1 | 296,486 | 4,383 | 97,802 | 329.9 | `kv_read` | `a100_sxm_80gb-x783-hybrid` | 181.3 | 28,055 | 4,906.5 | 1.001 | 6.39x | 12.1x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 322,740 | 484.6 | 496,214 | 14,417 | 68,097 | 137.2 | `compute` | `a100_sxm_80gb-x391-expert` | 87.3 | 13,146 | 776.8 | 0.999 | 5.55x | 5.7x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 647,150 | 406.2 | 415,997 | 4,383 | 107,612 | 258.7 | `kv_read` | `a100_sxm_80gb-x783-expert` | 111.7 | 26,753 | 1,133.5 | 1.001 | 3.64x | 4.4x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 322,740 | 122.0 | 499,766 | 14,417 | 67,000 | 134.1 | `compute` | `a100_sxm_80gb-x391-expert` | 55.6 | 13,146 | 327.7 | 0.999 | 2.19x | 2.4x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x14` | 647,150 | 102.3 | 419,200 | 4,383 | 105,744 | 252.3 | `kv_read` | `a100_sxm_80gb-x783-expert` | 81.9 | 26,753 | 416.8 | 1.001 | 1.25x | 1.7x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x196` | 159,740 | array | SRAM | 1 |
| 2 | `ROM-N6-native-HBMKV-array-hw-tensor-x227` | 185,005 | array | HBM | 8,264 |
| 4 | `ROM-N6-native-HBMKV-array-hw-tensor-x234` | 190,710 | array | HBM | 8,519 |
| 8 | `ROM-N6-native-HBMKV-array-hw-tensor-x248` | 202,120 | array | HBM | 9,029 |
| 16-64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 319,480 | array | HBM | 14,271 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x396` | 322,740 | array | HBM | 14,417 |
| 1024-4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x396` | 322,740 | array | HBM | 14,417 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Pro-0813 | HBM | rom | 211, 227, 234, 248, 297, 302, 340, 362, 363, 396 |
| DeepSeek-V4-Pro-0813 | HBM | sram | 211, 227, 234, 248, 297, 302, 340, 391, 392, 396 |
| DeepSeek-V4-Pro-0813 | SRAM | rom | 195, 196, 227, 232, 278, 326, 327, 340, 370 |
| DeepSeek-V4-Pro-0813 | SRAM | sram | 195, 196, 227, 232, 278, 326, 327, 340, 370 |

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

- **0 of 3,397 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 33%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 1,219 | 0 | 70.5% | 79.7% | 0.386 | 51% |
| rom | wafer (>=40,000 mm2) | 2,178 | 0 | 21.9% | 65.2% | 0.326 | 83% |

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
| DeepSeek-V4-Pro-0813 | 1 | 158,925 | `DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x195` | 2.149412 | 9,839.1 | link_latency | `DSV4-Pro/a100_sxm_80gb-x192-tensor` | 44.866044 | 30,605.5 | link_latency | 20.87x |
| DeepSeek-V4-Pro-0813 | 2 | 202,120 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x248` | 2.078787 | 17,965.9 | link_latency | `DSV4-Pro/a100_sxm_80gb-x245-tensor` | 32.722565 | 38,693.6 | link_latency | 15.74x |
| DeepSeek-V4-Pro-0813 | 4 | 318,665 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x391` | 2.139064 | 65,469.4 | compute | `DSV4-Pro/a100_sxm_80gb-x386-tensor` | 38.664462 | 58,903.6 | link_latency | 18.08x |
| DeepSeek-V4-Pro-0813 | 8 | 318,665 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x391` | 1.103463 | 65,469.4 | compute | `DSV4-Pro/a100_sxm_80gb-x386-tensor` | 26.671642 | 59,500.2 | link_latency | 24.17x |
| DeepSeek-V4-Pro-0813 | 16 | 318,665 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x391` | 0.585663 | 65,469.4 | compute | `DSV4-Pro/a100_sxm_80gb-x386-hybrid` | 17.648673 | 109,493.3 | weight_read | 30.13x |
| DeepSeek-V4-Pro-0813 | 32 | 318,665 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x391` | 0.326763 | 65,469.4 | compute | `DSV4-Pro/a100_sxm_80gb-x386-hybrid` | 10.938055 | 109,493.3 | weight_read | 33.47x |
| DeepSeek-V4-Pro-0813 | 64 | 318,665 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x391` | 0.197313 | 65,469.4 | compute | `DSV4-Pro/a100_sxm_80gb-x386-hybrid` | 7.200335 | 110,338.6 | weight_read | 36.49x |
| DeepSeek-V4-Pro-0813 | 256 | 318,665 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x391` | 0.141262 | 65,284.8 | compute | `DSV4-Pro/a100_sxm_80gb-x386-hybrid` | 3.687165 | 115,240.1 | weight_read | 17.98x |
| DeepSeek-V4-Pro-0813 | 1024 | 318,665 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x391` | 0.137737 | 66,638.0 | compute | `DSV4-Pro/a100_sxm_80gb-x386-expert` | 0.773257 | 68,618.5 | weight_read | 5.61x |
| DeepSeek-V4-Pro-0813 | 4096 | 318,665 | `DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x391` | 0.134604 | 65,576.6 | compute | `DSV4-Pro/a100_sxm_80gb-x386-expert` | 0.326678 | 73,766.0 | compute | 2.43x |

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
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 29,732.4 | wafer-pipeline | 3,484.8 | wafer-hybrid | 8.53x | 3,579.6 | pipeline | 690.1 | tensor | 5.19x | 8.31x | 5.05x | 0.61x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 36,297.7 | wafer-pipeline | 3,734.7 | wafer-hybrid | 9.72x | 4,111.9 | pipeline | 523.4 | tensor | 7.86x | 8.83x | 7.14x | 0.81x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 36,297.7 | wafer-pipeline | 3,664.4 | wafer-hybrid | 9.91x | 4,442.2 | pipeline | 528.0 | tensor | 8.41x | 8.17x | 6.94x | 0.85x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 36,297.7 | wafer-pipeline | 3,531.5 | wafer-hybrid | 10.28x | 4,830.2 | pipeline | 532.7 | tensor | 9.07x | 7.51x | 6.63x | 0.88x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.61x to 0.88x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x196 | 159,740 | 4,637.4 | 4,637.4 | link_latency | DSV4-Pro/a100_sxm_80gb-x193-tensor | 159,418 | 1.00x | tensor | 1,322.11 | 682.3 | 682.3 | link_latency | 6.80x | 0.59x | 113.50x | 6.80x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x195 | 158,925 | 4,577.6 | 4,577.6 | link_latency | DSV4-Pro/a100_sxm_80gb-x192-tensor | 158,592 | 1.00x | tensor | 1,321.76 | 682.2 | 682.2 | link_latency | 6.71x | 0.58x | 112.03x | 6.71x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 4,443.3 | 439,885.0 | compute | DSV4-Pro/a100_sxm_80gb-x391-tensor | 322,966 | 1.00x | tensor | 2,042.44 | 466.7 | 933.5 | link_latency | 9.52x | 27.53x | 108.75x | 9.52x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x211 | 171,965 | 3,622.6 | 7,245.3 | link_latency | DSV4-Pro/a100_sxm_80gb-x208-tensor | 171,808 | 1.00x | tensor | 1,539.54 | 584.1 | 1,168.1 | link_latency | 6.20x | 0.85x | 88.66x | 6.20x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 4,443.3 | 439,885.0 | compute | DSV4-Pro/a100_sxm_80gb-x391-tensor | 322,966 | 1.00x | tensor | 2,484.24 | 381.1 | 1,524.4 | link_latency | 11.66x | 27.53x | 108.75x | 11.66x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x211 | 171,965 | 2,905.7 | 11,622.7 | link_latency | DSV4-Pro/a100_sxm_80gb-x208-tensor | 171,808 | 1.00x | tensor | 1,973.76 | 450.2 | 1,801.0 | link_latency | 6.45x | 1.37x | 71.11x | 6.45x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 4,443.3 | 439,885.0 | compute | DSV4-Pro/a100_sxm_80gb-x391-tensor | 322,966 | 1.00x | tensor | 3,367.84 | 279.1 | 2,232.4 | link_latency | 15.92x | 27.53x | 108.75x | 15.92x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x211 | 171,965 | 2,081.7 | 16,653.4 | link_latency | DSV4-Pro/a100_sxm_80gb-x208-tensor | 171,808 | 1.00x | tensor | 2,842.20 | 309.4 | 2,475.1 | link_latency | 6.73x | 1.96x | 50.95x | 6.73x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 4,443.3 | 439,885.0 | compute | DSV4-Pro/a100_sxm_80gb-x391-hybrid | 322,966 | 1.00x | hybrid | 750.27 | 262.2 | 12,848.7 | weight_read | 16.94x | 27.53x | 108.75x | 16.94x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x211 | 171,965 | 1,328.3 | 21,252.9 | compute | DSV4-Pro/a100_sxm_80gb-x208-hybrid | 171,808 | 1.00x | hybrid | 690.39 | 267.0 | 6,940.8 | weight_read | 4.98x | 2.50x | 32.51x | 4.98x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 4,443.3 | 439,885.0 | compute | DSV4-Pro/a100_sxm_80gb-x391-hybrid | 322,966 | 1.00x | hybrid | 750.27 | 262.2 | 12,848.7 | weight_read | 16.94x | 27.53x | 108.75x | 16.94x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x211 | 171,965 | 770.6 | 24,658.1 | compute | DSV4-Pro/a100_sxm_80gb-x208-hybrid | 171,808 | 1.00x | hybrid | 697.23 | 251.1 | 8,033.7 | weight_read | 3.07x | 2.90x | 18.86x | 3.07x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 4,443.3 | 439,885.0 | compute | DSV4-Pro/a100_sxm_80gb-x391-hybrid | 322,966 | 1.00x | hybrid | 763.38 | 242.0 | 15,485.1 | weight_read | 18.36x | 27.53x | 108.75x | 18.36x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211 | 171,965 | 510.1 | 32,643.5 | compute | DSV4-Pro/a100_sxm_80gb-x208-hybrid | 171,808 | 1.00x | hybrid | 733.71 | 191.0 | 12,225.0 | weight_read | 2.67x | 2.67x | 12.48x | 2.67x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x396 | 322,740 | 1,849.6 | 473,492.8 | compute | DSV4-Pro/a100_sxm_80gb-x391-hybrid | 322,966 | 1.00x | hybrid | 931.20 | 123.5 | 31,611.8 | weight_read | 14.98x | 14.98x | 45.27x | 14.98x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x211 | 171,965 | 129.0 | 33,013.3 | compute | DSV4-Pro/a100_sxm_80gb-x208-expert | 171,808 | 1.00x | expert | 1,524.97 | 81.4 | 20,850.3 | weight_read | 1.58x | 1.58x | 3.39x | 1.58x |
| DeepSeek-V4-Pro-0813 | 1024 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 484.6 | 496,213.7 | compute | DSV4-Pro/a100_sxm_80gb-x391-expert | 322,966 | 1.00x | expert | 2,283.45 | 87.3 | 89,387.2 | weight_read | 5.55x | 5.55x | 18.07x | 5.55x |
| DeepSeek-V4-Pro-0813 | 1024 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x211 | 171,965 | 32.3 | 33,075.9 | compute | DSV4-Pro/a100_sxm_80gb-x208-expert | 171,808 | 1.00x | expert | 3,526.89 | 64.8 | 66,385.3 | weight_read | 0.50x | 0.50x | 1.78x | 0.50x |
| DeepSeek-V4-Pro-0813 | 4096 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 122.0 | 499,766.0 | compute | DSV4-Pro/a100_sxm_80gb-x391-expert | 322,966 | 1.00x | expert | 6,560.84 | 55.6 | 227,758.8 | compute | 2.19x | 2.19x | 11.61x | 2.19x |
| DeepSeek-V4-Pro-0813 | 4096 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x211 | 171,965 | 8.1 | 33,091.6 | compute | DSV4-Pro/a100_sxm_80gb-x208-expert | 171,808 | 1.00x | expert | 11,534.58 | 32.9 | 134,865.4 | compute | 0.25x | 0.25x | 1.25x | 0.25x |

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
| DeepSeek-V4-Pro-0813 | 56 | 46,256 | 40.9 | 570.7 | 270.5 | tensor | 1,300.52 | 74.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 95 | 78,470 | 40.9 | 630.3 | 267.3 | tensor | 1,313.01 | 82.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 111 | 91,686 | 40.9 | 644.3 | 267.2 | tensor | 1,315.51 | 84.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 112 | 92,512 | 40.9 | 645.1 | 269.2 | tensor | 1,315.51 | 84.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 113 | 93,338 | 40.9 | 645.5 | 256.0 | tensor | 1,316.51 | 85.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 125 | 103,250 | 40.9 | 653.8 | 263.7 | tensor | 1,317.39 | 86.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 168 | 138,768 | 40.9 | 674.4 | 267.9 | tensor | 1,320.51 | 89.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 192 | 158,592 | 40.9 | 682.2 | 267.3 | tensor | 1,321.76 | 90.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 193 | 159,418 | 40.9 | 682.3 | 259.5 | tensor | 1,322.11 | 90.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 208 | 171,808 | 40.9 | 686.4 | 267.0 | tensor | 1,322.43 | 90.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 224 | 185,024 | 40.9 | 690.1 | 266.6 | tensor | 1,323.01 | 91.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 229 | 189,154 | 40.9 | 691.1 | 263.6 | tensor | 1,323.27 | 91.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 231 | 190,806 | 40.9 | 691.5 | 265.5 | tensor | 1,323.27 | 91.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 245 | 202,370 | 40.9 | 694.2 | 263.4 | tensor | 1,323.73 | 91.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 274 | 226,324 | 40.9 | 698.9 | 260.7 | tensor | 1,324.51 | 92.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 280 | 231,280 | 40.9 | 699.8 | 265.3 | tensor | 1,324.51 | 92.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 293 | 242,018 | 40.9 | 701.6 | 262.8 | tensor | 1,324.83 | 92.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 298 | 246,148 | 40.9 | 702.2 | 260.5 | tensor | 1,324.98 | 93.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 322 | 265,972 | 40.9 | 522.5 | 260.3 | tensor | 1,820.70 | 95.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 323 | 266,798 | 40.9 | 522.6 | 261.0 | tensor | 1,820.70 | 95.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 335 | 276,710 | 40.9 | 523.3 | 263.4 | tensor | 1,820.83 | 95.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 336 | 277,536 | 40.9 | 523.4 | 264.0 | tensor | 1,820.83 | 95.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 357 | 294,882 | 40.9 | 524.4 | 261.7 | tensor | 1,821.16 | 95.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 358 | 295,708 | 40.9 | 524.5 | 262.3 | tensor | 1,821.16 | 95.5% | link_latency |
| DeepSeek-V4-Pro-0813 | 365 | 301,490 | 40.9 | 524.8 | 261.6 | tensor | 1,821.26 | 95.6% | link_latency |
| DeepSeek-V4-Pro-0813 | 386 | 318,836 | 40.9 | 525.7 | 259.5 | tensor | 1,821.54 | 95.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 387 | 319,662 | 40.9 | 525.8 | 260.1 | tensor | 1,821.54 | 95.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 391 | 322,966 | 40.9 | 526.0 | 262.2 | tensor | 1,821.54 | 95.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 448 | 370,048 | 40.9 | 528.0 | 261.5 | tensor | 1,822.07 | 96.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 672 | 555,072 | 40.9 | 532.7 | 260.6 | tensor | 1,823.32 | 97.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 783 | 646,758 | 40.9 | 534.1 | 260.4 | tensor | 1,823.68 | 97.4% | link_latency |

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
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x327 | DeepSeek-V4-Pro-0813 | 327 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x195 | DeepSeek-V4-Pro-0813 | 195 | tensor | rom_package_ucie | rom_board_serdes | 244 | 167.32 us | 597.7 tok/s | 5,976.6 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 49 on rom_board_serdes (traversals 13.2) = 163.90 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x327 | DeepSeek-V4-Pro-0813 | 327 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 9.90 us | 10,099.3 tok/s | 100,993.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.48 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x326 | DeepSeek-V4-Pro-0813 | 326 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x6 | DeepSeek-V4-Pro-0813 | 6 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x196 | DeepSeek-V4-Pro-0813 | 196 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.11 us | 75.6 tok/s | 756.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 696.80 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x4 | DeepSeek-V4-Pro-0813 | 4 | tensor | on_wafer | rom_wafer_serdes | 244 | 262.35 us | 381.2 tok/s | 3,811.8 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 27.50 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x278 | DeepSeek-V4-Pro-0813 | 278 | hybrid | nvlink3 | infiniband_hdr | 156 | 713.82 us | 140.1 tok/s | 1,400.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 88.52 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x5 | DeepSeek-V4-Pro-0813 | 5 | hybrid | on_wafer | rom_wafer_serdes | 126 | 235.26 us | 425.1 tok/s | 4,250.6 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 4 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.41 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x392 | DeepSeek-V4-Pro-0813 | 392 | pipeline | rom_package_ucie | rom_board_serdes | 60 | 2.23 us | 44,828.0 tok/s | 448,280.4 tok/s | 45 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.61 us; 15 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.62 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x234 | DeepSeek-V4-Pro-0813 | 234 | tensor | rom_package_ucie | rom_board_serdes | 244 | 194.17 us | 515.0 tok/s | 5,150.1 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 122 x all_reduce span 59 on rom_board_serdes (traversals 15.4) = 190.75 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x392 | DeepSeek-V4-Pro-0813 | 392 | hybrid | rom_package_ucie | rom_board_serdes | 182 | 9.90 us | 10,099.3 tok/s | 100,993.0 tok/s | 122 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.42 us; 60 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 6.48 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x391 | DeepSeek-V4-Pro-0813 | 391 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14 | DeepSeek-V4-Pro-0813 | 14 | pipeline | on_wafer | rom_wafer_serdes | 60 | 7.48 us | 13,373.6 tok/s | 133,736.0 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x211 | DeepSeek-V4-Pro-0813 | 211 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.73 us | 75.6 tok/s | 756.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 697.43 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x14 | DeepSeek-V4-Pro-0813 | 14 | tensor | on_wafer | rom_wafer_serdes | 244 | 316.18 us | 316.3 tok/s | 3,162.7 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 14 on rom_wafer_serdes (traversals 6.6) = 81.33 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x302 | DeepSeek-V4-Pro-0813 | 302 | hybrid | nvlink3 | infiniband_hdr | 159 | 721.63 us | 138.6 tok/s | 1,385.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 37 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.33 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14 | DeepSeek-V4-Pro-0813 | 14 | hybrid | on_wafer | rom_wafer_serdes | 135 | 236.18 us | 423.4 tok/s | 4,234.0 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 13 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 1.33 us |
| DSV4-Pro/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 140.46 us | 711.9 tok/s | 7,119.4 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.84 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink3 | infiniband_hdr | 244 | 1,300.52 us | 76.9 tok/s | 768.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 675.22 us |
| DSV4-Pro/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink3 | infiniband_hdr | 128 | 640.92 us | 156.0 tok/s | 1,560.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| DSV4-Pro/a100_sxm_80gb-x56-expert | DeepSeek-V4-Pro-0813 | 56 | expert | nvlink3 | infiniband_hdr | 244 | 867.34 us | 115.3 tok/s | 1,152.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 612.19 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 255.16 us |
| DSV4-Pro/a100_sxm_80gb-x95-pipeline | DeepSeek-V4-Pro-0813 | 95 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x95-tensor | DeepSeek-V4-Pro-0813 | 95 | tensor | nvlink3 | infiniband_hdr | 244 | 1,313.01 us | 76.2 tok/s | 761.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 687.71 us |
| DSV4-Pro/a100_sxm_80gb-x95-hybrid | DeepSeek-V4-Pro-0813 | 95 | hybrid | nvlink3 | infiniband_hdr | 133 | 653.94 us | 152.9 tok/s | 1,529.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| DSV4-Pro/a100_sxm_80gb-x95-expert | DeepSeek-V4-Pro-0813 | 95 | expert | nvlink3 | infiniband_hdr | 244 | 863.47 us | 115.8 tok/s | 1,158.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.39 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 252.08 us |
| DSV4-Pro/a100_sxm_80gb-x111-pipeline | DeepSeek-V4-Pro-0813 | 111 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x111-tensor | DeepSeek-V4-Pro-0813 | 111 | tensor | nvlink3 | infiniband_hdr | 244 | 1,315.51 us | 76.0 tok/s | 760.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 690.21 us |
| DSV4-Pro/a100_sxm_80gb-x111-hybrid | DeepSeek-V4-Pro-0813 | 111 | hybrid | nvlink3 | infiniband_hdr | 135 | 659.15 us | 151.7 tok/s | 1,517.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| DSV4-Pro/a100_sxm_80gb-x111-expert | DeepSeek-V4-Pro-0813 | 111 | expert | nvlink3 | infiniband_hdr | 244 | 862.62 us | 115.9 tok/s | 1,159.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.18 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.44 us |
| DSV4-Pro/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Pro-0813 | 112 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink3 | infiniband_hdr | 244 | 1,315.51 us | 76.0 tok/s | 760.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 690.21 us |
| DSV4-Pro/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink3 | infiniband_hdr | 135 | 659.15 us | 151.7 tok/s | 1,517.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| DSV4-Pro/a100_sxm_80gb-x112-expert | DeepSeek-V4-Pro-0813 | 112 | expert | nvlink3 | infiniband_hdr | 244 | 862.50 us | 115.9 tok/s | 1,159.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.09 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.41 us |
| DSV4-Pro/a100_sxm_80gb-x113-pipeline | DeepSeek-V4-Pro-0813 | 113 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x113-tensor | DeepSeek-V4-Pro-0813 | 113 | tensor | nvlink3 | infiniband_hdr | 244 | 1,316.51 us | 76.0 tok/s | 759.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 691.21 us |
| DSV4-Pro/a100_sxm_80gb-x113-hybrid | DeepSeek-V4-Pro-0813 | 113 | hybrid | nvlink3 | infiniband_hdr | 136 | 661.75 us | 151.1 tok/s | 1,511.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 36.45 us |
| DSV4-Pro/a100_sxm_80gb-x113-expert | DeepSeek-V4-Pro-0813 | 113 | expert | nvlink3 | infiniband_hdr | 244 | 862.47 us | 115.9 tok/s | 1,159.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.09 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.37 us |
| DSV4-Pro/a100_sxm_80gb-x125-pipeline | DeepSeek-V4-Pro-0813 | 125 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x125-tensor | DeepSeek-V4-Pro-0813 | 125 | tensor | nvlink3 | infiniband_hdr | 244 | 1,317.39 us | 75.9 tok/s | 759.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 692.08 us |
| DSV4-Pro/a100_sxm_80gb-x125-hybrid | DeepSeek-V4-Pro-0813 | 125 | hybrid | nvlink3 | infiniband_hdr | 137 | 664.36 us | 150.5 tok/s | 1,505.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 15 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 39.05 us |
| DSV4-Pro/a100_sxm_80gb-x125-expert | DeepSeek-V4-Pro-0813 | 125 | expert | nvlink3 | infiniband_hdr | 244 | 862.04 us | 116.0 tok/s | 1,160.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 611.02 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 251.02 us |
| DSV4-Pro/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Pro-0813 | 168 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Pro-0813 | 168 | tensor | nvlink3 | infiniband_hdr | 244 | 1,320.51 us | 75.7 tok/s | 757.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 695.20 us |
| DSV4-Pro/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Pro-0813 | 168 | hybrid | nvlink3 | infiniband_hdr | 142 | 677.37 us | 147.6 tok/s | 1,476.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.07 us |
| DSV4-Pro/a100_sxm_80gb-x168-expert | DeepSeek-V4-Pro-0813 | 168 | expert | nvlink3 | infiniband_hdr | 244 | 860.89 us | 116.2 tok/s | 1,161.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.73 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 250.16 us |
| DSV4-Pro/a100_sxm_80gb-x192-pipeline | DeepSeek-V4-Pro-0813 | 192 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x192-tensor | DeepSeek-V4-Pro-0813 | 192 | tensor | nvlink3 | infiniband_hdr | 244 | 1,321.76 us | 75.7 tok/s | 756.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 696.45 us |
| DSV4-Pro/a100_sxm_80gb-x192-hybrid | DeepSeek-V4-Pro-0813 | 192 | hybrid | nvlink3 | infiniband_hdr | 145 | 685.18 us | 145.9 tok/s | 1,459.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 59.88 us |
| DSV4-Pro/a100_sxm_80gb-x192-expert | DeepSeek-V4-Pro-0813 | 192 | expert | nvlink3 | infiniband_hdr | 244 | 860.48 us | 116.2 tok/s | 1,162.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.64 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.85 us |
| DSV4-Pro/a100_sxm_80gb-x193-pipeline | DeepSeek-V4-Pro-0813 | 193 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x193-tensor | DeepSeek-V4-Pro-0813 | 193 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.11 us | 75.6 tok/s | 756.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 25 on infiniband_hdr (traversals 2.0) = 696.80 us |
| DSV4-Pro/a100_sxm_80gb-x193-hybrid | DeepSeek-V4-Pro-0813 | 193 | hybrid | nvlink3 | infiniband_hdr | 146 | 687.79 us | 145.4 tok/s | 1,453.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 24 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 62.48 us |
| DSV4-Pro/a100_sxm_80gb-x193-expert | DeepSeek-V4-Pro-0813 | 193 | expert | nvlink3 | infiniband_hdr | 244 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.64 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.83 us |
| DSV4-Pro/a100_sxm_80gb-x208-pipeline | DeepSeek-V4-Pro-0813 | 208 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x208-tensor | DeepSeek-V4-Pro-0813 | 208 | tensor | nvlink3 | infiniband_hdr | 244 | 1,322.43 us | 75.6 tok/s | 756.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 697.13 us |
| DSV4-Pro/a100_sxm_80gb-x208-hybrid | DeepSeek-V4-Pro-0813 | 208 | hybrid | nvlink3 | infiniband_hdr | 147 | 690.39 us | 144.8 tok/s | 1,448.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| DSV4-Pro/a100_sxm_80gb-x208-expert | DeepSeek-V4-Pro-0813 | 208 | expert | nvlink3 | infiniband_hdr | 244 | 860.27 us | 116.2 tok/s | 1,162.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.59 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.68 us |
| DSV4-Pro/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Pro-0813 | 224 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Pro-0813 | 224 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.01 us | 75.6 tok/s | 755.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 697.70 us |
| DSV4-Pro/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Pro-0813 | 224 | hybrid | nvlink3 | infiniband_hdr | 149 | 695.60 us | 143.8 tok/s | 1,437.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| DSV4-Pro/a100_sxm_80gb-x224-expert | DeepSeek-V4-Pro-0813 | 224 | expert | nvlink3 | infiniband_hdr | 244 | 860.08 us | 116.3 tok/s | 1,162.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.55 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.53 us |
| DSV4-Pro/a100_sxm_80gb-x229-pipeline | DeepSeek-V4-Pro-0813 | 229 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x229-tensor | DeepSeek-V4-Pro-0813 | 229 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.27 us | 75.6 tok/s | 755.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 697.96 us |
| DSV4-Pro/a100_sxm_80gb-x229-hybrid | DeepSeek-V4-Pro-0813 | 229 | hybrid | nvlink3 | infiniband_hdr | 150 | 698.20 us | 143.2 tok/s | 1,432.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 72.90 us |
| DSV4-Pro/a100_sxm_80gb-x229-expert | DeepSeek-V4-Pro-0813 | 229 | expert | nvlink3 | infiniband_hdr | 244 | 860.04 us | 116.3 tok/s | 1,162.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.55 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.49 us |
| DSV4-Pro/a100_sxm_80gb-x231-pipeline | DeepSeek-V4-Pro-0813 | 231 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x231-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.27 us | 75.6 tok/s | 755.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 697.96 us |
| DSV4-Pro/a100_sxm_80gb-x231-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink3 | infiniband_hdr | 150 | 698.20 us | 143.2 tok/s | 1,432.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 72.90 us |
| DSV4-Pro/a100_sxm_80gb-x231-expert | DeepSeek-V4-Pro-0813 | 231 | expert | nvlink3 | infiniband_hdr | 244 | 860.02 us | 116.3 tok/s | 1,162.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.55 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.48 us |
| DSV4-Pro/a100_sxm_80gb-x245-pipeline | DeepSeek-V4-Pro-0813 | 245 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x245-tensor | DeepSeek-V4-Pro-0813 | 245 | tensor | nvlink3 | infiniband_hdr | 244 | 1,323.73 us | 75.5 tok/s | 755.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 698.43 us |
| DSV4-Pro/a100_sxm_80gb-x245-hybrid | DeepSeek-V4-Pro-0813 | 245 | hybrid | nvlink3 | infiniband_hdr | 152 | 703.41 us | 142.2 tok/s | 1,421.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 78.10 us |
| DSV4-Pro/a100_sxm_80gb-x245-expert | DeepSeek-V4-Pro-0813 | 245 | expert | nvlink3 | infiniband_hdr | 244 | 859.88 us | 116.3 tok/s | 1,162.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.51 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.37 us |
| DSV4-Pro/a100_sxm_80gb-x274-pipeline | DeepSeek-V4-Pro-0813 | 274 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x274-tensor | DeepSeek-V4-Pro-0813 | 274 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.51 us | 75.5 tok/s | 755.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 699.20 us |
| DSV4-Pro/a100_sxm_80gb-x274-hybrid | DeepSeek-V4-Pro-0813 | 274 | hybrid | nvlink3 | infiniband_hdr | 156 | 713.82 us | 140.1 tok/s | 1,400.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 88.52 us |
| DSV4-Pro/a100_sxm_80gb-x274-expert | DeepSeek-V4-Pro-0813 | 274 | expert | nvlink3 | infiniband_hdr | 244 | 859.64 us | 116.3 tok/s | 1,163.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.45 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.19 us |
| DSV4-Pro/a100_sxm_80gb-x280-pipeline | DeepSeek-V4-Pro-0813 | 280 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x280-tensor | DeepSeek-V4-Pro-0813 | 280 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.51 us | 75.5 tok/s | 755.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 699.20 us |
| DSV4-Pro/a100_sxm_80gb-x280-hybrid | DeepSeek-V4-Pro-0813 | 280 | hybrid | nvlink3 | infiniband_hdr | 156 | 713.82 us | 140.1 tok/s | 1,400.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 88.52 us |
| DSV4-Pro/a100_sxm_80gb-x280-expert | DeepSeek-V4-Pro-0813 | 280 | expert | nvlink3 | infiniband_hdr | 244 | 859.60 us | 116.3 tok/s | 1,163.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.44 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.16 us |
| DSV4-Pro/a100_sxm_80gb-x293-pipeline | DeepSeek-V4-Pro-0813 | 293 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x293-tensor | DeepSeek-V4-Pro-0813 | 293 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.83 us | 75.5 tok/s | 754.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 37 on infiniband_hdr (traversals 2.0) = 699.53 us |
| DSV4-Pro/a100_sxm_80gb-x293-hybrid | DeepSeek-V4-Pro-0813 | 293 | hybrid | nvlink3 | infiniband_hdr | 158 | 719.03 us | 139.1 tok/s | 1,390.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 36 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 93.72 us |
| DSV4-Pro/a100_sxm_80gb-x293-expert | DeepSeek-V4-Pro-0813 | 293 | expert | nvlink3 | infiniband_hdr | 244 | 859.52 us | 116.3 tok/s | 1,163.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.43 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.09 us |
| DSV4-Pro/a100_sxm_80gb-x298-pipeline | DeepSeek-V4-Pro-0813 | 298 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x298-tensor | DeepSeek-V4-Pro-0813 | 298 | tensor | nvlink3 | infiniband_hdr | 244 | 1,324.98 us | 75.5 tok/s | 754.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 38 on infiniband_hdr (traversals 2.0) = 699.68 us |
| DSV4-Pro/a100_sxm_80gb-x298-hybrid | DeepSeek-V4-Pro-0813 | 298 | hybrid | nvlink3 | infiniband_hdr | 159 | 721.63 us | 138.6 tok/s | 1,385.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 37 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.33 us |
| DSV4-Pro/a100_sxm_80gb-x298-expert | DeepSeek-V4-Pro-0813 | 298 | expert | nvlink3 | infiniband_hdr | 244 | 859.48 us | 116.3 tok/s | 1,163.5 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.41 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 249.07 us |
| DSV4-Pro/a100_sxm_80gb-x322-pipeline | DeepSeek-V4-Pro-0813 | 322 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x322-tensor | DeepSeek-V4-Pro-0813 | 322 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.70 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 41 on infiniband_hdr (traversals 4.0) = 1,195.40 us |
| DSV4-Pro/a100_sxm_80gb-x322-hybrid | DeepSeek-V4-Pro-0813 | 322 | hybrid | nvlink3 | infiniband_hdr | 162 | 729.44 us | 137.1 tok/s | 1,370.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 40 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 104.14 us |
| DSV4-Pro/a100_sxm_80gb-x322-expert | DeepSeek-V4-Pro-0813 | 322 | expert | nvlink3 | infiniband_hdr | 244 | 859.35 us | 116.4 tok/s | 1,163.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.38 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.96 us |
| DSV4-Pro/a100_sxm_80gb-x323-pipeline | DeepSeek-V4-Pro-0813 | 323 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x323-tensor | DeepSeek-V4-Pro-0813 | 323 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.70 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 41 on infiniband_hdr (traversals 4.0) = 1,195.40 us |
| DSV4-Pro/a100_sxm_80gb-x323-hybrid | DeepSeek-V4-Pro-0813 | 323 | hybrid | nvlink3 | infiniband_hdr | 162 | 729.44 us | 137.1 tok/s | 1,370.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 40 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 104.14 us |
| DSV4-Pro/a100_sxm_80gb-x323-expert | DeepSeek-V4-Pro-0813 | 323 | expert | nvlink3 | infiniband_hdr | 244 | 859.34 us | 116.4 tok/s | 1,163.7 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.38 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.96 us |
| DSV4-Pro/a100_sxm_80gb-x335-pipeline | DeepSeek-V4-Pro-0813 | 335 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x335-tensor | DeepSeek-V4-Pro-0813 | 335 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x335-hybrid | DeepSeek-V4-Pro-0813 | 335 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x335-expert | DeepSeek-V4-Pro-0813 | 335 | expert | nvlink3 | infiniband_hdr | 244 | 859.29 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.37 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.91 us |
| DSV4-Pro/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Pro-0813 | 336 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Pro-0813 | 336 | tensor | nvlink3 | infiniband_hdr | 244 | 1,820.83 us | 54.9 tok/s | 549.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,195.52 us |
| DSV4-Pro/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Pro-0813 | 336 | hybrid | nvlink3 | infiniband_hdr | 163 | 732.04 us | 136.6 tok/s | 1,366.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| DSV4-Pro/a100_sxm_80gb-x336-expert | DeepSeek-V4-Pro-0813 | 336 | expert | nvlink3 | infiniband_hdr | 244 | 859.27 us | 116.4 tok/s | 1,163.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.36 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.91 us |
| DSV4-Pro/a100_sxm_80gb-x357-pipeline | DeepSeek-V4-Pro-0813 | 357 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x357-tensor | DeepSeek-V4-Pro-0813 | 357 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.16 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 1,195.86 us |
| DSV4-Pro/a100_sxm_80gb-x357-hybrid | DeepSeek-V4-Pro-0813 | 357 | hybrid | nvlink3 | infiniband_hdr | 166 | 739.86 us | 135.2 tok/s | 1,351.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 44 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 114.55 us |
| DSV4-Pro/a100_sxm_80gb-x357-expert | DeepSeek-V4-Pro-0813 | 357 | expert | nvlink3 | infiniband_hdr | 244 | 859.18 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.35 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.84 us |
| DSV4-Pro/a100_sxm_80gb-x358-pipeline | DeepSeek-V4-Pro-0813 | 358 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x358-tensor | DeepSeek-V4-Pro-0813 | 358 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.16 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 1,195.86 us |
| DSV4-Pro/a100_sxm_80gb-x358-hybrid | DeepSeek-V4-Pro-0813 | 358 | hybrid | nvlink3 | infiniband_hdr | 166 | 739.86 us | 135.2 tok/s | 1,351.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 44 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 114.55 us |
| DSV4-Pro/a100_sxm_80gb-x358-expert | DeepSeek-V4-Pro-0813 | 358 | expert | nvlink3 | infiniband_hdr | 244 | 859.18 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.35 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.83 us |
| DSV4-Pro/a100_sxm_80gb-x365-pipeline | DeepSeek-V4-Pro-0813 | 365 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x365-tensor | DeepSeek-V4-Pro-0813 | 365 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.26 us | 54.9 tok/s | 549.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 46 on infiniband_hdr (traversals 4.0) = 1,195.96 us |
| DSV4-Pro/a100_sxm_80gb-x365-hybrid | DeepSeek-V4-Pro-0813 | 365 | hybrid | nvlink3 | infiniband_hdr | 167 | 742.46 us | 134.7 tok/s | 1,346.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 45 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 117.15 us |
| DSV4-Pro/a100_sxm_80gb-x365-expert | DeepSeek-V4-Pro-0813 | 365 | expert | nvlink3 | infiniband_hdr | 244 | 859.15 us | 116.4 tok/s | 1,163.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.34 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.81 us |
| DSV4-Pro/a100_sxm_80gb-x386-pipeline | DeepSeek-V4-Pro-0813 | 386 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x386-tensor | DeepSeek-V4-Pro-0813 | 386 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.54 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,196.24 us |
| DSV4-Pro/a100_sxm_80gb-x386-hybrid | DeepSeek-V4-Pro-0813 | 386 | hybrid | nvlink3 | infiniband_hdr | 170 | 750.27 us | 133.3 tok/s | 1,332.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| DSV4-Pro/a100_sxm_80gb-x386-expert | DeepSeek-V4-Pro-0813 | 386 | expert | nvlink3 | infiniband_hdr | 244 | 859.07 us | 116.4 tok/s | 1,164.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.32 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.75 us |
| DSV4-Pro/a100_sxm_80gb-x387-pipeline | DeepSeek-V4-Pro-0813 | 387 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x387-tensor | DeepSeek-V4-Pro-0813 | 387 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.54 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,196.24 us |
| DSV4-Pro/a100_sxm_80gb-x387-hybrid | DeepSeek-V4-Pro-0813 | 387 | hybrid | nvlink3 | infiniband_hdr | 170 | 750.27 us | 133.3 tok/s | 1,332.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| DSV4-Pro/a100_sxm_80gb-x387-expert | DeepSeek-V4-Pro-0813 | 387 | expert | nvlink3 | infiniband_hdr | 244 | 859.06 us | 116.4 tok/s | 1,164.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.32 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.74 us |
| DSV4-Pro/a100_sxm_80gb-x391-pipeline | DeepSeek-V4-Pro-0813 | 391 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x391-tensor | DeepSeek-V4-Pro-0813 | 391 | tensor | nvlink3 | infiniband_hdr | 244 | 1,821.54 us | 54.9 tok/s | 549.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,196.24 us |
| DSV4-Pro/a100_sxm_80gb-x391-hybrid | DeepSeek-V4-Pro-0813 | 391 | hybrid | nvlink3 | infiniband_hdr | 170 | 750.27 us | 133.3 tok/s | 1,332.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| DSV4-Pro/a100_sxm_80gb-x391-expert | DeepSeek-V4-Pro-0813 | 391 | expert | nvlink3 | infiniband_hdr | 244 | 859.05 us | 116.4 tok/s | 1,164.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.32 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.73 us |
| DSV4-Pro/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Pro-0813 | 448 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Pro-0813 | 448 | tensor | nvlink3 | infiniband_hdr | 244 | 1,822.07 us | 54.9 tok/s | 548.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,196.77 us |
| DSV4-Pro/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Pro-0813 | 448 | hybrid | nvlink3 | infiniband_hdr | 177 | 768.49 us | 130.1 tok/s | 1,301.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 143.19 us |
| DSV4-Pro/a100_sxm_80gb-x448-expert | DeepSeek-V4-Pro-0813 | 448 | expert | nvlink3 | infiniband_hdr | 244 | 858.87 us | 116.4 tok/s | 1,164.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.27 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.60 us |
| DSV4-Pro/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Pro-0813 | 672 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Pro-0813 | 672 | tensor | nvlink3 | infiniband_hdr | 244 | 1,823.32 us | 54.8 tok/s | 548.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,198.02 us |
| DSV4-Pro/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Pro-0813 | 672 | hybrid | nvlink3 | infiniband_hdr | 182 | 781.51 us | 128.0 tok/s | 1,279.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 156.21 us |
| DSV4-Pro/a100_sxm_80gb-x672-expert | DeepSeek-V4-Pro-0813 | 672 | expert | nvlink3 | infiniband_hdr | 244 | 858.47 us | 116.5 tok/s | 1,164.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.18 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.28 us |
| DSV4-Pro/a100_sxm_80gb-x783-pipeline | DeepSeek-V4-Pro-0813 | 783 | pipeline | nvlink3 | infiniband_hdr | 60 | 153.26 us | 652.5 tok/s | 6,525.0 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.22 us |
| DSV4-Pro/a100_sxm_80gb-x783-tensor | DeepSeek-V4-Pro-0813 | 783 | tensor | nvlink3 | infiniband_hdr | 244 | 1,823.68 us | 54.8 tok/s | 548.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 98 on infiniband_hdr (traversals 4.0) = 1,198.38 us |
| DSV4-Pro/a100_sxm_80gb-x783-hybrid | DeepSeek-V4-Pro-0813 | 783 | hybrid | nvlink3 | infiniband_hdr | 182 | 781.51 us | 128.0 tok/s | 1,279.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 156.21 us |
| DSV4-Pro/a100_sxm_80gb-x783-expert | DeepSeek-V4-Pro-0813 | 783 | expert | nvlink3 | infiniband_hdr | 244 | 858.35 us | 116.5 tok/s | 1,165.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 610.16 us; 122 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 248.20 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Pro-0813 | 1 | array | array | DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x195 | 158,925 | 4,577.6 | 0.029 | 4,577.6 (158,925) | 3,686.7 (231,125) | 0.81x | link_latency |
| DeepSeek-V4-Pro-0813 | 2 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x248 | 202,120 | 4,321.2 | 0.021 | 4,321.2 (202,120) | 3,483.1 (647,150) | 0.81x | link_latency |
| DeepSeek-V4-Pro-0813 | 4 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x391 | 318,665 | 4,383.5 | 0.014 | 4,383.5 (318,665) | 3,483.1 (647,150) | 0.79x | compute |
| DeepSeek-V4-Pro-0813 | 8 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x391 | 318,665 | 4,383.5 | 0.014 | 4,383.5 (318,665) | 3,483.1 (647,150) | 0.79x | compute |
| DeepSeek-V4-Pro-0813 | 16 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x391 | 318,665 | 4,383.5 | 0.014 | 4,383.5 (318,665) | 3,426.3 (647,150) | 0.78x | compute |
| DeepSeek-V4-Pro-0813 | 32 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x391 | 318,665 | 4,383.5 | 0.014 | 4,383.5 (318,665) | 3,030.6 (647,150) | 0.69x | compute |
| DeepSeek-V4-Pro-0813 | 64 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x391 | 318,665 | 4,383.5 | 0.014 | 4,383.5 (318,665) | 2,462.0 (647,150) | 0.56x | compute |
| DeepSeek-V4-Pro-0813 | 256 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x391 | 318,665 | 1,805.3 | 0.006 | 1,805.3 (318,665) | 1,158.1 (647,150) | 0.64x | compute |
| DeepSeek-V4-Pro-0813 | 1024 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x391 | 318,665 | 472.5 | 0.001 | 472.5 (318,665) | 406.2 (647,150) | 0.86x | compute |
| DeepSeek-V4-Pro-0813 | 4096 | array | array | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x391 | 318,665 | 118.9 | 0.000 | 118.9 (318,665) | 102.3 (647,150) | 0.86x | compute |

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
| DeepSeek-V4-Pro-0813 | 384 | 2,140.8 MB | 469.5 mm2 | 84.51 mm2 (18.0%) | 180,295 mm2 | 32,453 mm2 | 195,796 mm2 = 240.2 reticles |

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
| DeepSeek-V4-Pro-0813 | 1 | sram | 488,866.3 | 26,091.7 | 26,091.7 | 18.74x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 488,866.3 | 26,091.7 | 26,091.7 | 18.74x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 488,866.3 | 26,091.7 | 26,091.7 | 18.74x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 488,866.3 | 26,091.7 | 30,662.5 | 18.74x | 1.18x | compute | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 16 | sram | 488,866.3 | 26,091.7 | 51,219.6 | 18.74x | 1.96x | compute | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | sram | 488,866.3 | 26,091.7 | 78,168.3 | 18.74x | 3.00x | compute | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | sram | 488,866.3 | 26,091.7 | 111,606.6 | 18.74x | 4.28x | compute | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 256 | sram | 488,866.3 | 26,091.7 | 222,603.8 | 18.74x | 8.53x | compute | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | sram | 496,213.7 | 26,098.4 | 331,426.0 | 19.01x | 12.70x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4096 | sram | 499,766.0 | 26,109.0 | 409,240.1 | 19.14x | 15.67x | compute | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 453,670.6 | 216,256.2 | 216,256.2 | 2.10x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 453,670.6 | 216,256.2 | 216,256.2 | 2.10x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 453,670.6 | 216,256.2 | 216,256.2 | 2.10x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 453,670.6 | 216,256.2 | 216,256.2 | 2.10x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 453,670.6 | 216,256.2 | 216,256.2 | 2.10x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 453,670.6 | 216,256.2 | 216,256.2 | 2.10x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 453,670.6 | 216,256.2 | 216,256.2 | 2.10x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 453,670.6 | 216,256.2 | 296,486.0 | 2.10x | 1.37x | compute | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 1024 | rom | 459,991.3 | 216,586.7 | 380,313.3 | 2.12x | 1.76x | compute | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 4096 | rom | 463,042.3 | 217,451.9 | 434,815.3 | 2.13x | 2.00x | compute | weight_read | kv_read |

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
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 1.00 | 1.00 | 488,866.3 | 1.515 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396-romfill | 322,740 | 1.07 | 1.00 | 453,670.6 | 1.406 | compute | 0.93x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,091.7 | 0.040 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion | 647,150 | 1.00 | 1.00 | 26,091.7 | 0.040 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 1.00 | 1.00 | 488,866.3 | 1.515 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396-romfill | 322,740 | 1.07 | 1.00 | 453,670.6 | 1.406 | compute | 0.93x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,091.7 | 0.040 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion | 647,150 | 1.00 | 1.00 | 26,091.7 | 0.040 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 1.00 | 1.00 | 488,866.3 | 1.515 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396-romfill | 322,740 | 1.07 | 1.00 | 453,670.6 | 1.406 | compute | 0.93x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,091.7 | 0.040 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion | 647,150 | 1.00 | 1.00 | 26,091.7 | 0.040 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 1.00 | 1.00 | 488,866.3 | 1.515 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396-romfill | 322,740 | 1.07 | 1.00 | 453,670.6 | 1.406 | compute | 0.93x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,091.7 | 0.040 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x113-perregion | 92,095 | 1.00 | 1.99 | 30,662.5 | 0.333 | link_latency | 0.06x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 1.00 | 1.00 | 488,866.3 | 1.515 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396-romfill | 322,740 | 1.07 | 1.00 | 453,670.6 | 1.406 | compute | 0.93x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,091.7 | 0.040 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x113-perregion | 92,095 | 1.00 | 2.54 | 51,219.6 | 0.556 | link_latency | 0.10x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 1.00 | 1.00 | 488,866.3 | 1.515 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396-romfill | 322,740 | 1.07 | 1.00 | 453,670.6 | 1.406 | compute | 0.93x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,091.7 | 0.040 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x113-perregion | 92,095 | 1.00 | 3.49 | 78,168.3 | 0.849 | link_latency | 0.16x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 1.00 | 1.00 | 488,866.3 | 1.515 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396-romfill | 322,740 | 1.07 | 1.00 | 453,670.6 | 1.406 | compute | 0.93x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,091.7 | 0.040 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x14-perregion | 647,150 | 1.00 | 4.92 | 111,606.6 | 0.172 | link_latency | 0.23x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perregion-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 1.00 | 1.00 | 488,866.3 | 1.515 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396-romfill | 322,740 | 1.07 | 1.00 | 453,670.6 | 1.406 | compute | 0.93x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 1.00 | 26,091.7 | 0.040 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.00 | 216,256.2 | 0.334 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x14-perregion | 647,150 | 1.00 | 10.96 | 222,603.8 | 0.344 | kv_read | 0.46x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perregion-romfill | 647,150 | 8.34 | 2.71 | 296,486.0 | 0.458 | kv_read | 0.61x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 1.00 | 1.00 | 496,213.7 | 1.538 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 1024 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396-romfill | 322,740 | 1.07 | 1.00 | 459,991.3 | 1.425 | compute | 0.93x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x113-perstream | 92,095 | 1.00 | 9.06 | 26,098.4 | 0.283 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 1024 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 1.29 | 216,586.7 | 0.335 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perregion | 647,150 | 1.00 | 5.29 | 331,426.0 | 0.512 | weight_read | 0.67x |
| DeepSeek-V4-Pro-0813 | 1024 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perregion-romfill | 647,150 | 8.34 | 5.29 | 380,313.3 | 0.588 | kv_read | 0.77x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396 | 322,740 | 1.00 | 1.00 | 499,766.0 | 1.549 | compute | 1.00x |
| DeepSeek-V4-Pro-0813 | 4096 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x396-romfill | 322,740 | 1.07 | 1.00 | 463,042.3 | 1.435 | compute | 0.93x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream | 647,150 | 1.00 | 5.15 | 26,109.0 | 0.040 | weight_read | 0.05x |
| DeepSeek-V4-Pro-0813 | 4096 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x14-perstream-romfill | 647,150 | 8.34 | 5.15 | 217,451.9 | 0.336 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x14-perregion | 647,150 | 1.00 | 11.95 | 409,240.1 | 0.632 | kv_read | 0.82x |
| DeepSeek-V4-Pro-0813 | 4096 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x127-perregion-romfill | 103,505 | 1.22 | 7.20 | 434,815.3 | 4.201 | kv_read | 0.87x |

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
| DeepSeek-V4-Pro-0813 | 1 | 96 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 113 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 113 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 113 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 113 | 2.27 | 1.010 | 1.131 | 1.12x |
| DeepSeek-V4-Pro-0813 | 1024 | 113 | 9.06 | 1.065 | 2.072 | 1.95x |
| DeepSeek-V4-Pro-0813 | 4096 | 113 | 36.25 | 1.302 | 3.701 | 2.84x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Pro-0813 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 56 | 10.81 | 6.97 | 1.55x |
| DeepSeek-V4-Pro-0813 | 4 | 56 | 19.29 | 9.82 | 1.97x |
| DeepSeek-V4-Pro-0813 | 8 | 56 | 31.31 | 13.36 | 2.34x |
| DeepSeek-V4-Pro-0813 | 16 | 56 | 44.01 | 17.42 | 2.53x |
| DeepSeek-V4-Pro-0813 | 32 | 56 | 52.38 | 21.53 | 2.43x |
| DeepSeek-V4-Pro-0813 | 64 | 56 | 55.31 | 25.09 | 2.20x |
| DeepSeek-V4-Pro-0813 | 256 | 56 | 55.94 | 28.42 | 1.97x |
| DeepSeek-V4-Pro-0813 | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| DeepSeek-V4-Pro-0813 | 1 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 95 | 11.25 | 7.96 | 1.41x |
| DeepSeek-V4-Pro-0813 | 4 | 95 | 20.87 | 11.25 | 1.85x |
| DeepSeek-V4-Pro-0813 | 8 | 95 | 36.28 | 16.11 | 2.25x |
| DeepSeek-V4-Pro-0813 | 16 | 95 | 56.57 | 21.79 | 2.60x |
| DeepSeek-V4-Pro-0813 | 32 | 95 | 75.98 | 27.91 | 2.72x |
| DeepSeek-V4-Pro-0813 | 64 | 95 | 87.80 | 33.52 | 2.62x |
| DeepSeek-V4-Pro-0813 | 256 | 95 | 93.25 | 39.02 | 2.39x |
| DeepSeek-V4-Pro-0813 | 1024 | 95 | 93.37 | 39.25 | 2.38x |
| DeepSeek-V4-Pro-0813 | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 111 | 11.34 | 8.26 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 111 | 21.22 | 11.67 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 111 | 37.44 | 16.97 | 2.21x |
| DeepSeek-V4-Pro-0813 | 16 | 111 | 59.81 | 23.14 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 111 | 82.95 | 29.94 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 111 | 98.78 | 36.26 | 2.72x |
| DeepSeek-V4-Pro-0813 | 256 | 111 | 107.35 | 42.56 | 2.52x |
| DeepSeek-V4-Pro-0813 | 1024 | 111 | 107.56 | 42.82 | 2.51x |
| DeepSeek-V4-Pro-0813 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 112 | 11.34 | 8.28 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 112 | 21.24 | 11.69 | 1.82x |
| DeepSeek-V4-Pro-0813 | 8 | 112 | 37.50 | 17.02 | 2.20x |
| DeepSeek-V4-Pro-0813 | 16 | 112 | 59.99 | 23.22 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 112 | 83.35 | 30.06 | 2.77x |
| DeepSeek-V4-Pro-0813 | 64 | 112 | 99.43 | 36.43 | 2.73x |
| DeepSeek-V4-Pro-0813 | 256 | 112 | 108.20 | 42.76 | 2.53x |
| DeepSeek-V4-Pro-0813 | 1024 | 112 | 108.42 | 43.03 | 2.52x |
| DeepSeek-V4-Pro-0813 | 1 | 113 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 113 | 11.35 | 8.30 | 1.37x |
| DeepSeek-V4-Pro-0813 | 4 | 113 | 21.26 | 11.72 | 1.81x |
| DeepSeek-V4-Pro-0813 | 8 | 113 | 37.56 | 17.07 | 2.20x |
| DeepSeek-V4-Pro-0813 | 16 | 113 | 60.17 | 23.29 | 2.58x |
| DeepSeek-V4-Pro-0813 | 32 | 113 | 83.74 | 30.18 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 113 | 100.07 | 36.59 | 2.74x |
| DeepSeek-V4-Pro-0813 | 256 | 113 | 109.05 | 42.97 | 2.54x |
| DeepSeek-V4-Pro-0813 | 1024 | 113 | 109.28 | 43.24 | 2.53x |
| DeepSeek-V4-Pro-0813 | 1 | 125 | 5.88 | 5.41 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 125 | 11.40 | 8.49 | 1.34x |
| DeepSeek-V4-Pro-0813 | 4 | 125 | 21.45 | 11.99 | 1.79x |
| DeepSeek-V4-Pro-0813 | 8 | 125 | 38.23 | 17.62 | 2.17x |
| DeepSeek-V4-Pro-0813 | 16 | 125 | 62.11 | 24.16 | 2.57x |
| DeepSeek-V4-Pro-0813 | 32 | 125 | 88.13 | 31.52 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 125 | 107.37 | 38.43 | 2.79x |
| DeepSeek-V4-Pro-0813 | 256 | 125 | 118.96 | 45.37 | 2.62x |
| DeepSeek-V4-Pro-0813 | 1024 | 125 | 119.28 | 45.67 | 2.61x |
| DeepSeek-V4-Pro-0813 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 168 | 11.53 | 9.03 | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 168 | 21.94 | 12.85 | 1.71x |
| DeepSeek-V4-Pro-0813 | 8 | 168 | 39.93 | 19.17 | 2.08x |
| DeepSeek-V4-Pro-0813 | 16 | 168 | 67.18 | 26.68 | 2.52x |
| DeepSeek-V4-Pro-0813 | 32 | 168 | 100.21 | 35.54 | 2.82x |
| DeepSeek-V4-Pro-0813 | 64 | 168 | 128.82 | 44.06 | 2.92x |
| DeepSeek-V4-Pro-0813 | 256 | 168 | 150.33 | 52.81 | 2.85x |
| DeepSeek-V4-Pro-0813 | 1024 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4-Pro-0813 | 4096 | 168 | 151.03 | 53.19 | 2.84x |
| DeepSeek-V4-Pro-0813 | 1 | 192 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 192 | 11.57 | 9.27 | 1.25x |
| DeepSeek-V4-Pro-0813 | 4 | 192 | 22.12 | 13.26 | 1.67x |
| DeepSeek-V4-Pro-0813 | 8 | 192 | 40.57 | 19.81 | 2.05x |
| DeepSeek-V4-Pro-0813 | 16 | 192 | 69.16 | 27.85 | 2.48x |
| DeepSeek-V4-Pro-0813 | 32 | 192 | 105.19 | 37.43 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 192 | 138.26 | 46.71 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 192 | 165.21 | 56.35 | 2.93x |
| DeepSeek-V4-Pro-0813 | 1024 | 192 | 166.15 | 56.77 | 2.93x |
| DeepSeek-V4-Pro-0813 | 4096 | 192 | 166.15 | 56.77 | 2.93x |
| DeepSeek-V4-Pro-0813 | 1 | 193 | 5.92 | 5.60 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 193 | 11.58 | 9.28 | 1.25x |
| DeepSeek-V4-Pro-0813 | 4 | 193 | 22.13 | 13.28 | 1.67x |
| DeepSeek-V4-Pro-0813 | 8 | 193 | 40.59 | 19.83 | 2.05x |
| DeepSeek-V4-Pro-0813 | 16 | 193 | 69.24 | 27.89 | 2.48x |
| DeepSeek-V4-Pro-0813 | 32 | 193 | 105.38 | 37.51 | 2.81x |
| DeepSeek-V4-Pro-0813 | 64 | 193 | 138.62 | 46.82 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 193 | 165.80 | 56.49 | 2.93x |
| DeepSeek-V4-Pro-0813 | 1024 | 193 | 166.74 | 56.91 | 2.93x |
| DeepSeek-V4-Pro-0813 | 4096 | 193 | 166.74 | 56.91 | 2.93x |
| DeepSeek-V4-Pro-0813 | 1 | 208 | 5.93 | 5.62 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 208 | 11.60 | 9.40 | 1.23x |
| DeepSeek-V4-Pro-0813 | 4 | 208 | 22.22 | 13.52 | 1.64x |
| DeepSeek-V4-Pro-0813 | 8 | 208 | 40.92 | 20.17 | 2.03x |
| DeepSeek-V4-Pro-0813 | 16 | 208 | 70.26 | 28.57 | 2.46x |
| DeepSeek-V4-Pro-0813 | 32 | 208 | 108.02 | 38.60 | 2.80x |
| DeepSeek-V4-Pro-0813 | 64 | 208 | 143.78 | 48.34 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 208 | 174.22 | 58.53 | 2.98x |
| DeepSeek-V4-Pro-0813 | 1024 | 208 | 175.31 | 58.97 | 2.97x |
| DeepSeek-V4-Pro-0813 | 4096 | 208 | 175.31 | 58.97 | 2.97x |
| DeepSeek-V4-Pro-0813 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 224 | 11.62 | 9.53 | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | 224 | 22.31 | 13.76 | 1.62x |
| DeepSeek-V4-Pro-0813 | 8 | 224 | 41.22 | 20.50 | 2.01x |
| DeepSeek-V4-Pro-0813 | 16 | 224 | 71.23 | 29.26 | 2.43x |
| DeepSeek-V4-Pro-0813 | 32 | 224 | 110.53 | 39.70 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 224 | 148.77 | 49.88 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 224 | 182.57 | 60.59 | 3.01x |
| DeepSeek-V4-Pro-0813 | 1024 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4-Pro-0813 | 4096 | 224 | 183.81 | 61.05 | 3.01x |
| DeepSeek-V4-Pro-0813 | 1 | 229 | 5.93 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 229 | 11.63 | 9.56 | 1.22x |
| DeepSeek-V4-Pro-0813 | 4 | 229 | 22.33 | 13.83 | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | 229 | 41.31 | 20.59 | 2.01x |
| DeepSeek-V4-Pro-0813 | 16 | 229 | 71.50 | 29.47 | 2.43x |
| DeepSeek-V4-Pro-0813 | 32 | 229 | 111.26 | 40.03 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 229 | 150.23 | 50.33 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 229 | 185.05 | 61.21 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1024 | 229 | 186.34 | 61.68 | 3.02x |
| DeepSeek-V4-Pro-0813 | 4096 | 229 | 186.34 | 61.68 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 231 | 11.63 | 9.58 | 1.21x |
| DeepSeek-V4-Pro-0813 | 4 | 231 | 22.34 | 13.86 | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | 231 | 41.34 | 20.63 | 2.00x |
| DeepSeek-V4-Pro-0813 | 16 | 231 | 71.61 | 29.55 | 2.42x |
| DeepSeek-V4-Pro-0813 | 32 | 231 | 111.55 | 40.16 | 2.78x |
| DeepSeek-V4-Pro-0813 | 64 | 231 | 150.80 | 50.51 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 231 | 186.03 | 61.46 | 3.03x |
| DeepSeek-V4-Pro-0813 | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4-Pro-0813 | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1 | 245 | 5.94 | 5.68 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 245 | 11.64 | 9.67 | 1.20x |
| DeepSeek-V4-Pro-0813 | 4 | 245 | 22.40 | 14.06 | 1.59x |
| DeepSeek-V4-Pro-0813 | 8 | 245 | 41.57 | 20.88 | 1.99x |
| DeepSeek-V4-Pro-0813 | 16 | 245 | 72.32 | 30.12 | 2.40x |
| DeepSeek-V4-Pro-0813 | 32 | 245 | 113.43 | 41.03 | 2.76x |
| DeepSeek-V4-Pro-0813 | 64 | 245 | 154.63 | 51.73 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 245 | 192.62 | 63.12 | 3.05x |
| DeepSeek-V4-Pro-0813 | 1024 | 245 | 194.06 | 63.62 | 3.05x |
| DeepSeek-V4-Pro-0813 | 4096 | 245 | 194.06 | 63.62 | 3.05x |
| DeepSeek-V4-Pro-0813 | 1 | 274 | 5.95 | 5.71 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 274 | 11.67 | 9.84 | 1.19x |
| DeepSeek-V4-Pro-0813 | 4 | 274 | 22.51 | 14.45 | 1.56x |
| DeepSeek-V4-Pro-0813 | 8 | 274 | 41.96 | 21.33 | 1.97x |
| DeepSeek-V4-Pro-0813 | 16 | 274 | 73.58 | 31.22 | 2.36x |
| DeepSeek-V4-Pro-0813 | 32 | 274 | 116.83 | 42.67 | 2.74x |
| DeepSeek-V4-Pro-0813 | 64 | 274 | 161.66 | 54.04 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 274 | 205.01 | 66.32 | 3.09x |
| DeepSeek-V4-Pro-0813 | 1024 | 274 | 206.70 | 66.86 | 3.09x |
| DeepSeek-V4-Pro-0813 | 4096 | 274 | 206.70 | 66.86 | 3.09x |
| DeepSeek-V4-Pro-0813 | 1 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 280 | 11.68 | 9.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 280 | 22.53 | 14.53 | 1.55x |
| DeepSeek-V4-Pro-0813 | 8 | 280 | 42.03 | 21.42 | 1.96x |
| DeepSeek-V4-Pro-0813 | 16 | 280 | 73.81 | 31.44 | 2.35x |
| DeepSeek-V4-Pro-0813 | 32 | 280 | 117.46 | 42.98 | 2.73x |
| DeepSeek-V4-Pro-0813 | 64 | 280 | 162.98 | 54.48 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 280 | 207.38 | 66.94 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1024 | 280 | 209.13 | 67.50 | 3.10x |
| DeepSeek-V4-Pro-0813 | 4096 | 280 | 209.13 | 67.50 | 3.10x |
| DeepSeek-V4-Pro-0813 | 1 | 293 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 293 | 11.69 | 9.94 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 293 | 22.57 | 14.69 | 1.54x |
| DeepSeek-V4-Pro-0813 | 8 | 293 | 42.17 | 21.60 | 1.95x |
| DeepSeek-V4-Pro-0813 | 16 | 293 | 74.29 | 31.89 | 2.33x |
| DeepSeek-V4-Pro-0813 | 32 | 293 | 118.75 | 43.62 | 2.72x |
| DeepSeek-V4-Pro-0813 | 64 | 293 | 165.70 | 55.42 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 293 | 212.31 | 68.26 | 3.11x |
| DeepSeek-V4-Pro-0813 | 1024 | 293 | 214.17 | 68.82 | 3.11x |
| DeepSeek-V4-Pro-0813 | 4096 | 293 | 214.17 | 68.82 | 3.11x |
| DeepSeek-V4-Pro-0813 | 1 | 298 | 5.95 | 5.73 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 298 | 11.69 | 9.97 | 1.17x |
| DeepSeek-V4-Pro-0813 | 4 | 298 | 22.58 | 14.75 | 1.53x |
| DeepSeek-V4-Pro-0813 | 8 | 298 | 42.22 | 21.67 | 1.95x |
| DeepSeek-V4-Pro-0813 | 16 | 298 | 74.46 | 32.06 | 2.32x |
| DeepSeek-V4-Pro-0813 | 32 | 298 | 119.22 | 43.86 | 2.72x |
| DeepSeek-V4-Pro-0813 | 64 | 298 | 166.71 | 55.77 | 2.99x |
| DeepSeek-V4-Pro-0813 | 256 | 298 | 214.13 | 68.75 | 3.11x |
| DeepSeek-V4-Pro-0813 | 1024 | 298 | 216.03 | 69.32 | 3.12x |
| DeepSeek-V4-Pro-0813 | 4096 | 298 | 216.03 | 69.32 | 3.12x |
| DeepSeek-V4-Pro-0813 | 1 | 322 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 322 | 11.71 | 10.08 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 322 | 22.64 | 15.03 | 1.51x |
| DeepSeek-V4-Pro-0813 | 8 | 322 | 42.45 | 21.98 | 1.93x |
| DeepSeek-V4-Pro-0813 | 16 | 322 | 75.22 | 32.84 | 2.29x |
| DeepSeek-V4-Pro-0813 | 32 | 322 | 121.31 | 44.94 | 2.70x |
| DeepSeek-V4-Pro-0813 | 64 | 322 | 171.18 | 57.39 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 322 | 222.38 | 71.03 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1024 | 322 | 224.47 | 71.63 | 3.13x |
| DeepSeek-V4-Pro-0813 | 4096 | 322 | 224.47 | 71.63 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1 | 323 | 5.95 | 5.75 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 323 | 11.71 | 10.08 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 323 | 22.65 | 15.04 | 1.51x |
| DeepSeek-V4-Pro-0813 | 8 | 323 | 42.46 | 21.99 | 1.93x |
| DeepSeek-V4-Pro-0813 | 16 | 323 | 75.24 | 32.88 | 2.29x |
| DeepSeek-V4-Pro-0813 | 32 | 323 | 121.40 | 44.98 | 2.70x |
| DeepSeek-V4-Pro-0813 | 64 | 323 | 171.35 | 57.46 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 323 | 222.71 | 71.12 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1024 | 323 | 224.81 | 71.72 | 3.13x |
| DeepSeek-V4-Pro-0813 | 4096 | 323 | 224.81 | 71.72 | 3.13x |
| DeepSeek-V4-Pro-0813 | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 335 | 11.71 | 10.13 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 335 | 22.67 | 15.17 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 335 | 42.57 | 22.14 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 335 | 75.58 | 33.24 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 335 | 122.34 | 45.48 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 335 | 173.40 | 58.23 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 335 | 226.52 | 72.22 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4-Pro-0813 | 4096 | 335 | 228.71 | 72.82 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 336 | 11.71 | 10.14 | 1.16x |
| DeepSeek-V4-Pro-0813 | 4 | 336 | 22.68 | 15.18 | 1.49x |
| DeepSeek-V4-Pro-0813 | 8 | 336 | 42.57 | 22.15 | 1.92x |
| DeepSeek-V4-Pro-0813 | 16 | 336 | 75.61 | 33.27 | 2.27x |
| DeepSeek-V4-Pro-0813 | 32 | 336 | 122.42 | 45.52 | 2.69x |
| DeepSeek-V4-Pro-0813 | 64 | 336 | 173.56 | 58.30 | 2.98x |
| DeepSeek-V4-Pro-0813 | 256 | 336 | 226.83 | 72.31 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4-Pro-0813 | 4096 | 336 | 229.03 | 72.91 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1 | 357 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 357 | 11.73 | 10.22 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 357 | 22.72 | 15.40 | 1.48x |
| DeepSeek-V4-Pro-0813 | 8 | 357 | 42.74 | 22.39 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 357 | 76.15 | 33.88 | 2.25x |
| DeepSeek-V4-Pro-0813 | 32 | 357 | 123.93 | 46.35 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 357 | 176.86 | 59.62 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 357 | 233.07 | 74.16 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 357 | 235.42 | 74.78 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 357 | 235.42 | 74.78 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 358 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 358 | 11.73 | 10.22 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 358 | 22.72 | 15.41 | 1.47x |
| DeepSeek-V4-Pro-0813 | 8 | 358 | 42.74 | 22.40 | 1.91x |
| DeepSeek-V4-Pro-0813 | 16 | 358 | 76.17 | 33.90 | 2.25x |
| DeepSeek-V4-Pro-0813 | 32 | 358 | 124.00 | 46.38 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 358 | 177.01 | 59.68 | 2.97x |
| DeepSeek-V4-Pro-0813 | 256 | 358 | 233.36 | 74.24 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 358 | 235.71 | 74.87 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 358 | 235.71 | 74.87 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 365 | 5.96 | 5.78 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 365 | 11.73 | 10.25 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 365 | 22.74 | 15.49 | 1.47x |
| DeepSeek-V4-Pro-0813 | 8 | 365 | 42.79 | 22.48 | 1.90x |
| DeepSeek-V4-Pro-0813 | 16 | 365 | 76.34 | 34.09 | 2.24x |
| DeepSeek-V4-Pro-0813 | 32 | 365 | 124.47 | 46.65 | 2.67x |
| DeepSeek-V4-Pro-0813 | 64 | 365 | 178.04 | 60.11 | 2.96x |
| DeepSeek-V4-Pro-0813 | 256 | 365 | 235.32 | 74.84 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 365 | 237.72 | 75.47 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 365 | 237.72 | 75.47 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 386 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 386 | 11.74 | 10.32 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 386 | 22.77 | 15.69 | 1.45x |
| DeepSeek-V4-Pro-0813 | 8 | 386 | 42.93 | 22.71 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 386 | 76.81 | 34.64 | 2.22x |
| DeepSeek-V4-Pro-0813 | 32 | 386 | 125.78 | 47.40 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 386 | 180.94 | 61.36 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 386 | 240.90 | 76.58 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 386 | 243.44 | 77.23 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 386 | 243.45 | 77.23 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 387 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 387 | 11.74 | 10.32 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 387 | 22.78 | 15.70 | 1.45x |
| DeepSeek-V4-Pro-0813 | 8 | 387 | 42.94 | 22.72 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 387 | 76.83 | 34.66 | 2.22x |
| DeepSeek-V4-Pro-0813 | 32 | 387 | 125.84 | 47.44 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 387 | 181.07 | 61.42 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 387 | 241.16 | 76.66 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 387 | 243.71 | 77.31 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 387 | 243.71 | 77.31 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 391 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 391 | 11.74 | 10.33 | 1.14x |
| DeepSeek-V4-Pro-0813 | 4 | 391 | 22.78 | 15.74 | 1.45x |
| DeepSeek-V4-Pro-0813 | 8 | 391 | 42.96 | 22.76 | 1.89x |
| DeepSeek-V4-Pro-0813 | 16 | 391 | 76.91 | 34.76 | 2.21x |
| DeepSeek-V4-Pro-0813 | 32 | 391 | 126.08 | 47.58 | 2.65x |
| DeepSeek-V4-Pro-0813 | 64 | 391 | 181.60 | 61.65 | 2.95x |
| DeepSeek-V4-Pro-0813 | 256 | 391 | 242.17 | 76.98 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1024 | 391 | 244.74 | 77.64 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 391 | 244.74 | 77.64 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 448 | 11.76 | 10.50 | 1.12x |
| DeepSeek-V4-Pro-0813 | 4 | 448 | 22.87 | 16.25 | 1.41x |
| DeepSeek-V4-Pro-0813 | 8 | 448 | 43.27 | 23.34 | 1.85x |
| DeepSeek-V4-Pro-0813 | 16 | 448 | 77.94 | 36.03 | 2.16x |
| DeepSeek-V4-Pro-0813 | 32 | 448 | 129.03 | 49.47 | 2.61x |
| DeepSeek-V4-Pro-0813 | 64 | 448 | 188.21 | 64.80 | 2.90x |
| DeepSeek-V4-Pro-0813 | 256 | 448 | 255.15 | 81.21 | 3.14x |
| DeepSeek-V4-Pro-0813 | 1024 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4-Pro-0813 | 4096 | 448 | 258.06 | 81.95 | 3.15x |
| DeepSeek-V4-Pro-0813 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 672 | 11.81 | 10.91 | 1.08x |
| DeepSeek-V4-Pro-0813 | 4 | 672 | 23.06 | 17.73 | 1.30x |
| DeepSeek-V4-Pro-0813 | 8 | 672 | 43.98 | 25.33 | 1.74x |
| DeepSeek-V4-Pro-0813 | 16 | 672 | 80.37 | 39.17 | 2.05x |
| DeepSeek-V4-Pro-0813 | 32 | 672 | 136.13 | 55.89 | 2.44x |
| DeepSeek-V4-Pro-0813 | 64 | 672 | 204.63 | 73.69 | 2.78x |
| DeepSeek-V4-Pro-0813 | 256 | 672 | 288.80 | 93.78 | 3.08x |
| DeepSeek-V4-Pro-0813 | 1024 | 672 | 292.67 | 94.67 | 3.09x |
| DeepSeek-V4-Pro-0813 | 4096 | 672 | 292.67 | 94.67 | 3.09x |
| DeepSeek-V4-Pro-0813 | 1 | 783 | 5.98 | 5.90 | 1.01x |
| DeepSeek-V4-Pro-0813 | 2 | 783 | 11.82 | 11.03 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 783 | 23.11 | 18.26 | 1.27x |
| DeepSeek-V4-Pro-0813 | 8 | 783 | 44.19 | 26.20 | 1.69x |
| DeepSeek-V4-Pro-0813 | 16 | 783 | 81.07 | 40.13 | 2.02x |
| DeepSeek-V4-Pro-0813 | 32 | 783 | 138.24 | 58.57 | 2.36x |
| DeepSeek-V4-Pro-0813 | 64 | 783 | 209.64 | 76.70 | 2.73x |
| DeepSeek-V4-Pro-0813 | 256 | 783 | 299.47 | 99.03 | 3.02x |
| DeepSeek-V4-Pro-0813 | 1024 | 783 | 303.67 | 99.95 | 3.04x |
| DeepSeek-V4-Pro-0813 | 4096 | 783 | 303.67 | 99.95 | 3.04x |

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
| gpu | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 1.2% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 17.61 | 10.4% |

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
| DeepSeek-V4-Pro-0813 | 1 | 96 | 58.43% | 124.46 | 2.22 |
| DeepSeek-V4-Pro-0813 | 2 | 2 | 6.43% | 16.27 | 2.22 |
| DeepSeek-V4-Pro-0813 | 4 | 2 | 6.43% | 16.27 | 2.22 |
| DeepSeek-V4-Pro-0813 | 8 | 2 | 6.43% | 16.27 | 2.22 |

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
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 156.4 | 32,995.6 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 156.4 | 32,995.6 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 156.4 | 32,995.6 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 156.4 | 32,995.6 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 156.4 | 32,995.6 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 156.4 | 32,995.6 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 156.4 | 32,995.6 |
| DeepSeek-V4-Pro-0813 | 256 | 1.89% | 42.4 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 129.0 | 33,013.3 |
| DeepSeek-V4-Pro-0813 | 1024 | 7.36% | 87.3 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 32.3 | 33,075.9 |
| DeepSeek-V4-Pro-0813 | 4096 | 26.34% | 243.4 GB | 100.00% | 25,902.15 TB/s | 25,902.15 TB/s | 8.1 | 33,091.6 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 23 |
| gpu | infeasible | 21 |
| gpu | link_latency | 305 |
| gpu | weight_read | 891 |
| rom | compute | 754 |
| rom | infeasible | 1602 |
| rom | kv_read | 71 |
| rom | link_latency | 890 |
| rom | weight_read | 463 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 21 |
| rom | CAPACITY | 1602 |

## Mechanical consistency audit

**FAIL** over 106,257 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x195', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x196', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x232', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x278', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x326', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x327', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x370', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x195', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x196', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x232', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x278', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x326', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x327', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x370', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x195', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x196', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x232', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x278', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x326', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x327', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x370', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x195', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x196', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x232', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x278', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x326', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x327', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x370', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x5', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x195', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x196', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x227', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x232', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x278', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x326', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x327', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x340', 'DeepSeek-V4-Pro-0813', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x370', 'DeepSeek-V4-Pro-0813', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 71 |
| derived | 47 |
| assumed | 67 |

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

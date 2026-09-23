# Area-constrained roofline: n6_vs_a100-flash-1m

> CONTEXT-LADDER RUNG of n6_vs_a100: DeepSeek-V4-Flash-0731 at 1,000,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 1,787x (ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream, 2,610 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 34 devices. On the GPU side the correction reaches 65x (a100_sxm_80gb-x2574-pipeline, 2,574 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 111 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Flash-0731 takes 50 x 815 mm2 (40,750 mm2, array, KV in SRAM) at 10,082 tok/s per user and 247 tok/s per 1,000 mm2, holding 1 session, against 49 copies of one unified HBM die at the same silicon: 10.4x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Flash-0731 on 51,345 mm2 of ROM silicon at 11,704 tok/s per user against 51,212 mm2 of a100_sxm_80gb-x62-tensor at 1,004 tok/s: **11.7x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 624. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 8.57x to it.** At 185,005 mm2 on DeepSeek-V4-Flash-0731 the pipeline-only GPU delivers 127.71 tok/s and the same silicon running tensor delivers 1,094 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.34x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`) to 0.40x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 978 to 425,081 tok/s, and its rate with every slot occupied from 383,223 to 425,081. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 392 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,219 us over NVLink, capping per-user decode at 821 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 279.4 us and cap it at 3,579 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 5.2x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 0 of 10 operating points and an array 10; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 201 of 1875 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 16.4x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 13.96x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.04x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 10 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### DeepSeek-V4-Flash-0731 at 1,000,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x50`** -- 50 x 815 mm2 reticle dies, 40,750 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **10,082.3 tok/s per user** (0.10 ms/token), binding on `link_latency`
- **247.4 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 10,082 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 2,878 W at 0.071 W/mm2, 285.4 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 49 copies of one unified HBM die -- `a100_sxm_80gb-x49-tensor`, 40,474 mm2, area ratio 1.0068 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 40,750 | 40,474 | 1.0068 |
| user tok/s | 10,082.3 | 973.2 | 10.36x |
| aggregate tok/s | 10,082 | 973 | 1.61x |
| resident sessions | 1 | 488 | -- |
| J/token | 0.2854 | 8.6147 | 30.2x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 488 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x224-tensor` at 185,024 mm2 and 1,094.5 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-array-hw-tensor-x57` | 46,455 | 11,174.6 | 240.5 | 1 | 11.26x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill` | 51,345 | 11,704.1 | 228.0 | 1 | 11.66x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x48` | 39,120 | 9,582.0 | 244.9 | 1 | 9.89x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x50` | 40,750 | 10,082.3 | 247.4 | 1 | 10.36x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x50` | 40,750 | 10,082.3 | 247.4 | -- | 247.4 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x57` | 46,455 | 11,174.6 | 240.5 | 191.5 | 247.4 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x61` | 49,715 | 11,552.7 | 232.4 | 164.0 | 247.4 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill` | 51,345 | 11,704.1 | 228.0 | 153.1 | 247.4 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x50` **<-- recommended** | 40,750 | 50 | 10,082.3 | 10,082 | 247.4 | 1 | `link_latency` | 2,878 | 285.4 | `a100_sxm_80gb-x49-tensor` | 10.36x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x57` | 46,455 | 57 | 11,174.6 | 11,175 | 240.5 | 1 | `link_latency` | 3,719 | 332.8 | `a100_sxm_80gb-x56-tensor` | 11.26x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x61` | 49,715 | 61 | 11,552.7 | 11,553 | 232.4 | 1 | `link_latency` | 4,197 | 363.3 | `a100_sxm_80gb-x60-tensor` | 11.56x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill` | 51,345 | 63 | 11,704.1 | 11,704 | 228.0 | 1 | `link_latency` | 4,435 | 379.0 | `a100_sxm_80gb-x62-tensor` | 11.66x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 180 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x50` | 40,750 | 10,082.3 | 247.4 | 1 |
| array | 180 | fastest | `ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill` | 51,345 | 11,704.1 | 228.0 | 1 |
| array | 180 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x48` | 39,120 | 9,582.0 | 244.9 | 1 |
| wafer | 46 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,165.8 | 111.8 | 1 |
| wafer | 46 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 5,380.2 | 38.8 | 1 |
| wafer | 46 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 5,165.8 | 111.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill` | 51,345 | 11,704.1 | 11,704 | 1 | 4,435 | 379.0 | `link_latency` | `a100_sxm_80gb-x62-tensor` | 1,003.9 | 624 | 10,261.5 | 1.003 | 11.66x | 27.1x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 5,380.2 | 5,380 | 1 | 17,015 | 3,162.6 | `link_latency` | `a100_sxm_80gb-x168-tensor` | 1,082.1 | 1,732 | 23,761.2 | 0.999 | 4.97x | 7.5x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-hybrid-x170` | 138,550 | 7,716.6 | 7,717 | 1 | 17,028 | 2,206.6 | `weight_read` | `a100_sxm_80gb-x168-tensor` | 1,082.1 | 1,732 | 23,761.2 | 0.998 | 7.13x | 10.8x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 5,380.2 | -- | 1 | -- | 3,162.6 | -- | -- | -- | -- | -- | 0.999 | 0.70x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 319,480 | 5,202.7 | 10,405 | 4,098 | 50,683 | 4,870.8 | `link_latency` | `a100_sxm_80gb-x387-tensor` | 742.8 | 4,022 | 38,544.2 | 0.999 | 7.00x | 7.9x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 2,126,350 | 3,457.0 | 159,024 | 4,136 | 224,537 | 28,764.7 | `link_latency` | `a100_sxm_80gb-x2574-tensor` | 754.3 | 26,890 | 247,285.4 | 1.000 | 4.58x | 8.6x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 319,480 | 4,999.4 | 19,998 | 4,098 | 52,277 | 2,614.1 | `link_latency` | `a100_sxm_80gb-x387-hybrid` | 656.1 | 4,022 | 22,635.5 | 0.999 | 7.62x | 8.5x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 2,126,350 | 3,457.0 | 159,024 | 4,136 | 224,537 | 14,466.7 | `link_latency` | `a100_sxm_80gb-x2574-tensor` | 662.7 | 26,890 | 140,911.3 | 1.000 | 5.22x | 9.7x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 319,480 | 4,637.1 | 37,097 | 4,098 | 55,116 | 1,485.7 | `link_latency` | `a100_sxm_80gb-x387-hybrid` | 656.1 | 4,022 | 11,990.1 | 0.999 | 7.07x | 8.1x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 2,126,350 | 3,457.0 | 159,024 | 4,136 | 224,537 | 7,317.7 | `link_latency` | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 26,890 | 71,605.1 | 1.000 | 5.23x | 9.8x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 319,480 | 4,050.1 | 64,801 | 4,098 | 59,713 | 921.5 | `link_latency` | `a100_sxm_80gb-x387-hybrid` | 656.1 | 4,022 | 6,667.4 | 0.999 | 6.17x | 7.2x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 2,126,350 | 3,457.0 | 159,024 | 4,136 | 224,537 | 3,743.2 | `link_latency` | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 26,890 | 36,474.9 | 1.000 | 5.23x | 9.7x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 319,480 | 4,014.6 | 393,434 | 4,098 | 101,840 | 444.9 | `kv_read` | `a100_sxm_80gb-x387-hybrid` | 656.1 | 4,022 | 4,006.0 | 0.999 | 6.12x | 9.0x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x46-romfill` | 2,126,350 | 3,457.0 | 159,024 | 4,136 | 224,537 | 1,955.9 | `link_latency` | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 26,890 | 18,909.8 | 1.000 | 5.23x | 9.7x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 319,480 | 4,014.6 | 393,434 | 4,098 | 101,840 | 306.8 | `kv_read` | `a100_sxm_80gb-x387-hybrid` | 607.7 | 4,022 | 2,588.8 | 0.999 | 6.61x | 8.4x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,126,350 | 3,019.5 | 193,247 | 4,136 | 343,449 | 1,777.2 | `link_latency` | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 26,890 | 10,127.2 | 1.000 | 4.57x | 5.7x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 319,480 | 1,609.9 | 412,135 | 4,098 | 117,831 | 285.9 | `kv_read` | `a100_sxm_80gb-x387-hybrid` | 317.3 | 4,022 | 1,354.8 | 0.999 | 5.07x | 3.4x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,126,350 | 1,284.9 | 328,923 | 4,136 | 365,796 | 1,112.1 | `kv_read` | `a100_sxm_80gb-x2574-hybrid` | 661.2 | 26,890 | 3,540.3 | 1.000 | 1.94x | 3.0x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 319,480 | 413.4 | 423,274 | 4,098 | 119,693 | 282.8 | `kv_read` | `a100_sxm_80gb-x387-expert` | 177.6 | 3,969 | 488.8 | 0.999 | 2.33x | 1.7x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x46` | 2,126,350 | 389.6 | 398,945 | 4,136 | 377,265 | 945.7 | `kv_read` | `a100_sxm_80gb-x2574-hybrid` | 424.5 | 26,890 | 1,630.7 | 1.000 | 0.92x | 1.1x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 319,480 | 103.8 | 425,081 | 4,098 | 119,663 | 281.5 | `kv_read` | `a100_sxm_80gb-x387-pipeline` | 0.0 | 4,022 | 1,036.1 | 0.999 | --x | --x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x46` | 2,126,350 | 104.7 | 428,854 | 4,136 | 382,941 | 892.9 | `kv_read` | `a100_sxm_80gb-x2574-expert` | 261.2 | 26,529 | 516.9 | 1.000 | 0.40x | 0.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x50` | 40,750 | array | SRAM | 1 |
| 2-16 | `ROM-N6-native-HBMKV-array-hw-tensor-x392` | 319,480 | array | HBM | 4,098 |
| 32-64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 319,480 | array | HBM | 4,098 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 319,480 | array | HBM | 4,098 |
| 1024-4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 319,480 | array | HBM | 4,098 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 392 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 392 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 48, 57, 61, 63, 68, 76, 77, 82, 113, 114, 152, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 48, 50, 57, 61, 76, 78, 113, 114, 142, 144, 152, 170, 227, 340 |

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

- **0 of 1,875 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 120 | 0 | 65.8% | 79.7% | 0.386 | 55% |
| gpu | wafer (>=40,000 mm2) | 903 | 0 | 63.9% | 79.8% | 0.386 | 56% |
| rom | large array (5,000-40,000 mm2) | 60 | 0 | 13.1% | 14.5% | 0.072 | 99% |
| rom | wafer (>=40,000 mm2) | 792 | 0 | 20.5% | 74.9% | 0.375 | 94% |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,455 | `DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x57` | 0.332850 | 3,719.5 | link_latency | `DSV4-Flash/a100_sxm_80gb-x56-tensor` | 9.494153 | 9,419.7 | link_latency | 28.52x |
| DeepSeek-V4-Flash-0731 | 2 | 319,480 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392` | 4.870823 | 50,683.0 | link_latency | `DSV4-Flash/a100_sxm_80gb-x387-tensor` | 38.544232 | 57,261.5 | link_latency | 7.91x |
| DeepSeek-V4-Flash-0731 | 4 | 319,480 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392` | 2.614121 | 52,276.6 | link_latency | `DSV4-Flash/a100_sxm_80gb-x387-hybrid` | 22.635486 | 99,108.0 | weight_read | 8.50x |
| DeepSeek-V4-Flash-0731 | 8 | 319,480 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392` | 1.485736 | 55,116.2 | link_latency | `DSV4-Flash/a100_sxm_80gb-x387-hybrid` | 11.990091 | 99,108.0 | weight_read | 8.07x |
| DeepSeek-V4-Flash-0731 | 16 | 319,480 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392` | 0.921482 | 59,712.8 | link_latency | `DSV4-Flash/a100_sxm_80gb-x387-hybrid` | 6.667394 | 99,108.0 | weight_read | 7.24x |
| DeepSeek-V4-Flash-0731 | 32 | 319,480 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 0.444859 | 101,839.8 | kv_read | `DSV4-Flash/a100_sxm_80gb-x387-hybrid` | 4.006045 | 99,108.0 | weight_read | 9.01x |
| DeepSeek-V4-Flash-0731 | 64 | 319,480 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill` | 0.306760 | 101,839.8 | kv_read | `DSV4-Flash/a100_sxm_80gb-x387-hybrid` | 2.588760 | 100,679.9 | weight_read | 8.44x |
| DeepSeek-V4-Flash-0731 | 256 | 319,480 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x392` | 0.285904 | 117,831.1 | kv_read | `DSV4-Flash/a100_sxm_80gb-x387-hybrid` | 1.354764 | 110,059.6 | weight_read | 3.37x |
| DeepSeek-V4-Flash-0731 | 1024 | 319,480 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x392` | 0.282779 | 119,693.0 | kv_read | `DSV4-Flash/a100_sxm_80gb-x387-expert` | 0.488805 | 88,884.5 | kv_read | 1.73x |
| DeepSeek-V4-Flash-0731 | 4096 | 2,126,350 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46` | 0.892939 | 382,940.7 | kv_read | `DSV4-Flash/a100_sxm_80gb-x2574-expert` | 0.516902 | 553,121.2 | kv_read | 0.58x |

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
| DeepSeek-V4-Flash-0731 | 1,000,000 | 284 B | 166.9 GB | 4.70 | 1.521 GB | 6.886 GB | 7.4 |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 30,046.3 | wafer-pipeline | 5,165.8 | wafer-tensor | 5.82x | 3,915.1 | pipeline | 992.2 | tensor | 3.95x | 7.67x | 5.21x | 0.68x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 45,424.9 | wafer-pipeline | 5,353.7 | wafer-hybrid | 8.48x | 5,360.3 | pipeline | 1,058.1 | tensor | 5.07x | 8.47x | 5.06x | 0.60x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 49,463.3 | wafer-pipeline | 5,380.2 | wafer-hybrid | 9.19x | 6,112.4 | pipeline | 1,082.1 | tensor | 5.65x | 8.09x | 4.97x | 0.61x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 49,463.3 | wafer-pipeline | 5,303.8 | wafer-hybrid | 9.33x | 6,573.6 | pipeline | 1,094.5 | tensor | 6.01x | 7.52x | 4.85x | 0.64x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 50,204.7 | wafer-pipeline | 5,205.5 | wafer-hybrid | 9.64x | 7,110.0 | pipeline | 798.5 | tensor | 8.90x | 7.06x | 6.52x | 0.92x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 50,204.7 | wafer-pipeline | 5,079.8 | wafer-hybrid | 9.88x | 7,412.5 | pipeline | 801.8 | tensor | 9.24x | 6.77x | 6.34x | 0.94x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 50,204.7 | wafer-pipeline | 4,845.8 | wafer-hybrid | 10.36x | 7,741.8 | pipeline | 805.2 | tensor | 9.61x | 6.48x | 6.02x | 0.93x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.60x to 0.94x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x63-romfill | 51,345 | 11,704.1 | 11,704.1 | link_latency | DSV4-Flash/a100_sxm_80gb-x62-tensor | 51,212 | 1.00x | tensor | 859.30 | 1,003.9 | 1,003.9 | link_latency | 11.66x | 1.48x | 91.65x | 11.66x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x48 | 39,120 | 9,582.0 | 9,582.0 | link_latency | DSV4-Flash/a100_sxm_80gb-x47-tensor | 38,822 | 1.01x | tensor | 855.78 | 968.7 | 968.7 | link_latency | 9.89x | 1.60x | 75.03x | 9.89x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392 | 319,480 | 5,202.7 | 10,405.4 | link_latency | DSV4-Flash/a100_sxm_80gb-x387-tensor | 319,662 | 1.00x | tensor | 1,306.28 | 742.8 | 1,485.6 | link_latency | 7.00x | 0.21x | 40.74x | 7.00x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392 | 319,480 | 4,999.4 | 19,997.8 | link_latency | DSV4-Flash/a100_sxm_80gb-x387-hybrid | 319,662 | 1.00x | hybrid | 535.19 | 656.1 | 32,149.5 | weight_read | 7.62x | 0.40x | 39.15x | 7.69x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392 | 319,480 | 4,637.1 | 37,096.9 | link_latency | DSV4-Flash/a100_sxm_80gb-x387-hybrid | 319,662 | 1.00x | hybrid | 535.19 | 656.1 | 32,149.5 | weight_read | 7.07x | 0.75x | 36.31x | 7.13x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392 | 319,480 | 4,050.1 | 64,800.8 | link_latency | DSV4-Flash/a100_sxm_80gb-x387-hybrid | 319,662 | 1.00x | hybrid | 535.19 | 656.1 | 32,149.5 | weight_read | 6.17x | 1.31x | 31.71x | 6.23x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill | 319,480 | 4,014.6 | 393,434.3 | kv_read | DSV4-Flash/a100_sxm_80gb-x387-hybrid | 319,662 | 1.00x | hybrid | 535.19 | 656.1 | 32,149.5 | weight_read | 6.12x | 7.96x | 31.44x | 6.18x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill | 319,480 | 4,014.6 | 393,434.3 | kv_read | DSV4-Flash/a100_sxm_80gb-x387-hybrid | 319,662 | 1.00x | hybrid | 541.29 | 607.7 | 38,891.1 | weight_read | 6.61x | 7.96x | 31.44x | 6.67x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x392 | 319,480 | 1,609.9 | 412,135.0 | kv_read | DSV4-Flash/a100_sxm_80gb-x387-hybrid | 319,662 | 1.00x | hybrid | 619.37 | 317.3 | 81,238.9 | weight_read | 5.07x | 5.07x | 12.61x | 5.11x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x392 | 319,480 | 413.4 | 423,274.0 | kv_read | DSV4-Flash/a100_sxm_80gb-x387-expert | 319,662 | 1.00x | expert | 1,183.48 | 177.6 | 181,840.3 | kv_read | 2.33x | 2.33x | 5.24x | 2.33x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46 | 2,126,350 | 104.7 | 428,854.4 | kv_read | DSV4-Flash/a100_sxm_80gb-x2574-expert | 2,126,124 | 1.00x | expert | 952.30 | 261.2 | 1,070,068.9 | kv_read | 0.40x | 0.40x | 1.00x | 0.40x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x392 | 319,480 | 103.8 | 425,081.1 | kv_read | DSV4-Flash/a100_sxm_80gb-x387-pipeline | 319,662 | 1.00x | pipeline | 130.68 | infeasible | — | capacity_or_format | — | — | — | — |

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
| DeepSeek-V4-Flash-0731 | 22 | 18,172 | 128.6 | 830.1 | 664.4 | tensor | 841.69 | 69.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 23 | 18,998 | 128.5 | 840.7 | 685.3 | tensor | 841.69 | 70.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 34 | 28,084 | 128.1 | 915.6 | 628.1 | tensor | 852.96 | 78.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 47 | 38,822 | 127.7 | 968.7 | 692.1 | tensor | 855.78 | 82.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 49 | 40,474 | 127.7 | 973.2 | 639.2 | tensor | 857.79 | 83.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 56 | 46,256 | 127.7 | 992.2 | 700.9 | tensor | 857.79 | 85.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 59 | 48,734 | 127.7 | 997.6 | 661.9 | tensor | 859.30 | 85.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 60 | 49,560 | 127.7 | 999.8 | 669.6 | tensor | 859.30 | 85.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 61 | 50,386 | 127.7 | 1,001.9 | 677.2 | tensor | 859.30 | 86.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 62 | 51,212 | 127.7 | 1,003.9 | 684.8 | tensor | 859.30 | 86.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 63 | 52,038 | 127.7 | 1,005.9 | 692.3 | tensor | 859.30 | 86.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 67 | 55,342 | 127.7 | 1,012.2 | 665.1 | tensor | 860.47 | 87.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 75 | 61,950 | 127.7 | 1,023.9 | 667.5 | tensor | 861.41 | 88.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 76 | 62,776 | 127.7 | 1,025.3 | 673.6 | tensor | 861.41 | 88.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 77 | 63,602 | 127.7 | 1,026.7 | 679.6 | tensor | 861.41 | 88.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 81 | 66,906 | 127.7 | 1,031.1 | 658.1 | tensor | 862.18 | 88.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 111 | 91,686 | 127.7 | 1,057.4 | 688.7 | tensor | 863.83 | 91.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 112 | 92,512 | 127.7 | 1,058.1 | 692.9 | tensor | 863.83 | 91.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 140 | 115,640 | 127.7 | 1,072.2 | 675.5 | tensor | 865.17 | 92.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 142 | 117,292 | 127.7 | 1,073.1 | 682.0 | tensor | 865.17 | 92.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 150 | 123,900 | 127.7 | 1,076.2 | 681.2 | tensor | 865.42 | 93.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 168 | 138,768 | 127.7 | 1,082.1 | 685.0 | tensor | 865.84 | 93.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 224 | 185,024 | 127.7 | 1,094.5 | 677.4 | tensor | 866.85 | 94.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 335 | 276,710 | 127.7 | 798.4 | 661.3 | tensor | 1,217.01 | 97.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 336 | 277,536 | 127.7 | 798.5 | 662.6 | tensor | 1,217.01 | 97.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 387 | 319,662 | 127.7 | 800.2 | 656.1 | tensor | 1,217.30 | 97.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 395 | 326,270 | 127.7 | 800.5 | 656.2 | tensor | 1,217.34 | 97.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 448 | 370,048 | 127.7 | 801.8 | 661.5 | tensor | 1,217.52 | 97.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 672 | 555,072 | 127.7 | 805.2 | 661.5 | tensor | 1,218.02 | 98.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 2574 | 2,126,124 | 127.7 | 810.3 | 661.2 | tensor | 1,218.76 | 98.8% | link_latency |

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
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x144 | DeepSeek-V4-Flash-0731 | 144 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x61 | DeepSeek-V4-Flash-0731 | 61 | tensor | rom_package_ucie | rom_board_serdes | 172 | 59.98 us | 1,667.3 tok/s | 16,673.0 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 16 on rom_board_serdes (traversals 6.6) = 57.86 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x144 | DeepSeek-V4-Flash-0731 | 144 | hybrid | rom_package_ucie | rom_board_serdes | 121 | 5.78 us | 17,314.3 tok/s | 173,142.9 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 35 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 3.66 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x142 | DeepSeek-V4-Flash-0731 | 142 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x3 | DeepSeek-V4-Flash-0731 | 3 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-tensor-x50 | DeepSeek-V4-Flash-0731 | 50 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x78 | DeepSeek-V4-Flash-0731 | 78 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | DeepSeek-V4-Flash-0731 | 2 | hybrid | on_wafer | rom_wafer_serdes | 87 | 165.65 us | 603.7 tok/s | 6,036.8 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x392 | DeepSeek-V4-Flash-0731 | 392 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392 | DeepSeek-V4-Flash-0731 | 392 | tensor | rom_package_ucie | rom_board_serdes | 172 | 173.56 us | 576.2 tok/s | 5,761.7 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 98 on rom_board_serdes (traversals 19.8) = 171.44 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x392 | DeepSeek-V4-Flash-0731 | 392 | hybrid | rom_package_ucie | rom_board_serdes | 128 | 6.51 us | 15,367.0 tok/s | 153,670.4 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 42 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.39 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x392 | DeepSeek-V4-Flash-0731 | 392 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46 | DeepSeek-V4-Flash-0731 | 46 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-tensor-x392 | DeepSeek-V4-Flash-0731 | 392 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.30 us | 82.1 tok/s | 821.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 781.14 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x46 | DeepSeek-V4-Flash-0731 | 46 | tensor | on_wafer | rom_wafer_serdes | 172 | 279.41 us | 357.9 tok/s | 3,578.9 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us; 86 x all_reduce span 46 on rom_wafer_serdes (traversals 13.2) = 113.86 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x392 | DeepSeek-V4-Flash-0731 | 392 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x46 | DeepSeek-V4-Flash-0731 | 46 | hybrid | on_wafer | rom_wafer_serdes | 128 | 169.81 us | 588.9 tok/s | 5,889.0 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us; 42 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 4.26 us |
| DSV4-Flash/a100_sxm_80gb-x22-pipeline | DeepSeek-V4-Flash-0731 | 22 | pipeline | nvlink3 | infiniband_hdr | 21 | 52.73 us | 1,896.3 tok/s | 18,963.0 tok/s | 19 x point_to_point span 2 on nvlink3 (traversals 1.0) = 48.02 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x22-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x22-hybrid | DeepSeek-V4-Flash-0731 | 22 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x22-expert | DeepSeek-V4-Flash-0731 | 22 | expert | nvlink3 | infiniband_hdr | 172 | 615.35 us | 162.5 tok/s | 1,625.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 182.27 us |
| DSV4-Flash/a100_sxm_80gb-x23-pipeline | DeepSeek-V4-Flash-0731 | 23 | pipeline | nvlink3 | infiniband_hdr | 22 | 55.26 us | 1,809.6 tok/s | 18,095.8 tok/s | 20 x point_to_point span 2 on nvlink3 (traversals 1.0) = 50.55 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x23-tensor | DeepSeek-V4-Flash-0731 | 23 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x23-hybrid | DeepSeek-V4-Flash-0731 | 23 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x23-expert | DeepSeek-V4-Flash-0731 | 23 | expert | nvlink3 | infiniband_hdr | 172 | 615.01 us | 162.6 tok/s | 1,626.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 181.93 us |
| DSV4-Flash/a100_sxm_80gb-x34-pipeline | DeepSeek-V4-Flash-0731 | 34 | pipeline | nvlink3 | infiniband_hdr | 33 | 82.72 us | 1,208.9 tok/s | 12,088.6 tok/s | 29 x point_to_point span 2 on nvlink3 (traversals 1.0) = 73.29 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x34-tensor | DeepSeek-V4-Flash-0731 | 34 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x34-hybrid | DeepSeek-V4-Flash-0731 | 34 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x34-expert | DeepSeek-V4-Flash-0731 | 34 | expert | nvlink3 | infiniband_hdr | 172 | 611.09 us | 163.6 tok/s | 1,636.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 179.55 us |
| DSV4-Flash/a100_sxm_80gb-x47-pipeline | DeepSeek-V4-Flash-0731 | 47 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x47-tensor | DeepSeek-V4-Flash-0731 | 47 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x47-hybrid | DeepSeek-V4-Flash-0731 | 47 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x47-expert | DeepSeek-V4-Flash-0731 | 47 | expert | nvlink3 | infiniband_hdr | 172 | 609.41 us | 164.1 tok/s | 1,640.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.18 us |
| DSV4-Flash/a100_sxm_80gb-x49-pipeline | DeepSeek-V4-Flash-0731 | 49 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x49-tensor | DeepSeek-V4-Flash-0731 | 49 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x49-hybrid | DeepSeek-V4-Flash-0731 | 49 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x49-expert | DeepSeek-V4-Flash-0731 | 49 | expert | nvlink3 | infiniband_hdr | 172 | 609.06 us | 164.2 tok/s | 1,641.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.03 us |
| DSV4-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Flash-0731 | 56 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Flash-0731 | 56 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Flash-0731 | 56 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x56-expert | DeepSeek-V4-Flash-0731 | 56 | expert | nvlink3 | infiniband_hdr | 172 | 608.48 us | 164.3 tok/s | 1,643.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.60 us |
| DSV4-Flash/a100_sxm_80gb-x59-pipeline | DeepSeek-V4-Flash-0731 | 59 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x59-tensor | DeepSeek-V4-Flash-0731 | 59 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x59-hybrid | DeepSeek-V4-Flash-0731 | 59 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x59-expert | DeepSeek-V4-Flash-0731 | 59 | expert | nvlink3 | infiniband_hdr | 172 | 608.33 us | 164.4 tok/s | 1,643.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.45 us |
| DSV4-Flash/a100_sxm_80gb-x60-pipeline | DeepSeek-V4-Flash-0731 | 60 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x60-tensor | DeepSeek-V4-Flash-0731 | 60 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x60-hybrid | DeepSeek-V4-Flash-0731 | 60 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x60-expert | DeepSeek-V4-Flash-0731 | 60 | expert | nvlink3 | infiniband_hdr | 172 | 608.28 us | 164.4 tok/s | 1,644.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.40 us |
| DSV4-Flash/a100_sxm_80gb-x61-pipeline | DeepSeek-V4-Flash-0731 | 61 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x61-tensor | DeepSeek-V4-Flash-0731 | 61 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x61-hybrid | DeepSeek-V4-Flash-0731 | 61 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x61-expert | DeepSeek-V4-Flash-0731 | 61 | expert | nvlink3 | infiniband_hdr | 172 | 608.23 us | 164.4 tok/s | 1,644.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.35 us |
| DSV4-Flash/a100_sxm_80gb-x62-pipeline | DeepSeek-V4-Flash-0731 | 62 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x62-tensor | DeepSeek-V4-Flash-0731 | 62 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x62-hybrid | DeepSeek-V4-Flash-0731 | 62 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x62-expert | DeepSeek-V4-Flash-0731 | 62 | expert | nvlink3 | infiniband_hdr | 172 | 608.19 us | 164.4 tok/s | 1,644.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.31 us |
| DSV4-Flash/a100_sxm_80gb-x63-pipeline | DeepSeek-V4-Flash-0731 | 63 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x63-tensor | DeepSeek-V4-Flash-0731 | 63 | tensor | nvlink3 | infiniband_hdr | 172 | 859.30 us | 116.4 tok/s | 1,163.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 423.13 us |
| DSV4-Flash/a100_sxm_80gb-x63-hybrid | DeepSeek-V4-Flash-0731 | 63 | hybrid | nvlink3 | infiniband_hdr | 93 | 452.67 us | 220.9 tok/s | 2,209.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| DSV4-Flash/a100_sxm_80gb-x63-expert | DeepSeek-V4-Flash-0731 | 63 | expert | nvlink3 | infiniband_hdr | 172 | 608.14 us | 164.4 tok/s | 1,644.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.26 us |
| DSV4-Flash/a100_sxm_80gb-x67-pipeline | DeepSeek-V4-Flash-0731 | 67 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x67-tensor | DeepSeek-V4-Flash-0731 | 67 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x67-hybrid | DeepSeek-V4-Flash-0731 | 67 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x67-expert | DeepSeek-V4-Flash-0731 | 67 | expert | nvlink3 | infiniband_hdr | 172 | 607.87 us | 164.5 tok/s | 1,645.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.77 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.10 us |
| DSV4-Flash/a100_sxm_80gb-x75-pipeline | DeepSeek-V4-Flash-0731 | 75 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x75-tensor | DeepSeek-V4-Flash-0731 | 75 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x75-hybrid | DeepSeek-V4-Flash-0731 | 75 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x75-expert | DeepSeek-V4-Flash-0731 | 75 | expert | nvlink3 | infiniband_hdr | 172 | 607.52 us | 164.6 tok/s | 1,646.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.68 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.83 us |
| DSV4-Flash/a100_sxm_80gb-x76-pipeline | DeepSeek-V4-Flash-0731 | 76 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x76-tensor | DeepSeek-V4-Flash-0731 | 76 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x76-hybrid | DeepSeek-V4-Flash-0731 | 76 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x76-expert | DeepSeek-V4-Flash-0731 | 76 | expert | nvlink3 | infiniband_hdr | 172 | 607.49 us | 164.6 tok/s | 1,646.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.68 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.80 us |
| DSV4-Flash/a100_sxm_80gb-x77-pipeline | DeepSeek-V4-Flash-0731 | 77 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x77-tensor | DeepSeek-V4-Flash-0731 | 77 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x77-hybrid | DeepSeek-V4-Flash-0731 | 77 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x77-expert | DeepSeek-V4-Flash-0731 | 77 | expert | nvlink3 | infiniband_hdr | 172 | 607.46 us | 164.6 tok/s | 1,646.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.68 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.78 us |
| DSV4-Flash/a100_sxm_80gb-x81-pipeline | DeepSeek-V4-Flash-0731 | 81 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x81-tensor | DeepSeek-V4-Flash-0731 | 81 | tensor | nvlink3 | infiniband_hdr | 172 | 862.18 us | 116.0 tok/s | 1,159.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 426.02 us |
| DSV4-Flash/a100_sxm_80gb-x81-hybrid | DeepSeek-V4-Flash-0731 | 81 | hybrid | nvlink3 | infiniband_hdr | 96 | 459.74 us | 217.5 tok/s | 2,175.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| DSV4-Flash/a100_sxm_80gb-x81-expert | DeepSeek-V4-Flash-0731 | 81 | expert | nvlink3 | infiniband_hdr | 172 | 607.28 us | 164.7 tok/s | 1,646.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.62 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.67 us |
| DSV4-Flash/a100_sxm_80gb-x111-pipeline | DeepSeek-V4-Flash-0731 | 111 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x111-tensor | DeepSeek-V4-Flash-0731 | 111 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x111-hybrid | DeepSeek-V4-Flash-0731 | 111 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x111-expert | DeepSeek-V4-Flash-0731 | 111 | expert | nvlink3 | infiniband_hdr | 172 | 606.58 us | 164.9 tok/s | 1,648.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.47 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.10 us |
| DSV4-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Flash-0731 | 112 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Flash-0731 | 112 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Flash-0731 | 112 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x112-expert | DeepSeek-V4-Flash-0731 | 112 | expert | nvlink3 | infiniband_hdr | 172 | 606.53 us | 164.9 tok/s | 1,648.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.44 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.09 us |
| DSV4-Flash/a100_sxm_80gb-x140-pipeline | DeepSeek-V4-Flash-0731 | 140 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x140-tensor | DeepSeek-V4-Flash-0731 | 140 | tensor | nvlink3 | infiniband_hdr | 172 | 865.17 us | 115.6 tok/s | 1,155.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 429.00 us |
| DSV4-Flash/a100_sxm_80gb-x140-hybrid | DeepSeek-V4-Flash-0731 | 140 | hybrid | nvlink3 | infiniband_hdr | 103 | 476.25 us | 210.0 tok/s | 2,099.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| DSV4-Flash/a100_sxm_80gb-x140-expert | DeepSeek-V4-Flash-0731 | 140 | expert | nvlink3 | infiniband_hdr | 172 | 606.15 us | 165.0 tok/s | 1,649.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.36 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.79 us |
| DSV4-Flash/a100_sxm_80gb-x142-pipeline | DeepSeek-V4-Flash-0731 | 142 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x142-tensor | DeepSeek-V4-Flash-0731 | 142 | tensor | nvlink3 | infiniband_hdr | 172 | 865.17 us | 115.6 tok/s | 1,155.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 429.00 us |
| DSV4-Flash/a100_sxm_80gb-x142-hybrid | DeepSeek-V4-Flash-0731 | 142 | hybrid | nvlink3 | infiniband_hdr | 103 | 476.25 us | 210.0 tok/s | 2,099.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| DSV4-Flash/a100_sxm_80gb-x142-expert | DeepSeek-V4-Flash-0731 | 142 | expert | nvlink3 | infiniband_hdr | 172 | 606.13 us | 165.0 tok/s | 1,649.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.36 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.77 us |
| DSV4-Flash/a100_sxm_80gb-x150-pipeline | DeepSeek-V4-Flash-0731 | 150 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x150-tensor | DeepSeek-V4-Flash-0731 | 150 | tensor | nvlink3 | infiniband_hdr | 172 | 865.42 us | 115.6 tok/s | 1,155.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 429.25 us |
| DSV4-Flash/a100_sxm_80gb-x150-hybrid | DeepSeek-V4-Flash-0731 | 150 | hybrid | nvlink3 | infiniband_hdr | 104 | 478.60 us | 208.9 tok/s | 2,089.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 42.44 us |
| DSV4-Flash/a100_sxm_80gb-x150-expert | DeepSeek-V4-Flash-0731 | 150 | expert | nvlink3 | infiniband_hdr | 172 | 606.05 us | 165.0 tok/s | 1,650.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.34 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.71 us |
| DSV4-Flash/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Flash-0731 | 168 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Flash-0731 | 168 | tensor | nvlink3 | infiniband_hdr | 172 | 865.84 us | 115.5 tok/s | 1,154.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 429.68 us |
| DSV4-Flash/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Flash-0731 | 168 | hybrid | nvlink3 | infiniband_hdr | 106 | 483.32 us | 206.9 tok/s | 2,069.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.15 us |
| DSV4-Flash/a100_sxm_80gb-x168-expert | DeepSeek-V4-Flash-0731 | 168 | expert | nvlink3 | infiniband_hdr | 172 | 605.88 us | 165.0 tok/s | 1,650.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.29 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.59 us |
| DSV4-Flash/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Flash-0731 | 224 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Flash-0731 | 224 | tensor | nvlink3 | infiniband_hdr | 172 | 866.85 us | 115.4 tok/s | 1,153.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 430.68 us |
| DSV4-Flash/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Flash-0731 | 224 | hybrid | nvlink3 | infiniband_hdr | 113 | 499.82 us | 200.1 tok/s | 2,000.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.66 us |
| DSV4-Flash/a100_sxm_80gb-x224-expert | DeepSeek-V4-Flash-0731 | 224 | expert | nvlink3 | infiniband_hdr | 172 | 605.55 us | 165.1 tok/s | 1,651.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.22 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.33 us |
| DSV4-Flash/a100_sxm_80gb-x335-pipeline | DeepSeek-V4-Flash-0731 | 335 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x335-tensor | DeepSeek-V4-Flash-0731 | 335 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.01 us | 82.2 tok/s | 821.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 780.85 us |
| DSV4-Flash/a100_sxm_80gb-x335-hybrid | DeepSeek-V4-Flash-0731 | 335 | hybrid | nvlink3 | infiniband_hdr | 127 | 532.83 us | 187.7 tok/s | 1,876.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| DSV4-Flash/a100_sxm_80gb-x335-expert | DeepSeek-V4-Flash-0731 | 335 | expert | nvlink3 | infiniband_hdr | 172 | 605.24 us | 165.2 tok/s | 1,652.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.15 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.08 us |
| DSV4-Flash/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Flash-0731 | 336 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Flash-0731 | 336 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.01 us | 82.2 tok/s | 821.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 780.85 us |
| DSV4-Flash/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Flash-0731 | 336 | hybrid | nvlink3 | infiniband_hdr | 127 | 532.83 us | 187.7 tok/s | 1,876.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| DSV4-Flash/a100_sxm_80gb-x336-expert | DeepSeek-V4-Flash-0731 | 336 | expert | nvlink3 | infiniband_hdr | 172 | 605.23 us | 165.2 tok/s | 1,652.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.15 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.08 us |
| DSV4-Flash/a100_sxm_80gb-x387-pipeline | DeepSeek-V4-Flash-0731 | 387 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x387-tensor | DeepSeek-V4-Flash-0731 | 387 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.30 us | 82.1 tok/s | 821.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 781.14 us |
| DSV4-Flash/a100_sxm_80gb-x387-hybrid | DeepSeek-V4-Flash-0731 | 387 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x387-expert | DeepSeek-V4-Flash-0731 | 387 | expert | nvlink3 | infiniband_hdr | 172 | 605.15 us | 165.2 tok/s | 1,652.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.13 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.02 us |
| DSV4-Flash/a100_sxm_80gb-x395-pipeline | DeepSeek-V4-Flash-0731 | 395 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x395-tensor | DeepSeek-V4-Flash-0731 | 395 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.34 us | 82.1 tok/s | 821.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 50 on infiniband_hdr (traversals 4.0) = 781.17 us |
| DSV4-Flash/a100_sxm_80gb-x395-hybrid | DeepSeek-V4-Flash-0731 | 395 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x395-expert | DeepSeek-V4-Flash-0731 | 395 | expert | nvlink3 | infiniband_hdr | 172 | 605.13 us | 165.3 tok/s | 1,652.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.13 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.01 us |
| DSV4-Flash/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Flash-0731 | 448 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Flash-0731 | 448 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.52 us | 82.1 tok/s | 821.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 781.35 us |
| DSV4-Flash/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Flash-0731 | 448 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x448-expert | DeepSeek-V4-Flash-0731 | 448 | expert | nvlink3 | infiniband_hdr | 172 | 605.07 us | 165.3 tok/s | 1,652.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.11 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 174.96 us |
| DSV4-Flash/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Flash-0731 | 672 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Flash-0731 | 672 | tensor | nvlink3 | infiniband_hdr | 172 | 1,218.02 us | 82.1 tok/s | 821.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 781.85 us |
| DSV4-Flash/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Flash-0731 | 672 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x672-expert | DeepSeek-V4-Flash-0731 | 672 | expert | nvlink3 | infiniband_hdr | 172 | 604.90 us | 165.3 tok/s | 1,653.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.07 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 174.83 us |
| DSV4-Flash/a100_sxm_80gb-x2574-pipeline | DeepSeek-V4-Flash-0731 | 2574 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x2574-tensor | DeepSeek-V4-Flash-0731 | 2574 | tensor | nvlink3 | infiniband_hdr | 172 | 1,218.76 us | 82.1 tok/s | 820.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 322 on infiniband_hdr (traversals 4.0) = 782.60 us |
| DSV4-Flash/a100_sxm_80gb-x2574-hybrid | DeepSeek-V4-Flash-0731 | 2574 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x2574-expert | DeepSeek-V4-Flash-0731 | 2574 | expert | nvlink3 | infiniband_hdr | 172 | 604.66 us | 165.4 tok/s | 1,653.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.02 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 174.65 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 1 | array | array | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x57 | 46,455 | 11,174.6 | 0.241 | 11,174.6 (46,455) | 5,165.8 (46,225) | 0.46x | link_latency |
| DeepSeek-V4-Flash-0731 | 2 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392 | 319,480 | 5,202.7 | 0.016 | 5,202.7 (319,480) | 3,457.0 (2,126,350) | 0.66x | link_latency |
| DeepSeek-V4-Flash-0731 | 4 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392 | 319,480 | 4,999.4 | 0.016 | 4,999.4 (319,480) | 3,457.0 (2,126,350) | 0.69x | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392 | 319,480 | 4,637.1 | 0.015 | 4,637.1 (319,480) | 3,457.0 (2,126,350) | 0.75x | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392 | 319,480 | 4,050.1 | 0.013 | 4,050.1 (319,480) | 3,457.0 (2,126,350) | 0.85x | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill | 319,480 | 4,014.6 | 0.013 | 4,014.6 (319,480) | 3,457.0 (2,126,350) | 0.86x | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x392-romfill | 319,480 | 4,014.6 | 0.013 | 4,014.6 (319,480) | 3,019.5 (2,126,350) | 0.75x | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x392 | 319,480 | 1,609.9 | 0.005 | 1,609.9 (319,480) | 1,284.9 (2,126,350) | 0.80x | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x392 | 319,480 | 413.4 | 0.001 | 413.4 (319,480) | 389.6 (2,126,350) | 0.94x | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x392 | 319,480 | 103.8 | 0.000 | 103.8 (319,480) | 104.7 (2,126,350) | 1.01x | kv_read |

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
| DeepSeek-V4-Flash-0731 | 256 | 574.9 MB | 126.1 mm2 | 22.70 mm2 (18.0%) | 32,278 mm2 | 5,810 mm2 | 36,600 mm2 = 44.9 reticles |

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
| DeepSeek-V4-Flash-0731 | 1 | sram | 387,455.6 | 26,108.5 | 26,108.5 | 14.84x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 387,455.6 | 26,108.5 | 26,108.5 | 14.84x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 387,455.6 | 26,108.5 | 26,108.5 | 14.84x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 387,455.6 | 26,108.5 | 31,812.2 | 14.84x | 1.22x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | sram | 387,455.6 | 26,108.5 | 50,039.6 | 14.84x | 1.92x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | sram | 387,455.6 | 26,108.5 | 82,380.3 | 14.84x | 3.16x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | sram | 387,455.6 | 26,108.5 | 126,124.1 | 14.84x | 4.83x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | sram | 412,135.0 | 26,108.5 | 262,419.8 | 15.79x | 10.05x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 423,274.0 | 26,108.5 | 338,204.2 | 16.21x | 12.95x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 428,854.4 | 26,110.7 | 364,521.8 | 16.42x | 13.96x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 428,403.9 | 428,403.9 | 428,403.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 428,403.9 | 428,403.9 | 428,403.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 428,403.9 | 428,403.9 | 428,403.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 428,403.9 | 428,403.9 | 428,403.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 428,403.9 | 428,403.9 | 428,403.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 428,403.9 | 428,403.9 | 428,403.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 428,403.9 | 428,403.9 | 428,403.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 428,403.9 | 428,403.9 | 428,403.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 428,403.9 | 428,403.9 | 428,403.9 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 428,854.4 | 428,854.4 | 428,854.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46 | 2,126,350 | 1.00 | 1.00 | 387,455.6 | 0.182 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-romfill | 2,126,350 | 40.44 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream | 2,126,350 | 1.00 | 1.00 | 26,108.5 | 0.012 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion | 2,126,350 | 1.00 | 1.00 | 26,108.5 | 0.012 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46 | 2,126,350 | 1.00 | 1.00 | 387,455.6 | 0.182 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-romfill | 2,126,350 | 40.44 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream | 2,126,350 | 1.00 | 1.00 | 26,108.5 | 0.012 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion | 2,126,350 | 1.00 | 1.00 | 26,108.5 | 0.012 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46 | 2,126,350 | 1.00 | 1.00 | 387,455.6 | 0.182 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-romfill | 2,126,350 | 40.44 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream | 2,126,350 | 1.00 | 1.00 | 26,108.5 | 0.012 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion | 2,126,350 | 1.00 | 1.00 | 26,108.5 | 0.012 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46 | 2,126,350 | 1.00 | 1.00 | 387,455.6 | 0.182 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-romfill | 2,126,350 | 40.44 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream | 2,126,350 | 1.00 | 1.00 | 26,108.5 | 0.012 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.13 | 31,812.2 | 0.688 | link_latency | 0.08x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46 | 2,126,350 | 1.00 | 1.00 | 387,455.6 | 0.182 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-romfill | 2,126,350 | 40.44 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream | 2,126,350 | 1.00 | 1.00 | 26,108.5 | 0.012 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392-perregion | 319,480 | 1.00 | 2.88 | 50,039.6 | 0.157 | link_latency | 0.13x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46 | 2,126,350 | 1.00 | 1.00 | 387,455.6 | 0.182 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-romfill | 2,126,350 | 40.44 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream | 2,126,350 | 1.00 | 1.00 | 26,108.5 | 0.012 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392-perregion | 319,480 | 1.00 | 4.03 | 82,380.3 | 0.258 | link_latency | 0.21x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46 | 2,126,350 | 1.00 | 1.00 | 387,455.6 | 0.182 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-romfill | 2,126,350 | 40.44 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream | 2,126,350 | 1.00 | 1.00 | 26,108.5 | 0.012 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x392-perregion | 319,480 | 1.00 | 5.83 | 126,124.1 | 0.395 | link_latency | 0.33x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.11x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x392 | 319,480 | 1.00 | 1.00 | 412,135.0 | 1.290 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-romfill | 2,126,350 | 40.44 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.04x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream | 2,126,350 | 1.00 | 1.00 | 26,108.5 | 0.012 | weight_read | 0.06x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.04x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x46-perregion | 2,126,350 | 1.00 | 13.84 | 262,419.8 | 0.123 | kv_read | 0.64x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.04x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x392 | 319,480 | 1.00 | 1.00 | 423,274.0 | 1.325 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-romfill | 2,126,350 | 40.44 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.01x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream | 2,126,350 | 1.00 | 1.00 | 26,108.5 | 0.012 | weight_read | 0.06x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.01x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x46-perregion | 2,126,350 | 1.00 | 38.75 | 338,204.2 | 0.159 | kv_read | 0.80x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion-romfill | 2,126,350 | 146.57 | 1.00 | 428,403.9 | 0.201 | kv_read | 1.01x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46 | 2,126,350 | 1.00 | 1.00 | 428,854.4 | 0.202 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-romfill | 2,126,350 | 40.44 | 1.00 | 428,854.4 | 0.202 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x392-perstream | 319,480 | 1.00 | 10.45 | 26,110.7 | 0.082 | weight_read | 0.06x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perstream-romfill | 2,126,350 | 146.57 | 1.57 | 428,854.4 | 0.202 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x46-perregion | 2,126,350 | 1.00 | 124.47 | 364,521.8 | 0.171 | kv_read | 0.85x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x46-perregion-romfill | 2,126,350 | 146.57 | 1.07 | 428,854.4 | 0.202 | kv_read | 1.00x |

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
| DeepSeek-V4-Flash-0731 | 1 | 22 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 392 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 392 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 392 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | 392 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 392 | 2.61 | 1.019 | 1.261 | 1.24x |
| DeepSeek-V4-Flash-0731 | 4096 | 392 | 10.45 | 1.116 | 2.348 | 2.10x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 22 | 9.33 | 5.36 | 1.74x |
| DeepSeek-V4-Flash-0731 | 4 | 22 | 14.51 | 7.03 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 22 | 19.19 | 8.83 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 22 | 21.49 | 10.61 | 2.03x |
| DeepSeek-V4-Flash-0731 | 32 | 22 | 21.96 | 12.14 | 1.81x |
| DeepSeek-V4-Flash-0731 | 64 | 22 | 22.00 | 13.24 | 1.66x |
| DeepSeek-V4-Flash-0731 | 1 | 23 | 5.38 | 4.06 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 23 | 9.42 | 5.44 | 1.73x |
| DeepSeek-V4-Flash-0731 | 4 | 23 | 14.79 | 7.16 | 2.07x |
| DeepSeek-V4-Flash-0731 | 8 | 23 | 19.78 | 9.03 | 2.19x |
| DeepSeek-V4-Flash-0731 | 16 | 23 | 22.37 | 10.88 | 2.06x |
| DeepSeek-V4-Flash-0731 | 32 | 23 | 22.95 | 12.49 | 1.84x |
| DeepSeek-V4-Flash-0731 | 64 | 23 | 23.00 | 13.64 | 1.69x |
| DeepSeek-V4-Flash-0731 | 1 | 34 | 5.58 | 4.44 | 1.26x |
| DeepSeek-V4-Flash-0731 | 2 | 34 | 10.14 | 6.09 | 1.66x |
| DeepSeek-V4-Flash-0731 | 4 | 34 | 16.97 | 8.30 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 34 | 24.92 | 10.80 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 34 | 30.96 | 13.41 | 2.31x |
| DeepSeek-V4-Flash-0731 | 32 | 34 | 33.42 | 15.79 | 2.12x |
| DeepSeek-V4-Flash-0731 | 64 | 34 | 33.91 | 17.56 | 1.93x |
| DeepSeek-V4-Flash-0731 | 256 | 34 | 33.98 | 18.68 | 1.82x |
| DeepSeek-V4-Flash-0731 | 1 | 47 | 5.69 | 4.73 | 1.20x |
| DeepSeek-V4-Flash-0731 | 2 | 47 | 10.58 | 6.65 | 1.59x |
| DeepSeek-V4-Flash-0731 | 4 | 47 | 18.44 | 9.26 | 1.99x |
| DeepSeek-V4-Flash-0731 | 8 | 47 | 28.85 | 12.35 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 47 | 38.74 | 15.72 | 2.46x |
| DeepSeek-V4-Flash-0731 | 32 | 47 | 44.49 | 18.90 | 2.35x |
| DeepSeek-V4-Flash-0731 | 64 | 47 | 46.36 | 21.34 | 2.17x |
| DeepSeek-V4-Flash-0731 | 256 | 47 | 46.81 | 22.91 | 2.04x |
| DeepSeek-V4-Flash-0731 | 1 | 49 | 5.70 | 4.77 | 1.20x |
| DeepSeek-V4-Flash-0731 | 2 | 49 | 10.63 | 6.72 | 1.58x |
| DeepSeek-V4-Flash-0731 | 4 | 49 | 18.61 | 9.38 | 1.98x |
| DeepSeek-V4-Flash-0731 | 8 | 49 | 29.32 | 12.55 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 49 | 39.75 | 16.03 | 2.48x |
| DeepSeek-V4-Flash-0731 | 32 | 49 | 46.04 | 19.33 | 2.38x |
| DeepSeek-V4-Flash-0731 | 64 | 49 | 48.21 | 21.86 | 2.21x |
| DeepSeek-V4-Flash-0731 | 256 | 49 | 48.75 | 23.50 | 2.07x |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 10.77 | 6.96 | 1.55x |
| DeepSeek-V4-Flash-0731 | 4 | 56 | 19.11 | 9.76 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 56 | 30.77 | 13.20 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 56 | 42.95 | 17.03 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 56 | 51.18 | 20.71 | 2.47x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 54.47 | 23.58 | 2.31x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 55.44 | 25.44 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1 | 59 | 5.75 | 4.92 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 59 | 10.83 | 7.05 | 1.53x |
| DeepSeek-V4-Flash-0731 | 4 | 59 | 19.30 | 9.90 | 1.95x |
| DeepSeek-V4-Flash-0731 | 8 | 59 | 31.31 | 13.45 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 59 | 44.18 | 17.43 | 2.54x |
| DeepSeek-V4-Flash-0731 | 32 | 59 | 53.24 | 21.27 | 2.50x |
| DeepSeek-V4-Flash-0731 | 64 | 59 | 57.06 | 24.27 | 2.35x |
| DeepSeek-V4-Flash-0731 | 256 | 59 | 58.25 | 26.23 | 2.22x |
| DeepSeek-V4-Flash-0731 | 1 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 60 | 10.84 | 7.08 | 1.53x |
| DeepSeek-V4-Flash-0731 | 4 | 60 | 19.35 | 9.95 | 1.95x |
| DeepSeek-V4-Flash-0731 | 8 | 60 | 31.48 | 13.54 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 60 | 44.58 | 17.56 | 2.54x |
| DeepSeek-V4-Flash-0731 | 32 | 60 | 53.91 | 21.45 | 2.51x |
| DeepSeek-V4-Flash-0731 | 64 | 60 | 57.91 | 24.50 | 2.36x |
| DeepSeek-V4-Flash-0731 | 256 | 60 | 59.18 | 26.49 | 2.23x |
| DeepSeek-V4-Flash-0731 | 1 | 61 | 5.76 | 4.95 | 1.16x |
| DeepSeek-V4-Flash-0731 | 2 | 61 | 10.86 | 7.12 | 1.53x |
| DeepSeek-V4-Flash-0731 | 4 | 61 | 19.41 | 10.00 | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | 61 | 31.64 | 13.62 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 61 | 44.97 | 17.68 | 2.54x |
| DeepSeek-V4-Flash-0731 | 32 | 61 | 54.57 | 21.63 | 2.52x |
| DeepSeek-V4-Flash-0731 | 64 | 61 | 58.76 | 24.72 | 2.38x |
| DeepSeek-V4-Flash-0731 | 256 | 61 | 60.10 | 26.74 | 2.25x |
| DeepSeek-V4-Flash-0731 | 1 | 62 | 5.76 | 4.96 | 1.16x |
| DeepSeek-V4-Flash-0731 | 2 | 62 | 10.87 | 7.15 | 1.52x |
| DeepSeek-V4-Flash-0731 | 4 | 62 | 19.46 | 10.04 | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | 62 | 31.80 | 13.70 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 62 | 45.35 | 17.81 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 62 | 55.22 | 21.81 | 2.53x |
| DeepSeek-V4-Flash-0731 | 64 | 62 | 59.60 | 24.94 | 2.39x |
| DeepSeek-V4-Flash-0731 | 256 | 62 | 61.03 | 26.99 | 2.26x |
| DeepSeek-V4-Flash-0731 | 1 | 63 | 5.77 | 4.97 | 1.16x |
| DeepSeek-V4-Flash-0731 | 2 | 63 | 10.89 | 7.17 | 1.52x |
| DeepSeek-V4-Flash-0731 | 4 | 63 | 19.51 | 10.08 | 1.94x |
| DeepSeek-V4-Flash-0731 | 8 | 63 | 31.96 | 13.78 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 63 | 45.72 | 17.93 | 2.55x |
| DeepSeek-V4-Flash-0731 | 32 | 63 | 55.87 | 21.98 | 2.54x |
| DeepSeek-V4-Flash-0731 | 64 | 63 | 60.43 | 25.16 | 2.40x |
| DeepSeek-V4-Flash-0731 | 256 | 63 | 61.94 | 27.24 | 2.27x |
| DeepSeek-V4-Flash-0731 | 1 | 67 | 5.78 | 5.02 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 67 | 10.94 | 7.29 | 1.50x |
| DeepSeek-V4-Flash-0731 | 4 | 67 | 19.71 | 10.25 | 1.92x |
| DeepSeek-V4-Flash-0731 | 8 | 67 | 32.55 | 14.09 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 67 | 47.13 | 18.41 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 67 | 58.35 | 22.66 | 2.58x |
| DeepSeek-V4-Flash-0731 | 64 | 67 | 63.68 | 26.01 | 2.45x |
| DeepSeek-V4-Flash-0731 | 256 | 67 | 65.56 | 28.21 | 2.32x |
| DeepSeek-V4-Flash-0731 | 1 | 75 | 5.80 | 5.10 | 1.14x |
| DeepSeek-V4-Flash-0731 | 2 | 75 | 11.04 | 7.50 | 1.47x |
| DeepSeek-V4-Flash-0731 | 4 | 75 | 20.05 | 10.56 | 1.90x |
| DeepSeek-V4-Flash-0731 | 8 | 75 | 33.59 | 14.66 | 2.29x |
| DeepSeek-V4-Flash-0731 | 16 | 75 | 49.66 | 19.31 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 75 | 62.94 | 23.92 | 2.63x |
| DeepSeek-V4-Flash-0731 | 64 | 75 | 69.87 | 27.60 | 2.53x |
| DeepSeek-V4-Flash-0731 | 256 | 75 | 72.57 | 30.04 | 2.42x |
| DeepSeek-V4-Flash-0731 | 1 | 76 | 5.81 | 5.11 | 1.14x |
| DeepSeek-V4-Flash-0731 | 2 | 76 | 11.05 | 7.52 | 1.47x |
| DeepSeek-V4-Flash-0731 | 4 | 76 | 20.08 | 10.59 | 1.90x |
| DeepSeek-V4-Flash-0731 | 8 | 76 | 33.70 | 14.73 | 2.29x |
| DeepSeek-V4-Flash-0731 | 16 | 76 | 49.95 | 19.41 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 76 | 63.48 | 24.07 | 2.64x |
| DeepSeek-V4-Flash-0731 | 64 | 76 | 70.62 | 27.79 | 2.54x |
| DeepSeek-V4-Flash-0731 | 256 | 76 | 73.42 | 30.26 | 2.43x |
| DeepSeek-V4-Flash-0731 | 1 | 77 | 5.81 | 5.12 | 1.14x |
| DeepSeek-V4-Flash-0731 | 2 | 77 | 11.06 | 7.55 | 1.46x |
| DeepSeek-V4-Flash-0731 | 4 | 77 | 20.12 | 10.63 | 1.89x |
| DeepSeek-V4-Flash-0731 | 8 | 77 | 33.82 | 14.80 | 2.29x |
| DeepSeek-V4-Flash-0731 | 16 | 77 | 50.24 | 19.52 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 77 | 64.01 | 24.22 | 2.64x |
| DeepSeek-V4-Flash-0731 | 64 | 77 | 71.35 | 27.98 | 2.55x |
| DeepSeek-V4-Flash-0731 | 256 | 77 | 74.27 | 30.48 | 2.44x |
| DeepSeek-V4-Flash-0731 | 1 | 81 | 5.82 | 5.15 | 1.13x |
| DeepSeek-V4-Flash-0731 | 2 | 81 | 11.10 | 7.65 | 1.45x |
| DeepSeek-V4-Flash-0731 | 4 | 81 | 20.26 | 10.76 | 1.88x |
| DeepSeek-V4-Flash-0731 | 8 | 81 | 34.25 | 15.06 | 2.27x |
| DeepSeek-V4-Flash-0731 | 16 | 81 | 51.33 | 19.93 | 2.58x |
| DeepSeek-V4-Flash-0731 | 32 | 81 | 66.07 | 24.80 | 2.66x |
| DeepSeek-V4-Flash-0731 | 64 | 81 | 74.24 | 28.72 | 2.58x |
| DeepSeek-V4-Flash-0731 | 256 | 81 | 77.61 | 31.33 | 2.48x |
| DeepSeek-V4-Flash-0731 | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 111 | 11.30 | 8.25 | 1.37x |
| DeepSeek-V4-Flash-0731 | 4 | 111 | 21.00 | 11.59 | 1.81x |
| DeepSeek-V4-Flash-0731 | 8 | 111 | 36.62 | 16.74 | 2.19x |
| DeepSeek-V4-Flash-0731 | 16 | 111 | 57.59 | 22.52 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 111 | 78.62 | 28.55 | 2.75x |
| DeepSeek-V4-Flash-0731 | 64 | 111 | 92.82 | 33.53 | 2.77x |
| DeepSeek-V4-Flash-0731 | 256 | 111 | 100.00 | 36.92 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1024 | 111 | 100.06 | 36.95 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 112 | 11.30 | 8.26 | 1.37x |
| DeepSeek-V4-Flash-0731 | 4 | 112 | 21.01 | 11.62 | 1.81x |
| DeepSeek-V4-Flash-0731 | 8 | 112 | 36.68 | 16.79 | 2.18x |
| DeepSeek-V4-Flash-0731 | 16 | 112 | 57.76 | 22.59 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 112 | 78.97 | 28.66 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 112 | 93.35 | 33.67 | 2.77x |
| DeepSeek-V4-Flash-0731 | 256 | 112 | 100.67 | 37.08 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1024 | 112 | 100.73 | 37.11 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1 | 140 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 2 | 140 | 11.41 | 8.68 | 1.31x |
| DeepSeek-V4-Flash-0731 | 4 | 140 | 21.42 | 12.23 | 1.75x |
| DeepSeek-V4-Flash-0731 | 8 | 140 | 38.05 | 17.96 | 2.12x |
| DeepSeek-V4-Flash-0731 | 16 | 140 | 61.57 | 24.40 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 140 | 87.24 | 31.40 | 2.78x |
| DeepSeek-V4-Flash-0731 | 64 | 140 | 106.59 | 37.29 | 2.86x |
| DeepSeek-V4-Flash-0731 | 256 | 140 | 117.56 | 41.33 | 2.84x |
| DeepSeek-V4-Flash-0731 | 1024 | 140 | 117.66 | 41.37 | 2.84x |
| DeepSeek-V4-Flash-0731 | 1 | 142 | 5.90 | 5.47 | 1.08x |
| DeepSeek-V4-Flash-0731 | 2 | 142 | 11.42 | 8.71 | 1.31x |
| DeepSeek-V4-Flash-0731 | 4 | 142 | 21.45 | 12.27 | 1.75x |
| DeepSeek-V4-Flash-0731 | 8 | 142 | 38.13 | 18.03 | 2.11x |
| DeepSeek-V4-Flash-0731 | 16 | 142 | 61.80 | 24.52 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 142 | 87.75 | 31.58 | 2.78x |
| DeepSeek-V4-Flash-0731 | 64 | 142 | 107.42 | 37.52 | 2.86x |
| DeepSeek-V4-Flash-0731 | 256 | 142 | 118.65 | 41.61 | 2.85x |
| DeepSeek-V4-Flash-0731 | 1024 | 142 | 118.74 | 41.65 | 2.85x |
| DeepSeek-V4-Flash-0731 | 1 | 150 | 5.90 | 5.49 | 1.07x |
| DeepSeek-V4-Flash-0731 | 2 | 150 | 11.44 | 8.81 | 1.30x |
| DeepSeek-V4-Flash-0731 | 4 | 150 | 21.54 | 12.43 | 1.73x |
| DeepSeek-V4-Flash-0731 | 8 | 150 | 38.42 | 18.31 | 2.10x |
| DeepSeek-V4-Flash-0731 | 16 | 150 | 62.65 | 24.96 | 2.51x |
| DeepSeek-V4-Flash-0731 | 32 | 150 | 89.66 | 32.28 | 2.78x |
| DeepSeek-V4-Flash-0731 | 64 | 150 | 110.61 | 38.44 | 2.88x |
| DeepSeek-V4-Flash-0731 | 256 | 150 | 122.83 | 42.69 | 2.88x |
| DeepSeek-V4-Flash-0731 | 1024 | 150 | 122.93 | 42.73 | 2.88x |
| DeepSeek-V4-Flash-0731 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 2 | 168 | 11.48 | 9.01 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 168 | 21.70 | 12.77 | 1.70x |
| DeepSeek-V4-Flash-0731 | 8 | 168 | 39.00 | 18.86 | 2.07x |
| DeepSeek-V4-Flash-0731 | 16 | 168 | 64.32 | 25.90 | 2.48x |
| DeepSeek-V4-Flash-0731 | 32 | 168 | 93.48 | 33.74 | 2.77x |
| DeepSeek-V4-Flash-0731 | 64 | 168 | 117.06 | 40.37 | 2.90x |
| DeepSeek-V4-Flash-0731 | 256 | 168 | 131.43 | 44.95 | 2.92x |
| DeepSeek-V4-Flash-0731 | 1024 | 168 | 131.56 | 45.00 | 2.92x |
| DeepSeek-V4-Flash-0731 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 224 | 11.58 | 9.50 | 1.22x |
| DeepSeek-V4-Flash-0731 | 4 | 224 | 22.06 | 13.68 | 1.61x |
| DeepSeek-V4-Flash-0731 | 8 | 224 | 40.23 | 20.13 | 2.00x |
| DeepSeek-V4-Flash-0731 | 16 | 224 | 67.98 | 28.43 | 2.39x |
| DeepSeek-V4-Flash-0731 | 32 | 224 | 102.19 | 37.57 | 2.72x |
| DeepSeek-V4-Flash-0731 | 64 | 224 | 132.41 | 45.34 | 2.92x |
| DeepSeek-V4-Flash-0731 | 256 | 224 | 152.56 | 50.95 | 2.99x |
| DeepSeek-V4-Flash-0731 | 1024 | 224 | 152.75 | 51.00 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 335 | 11.67 | 10.10 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 335 | 22.42 | 15.08 | 1.49x |
| DeepSeek-V4-Flash-0731 | 8 | 335 | 41.50 | 21.74 | 1.91x |
| DeepSeek-V4-Flash-0731 | 16 | 335 | 71.92 | 32.23 | 2.23x |
| DeepSeek-V4-Flash-0731 | 32 | 335 | 112.01 | 42.67 | 2.63x |
| DeepSeek-V4-Flash-0731 | 64 | 335 | 150.70 | 52.74 | 2.86x |
| DeepSeek-V4-Flash-0731 | 256 | 335 | 178.89 | 59.63 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 335 | 179.16 | 59.70 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 336 | 11.67 | 10.11 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 336 | 22.42 | 15.09 | 1.49x |
| DeepSeek-V4-Flash-0731 | 8 | 336 | 41.51 | 21.75 | 1.91x |
| DeepSeek-V4-Flash-0731 | 16 | 336 | 71.94 | 32.26 | 2.23x |
| DeepSeek-V4-Flash-0731 | 32 | 336 | 112.08 | 42.70 | 2.62x |
| DeepSeek-V4-Flash-0731 | 64 | 336 | 150.82 | 52.80 | 2.86x |
| DeepSeek-V4-Flash-0731 | 256 | 336 | 179.07 | 59.69 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 336 | 179.34 | 59.76 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 387 | 5.96 | 5.79 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 387 | 11.69 | 10.29 | 1.14x |
| DeepSeek-V4-Flash-0731 | 4 | 387 | 22.52 | 15.61 | 1.44x |
| DeepSeek-V4-Flash-0731 | 8 | 387 | 41.86 | 22.32 | 1.88x |
| DeepSeek-V4-Flash-0731 | 16 | 387 | 73.04 | 33.54 | 2.18x |
| DeepSeek-V4-Flash-0731 | 32 | 387 | 114.90 | 44.51 | 2.58x |
| DeepSeek-V4-Flash-0731 | 64 | 387 | 156.27 | 55.50 | 2.82x |
| DeepSeek-V4-Flash-0731 | 256 | 387 | 187.14 | 62.87 | 2.98x |
| DeepSeek-V4-Flash-0731 | 1024 | 387 | 187.45 | 62.94 | 2.98x |
| DeepSeek-V4-Flash-0731 | 1 | 395 | 5.96 | 5.80 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 395 | 11.70 | 10.32 | 1.13x |
| DeepSeek-V4-Flash-0731 | 4 | 395 | 22.53 | 15.68 | 1.44x |
| DeepSeek-V4-Flash-0731 | 8 | 395 | 41.90 | 22.40 | 1.87x |
| DeepSeek-V4-Flash-0731 | 16 | 395 | 73.19 | 33.72 | 2.17x |
| DeepSeek-V4-Flash-0731 | 32 | 395 | 115.29 | 44.78 | 2.57x |
| DeepSeek-V4-Flash-0731 | 64 | 395 | 157.02 | 55.89 | 2.81x |
| DeepSeek-V4-Flash-0731 | 256 | 395 | 188.26 | 63.34 | 2.97x |
| DeepSeek-V4-Flash-0731 | 1024 | 395 | 188.57 | 63.42 | 2.97x |
| DeepSeek-V4-Flash-0731 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 448 | 11.72 | 10.47 | 1.12x |
| DeepSeek-V4-Flash-0731 | 4 | 448 | 22.61 | 16.14 | 1.40x |
| DeepSeek-V4-Flash-0731 | 8 | 448 | 42.17 | 22.95 | 1.84x |
| DeepSeek-V4-Flash-0731 | 16 | 448 | 74.04 | 34.77 | 2.13x |
| DeepSeek-V4-Flash-0731 | 32 | 448 | 117.52 | 46.50 | 2.53x |
| DeepSeek-V4-Flash-0731 | 64 | 448 | 161.39 | 58.19 | 2.77x |
| DeepSeek-V4-Flash-0731 | 256 | 448 | 194.83 | 66.34 | 2.94x |
| DeepSeek-V4-Flash-0731 | 1024 | 448 | 195.17 | 66.42 | 2.94x |
| DeepSeek-V4-Flash-0731 | 4096 | 448 | 195.17 | 66.42 | 2.94x |
| DeepSeek-V4-Flash-0731 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 672 | 11.76 | 10.87 | 1.08x |
| DeepSeek-V4-Flash-0731 | 4 | 672 | 22.79 | 17.60 | 1.29x |
| DeepSeek-V4-Flash-0731 | 8 | 672 | 42.85 | 24.95 | 1.72x |
| DeepSeek-V4-Flash-0731 | 16 | 672 | 76.22 | 37.57 | 2.03x |
| DeepSeek-V4-Flash-0731 | 32 | 672 | 123.33 | 52.69 | 2.34x |
| DeepSeek-V4-Flash-0731 | 64 | 672 | 173.01 | 65.13 | 2.66x |
| DeepSeek-V4-Flash-0731 | 256 | 672 | 212.61 | 75.82 | 2.80x |
| DeepSeek-V4-Flash-0731 | 1024 | 672 | 213.01 | 75.93 | 2.81x |
| DeepSeek-V4-Flash-0731 | 4096 | 672 | 213.01 | 75.93 | 2.81x |
| DeepSeek-V4-Flash-0731 | 1 | 2574 | 5.99 | 5.98 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 2574 | 11.83 | 11.57 | 1.02x |
| DeepSeek-V4-Flash-0731 | 4 | 2574 | 23.07 | 21.16 | 1.09x |
| DeepSeek-V4-Flash-0731 | 8 | 2574 | 43.87 | 33.78 | 1.30x |
| DeepSeek-V4-Flash-0731 | 16 | 2574 | 79.60 | 47.00 | 1.69x |
| DeepSeek-V4-Flash-0731 | 32 | 2574 | 132.64 | 67.16 | 1.97x |
| DeepSeek-V4-Flash-0731 | 64 | 2574 | 192.36 | 91.97 | 2.09x |
| DeepSeek-V4-Flash-0731 | 256 | 2574 | 243.19 | 109.66 | 2.22x |
| DeepSeek-V4-Flash-0731 | 1024 | 2574 | 243.73 | 109.83 | 2.22x |
| DeepSeek-V4-Flash-0731 | 4096 | 2574 | 243.73 | 109.83 | 2.22x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 1.4% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 16.3% |

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
| DeepSeek-V4-Flash-0731 | 1 | 22 | 98.41% | 44.34 | 2.05 |
| DeepSeek-V4-Flash-0731 | 2 | 1 | 11.20% | 13.07 | 2.05 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 11.20% | 13.07 | 2.05 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 11.20% | 13.07 | 2.05 |

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
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 977.6 | 383,223.1 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 977.6 | 383,223.1 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 977.6 | 383,223.1 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 977.6 | 383,223.1 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 977.6 | 383,223.1 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 977.6 | 383,223.1 |
| DeepSeek-V4-Flash-0731 | 64 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 977.6 | 383,223.1 |
| DeepSeek-V4-Flash-0731 | 256 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 977.6 | 383,223.1 |
| DeepSeek-V4-Flash-0731 | 1024 | 6.01% | 16.6 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 413.4 | 423,274.0 |
| DeepSeek-V4-Flash-0731 | 4096 | 21.95% | 40.1 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 103.8 | 425,081.1 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 177 |
| gpu | kv_read | 22 |
| gpu | link_latency | 256 |
| gpu | weight_read | 745 |
| rom | compute | 78 |
| rom | infeasible | 2688 |
| rom | kv_read | 179 |
| rom | link_latency | 363 |
| rom | weight_read | 232 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 177 |
| rom | CAPACITY | 2688 |

## Mechanical consistency audit

**FAIL** over 65,969 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x48', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x50', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x61', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x76', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x78', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x114', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x142', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x144', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x152', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x48', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x50', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x61', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x76', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x78', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x114', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x142', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x144', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x152', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x48', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x50', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x61', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x76', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x78', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x114', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x142', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x144', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x152', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x48', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x50', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x61', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x76', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x78', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x114', 'DeepSeek-V4-Flash-0731', 1)

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

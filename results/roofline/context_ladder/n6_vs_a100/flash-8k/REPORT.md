# Area-constrained roofline: n6_vs_a100-flash-8k

> CONTEXT-LADDER RUNG of n6_vs_a100: DeepSeek-V4-Flash-0731 at 8,192 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; only the context differs, and the primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 147x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 68 devices. On the GPU side the correction reaches 54x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 104 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. DeepSeek-V4-Flash-0731 takes 44 x 815 mm2 (35,860 mm2, array, KV in SRAM) at 12,446 tok/s per user and 347 tok/s per 1,000 mm2, holding 1 session, against 43 copies of one unified HBM die at the same silicon: 12.8x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is DeepSeek-V4-Flash-0731 on 277,100 mm2 of ROM silicon at 15,528 tok/s per user against 276,710 mm2 of a100_sxm_80gb-x335-tensor at 800 tok/s: **19.4x**, ROM binding on `compute` and the GPU on `link_latency`. It holds 394,857 resident sessions against the GPU cluster's 386,359. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 7.62x to it.** At 185,005 mm2 on DeepSeek-V4-Flash-0731 the pipeline-only GPU delivers 144.36 tok/s and the same silicon running tensor delivers 1,099 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`) to 4.38x (DeepSeek-V4-Flash-0731, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 1,140 to 47,455 tok/s, and its rate with every slot occupied from 46,722 to 47,455. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 41 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,218 us over NVLink, capping per-user decode at 821 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 165.6 us and cap it at 6,040 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 5.2x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 2 of 10 operating points and an array 8; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 101 of 4162 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 160.2x of aggregate throughput (DeepSeek-V4-Flash-0731). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 21.47x, on DeepSeek-V4-Flash-0731 at batch 4096, where the busiest region carries 3.03x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 81% of its cooling budget. The companion study at the other node does have power-limited points.


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

### DeepSeek-V4-Flash-0731 at 8,192 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x44`** -- 44 x 815 mm2 reticle dies, 35,860 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **12,446.0 tok/s per user** (0.08 ms/token), binding on `link_latency`
- **347.1 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 12,446 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 2,385 W at 0.066 W/mm2, 191.6 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 43 copies of one unified HBM die -- `a100_sxm_80gb-x43-tensor`, 35,518 mm2, area ratio 1.0096 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 35,860 | 35,518 | 1.0096 |
| user tok/s | 12,446.0 | 974.2 | 12.78x |
| aggregate tok/s | 12,446 | 974 | 2.01x |
| resident sessions | 1 | 47,246 | -- |
| J/token | 0.1916 | 7.5574 | 39.4x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 47,246 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x224-tensor` at 185,024 mm2 and 1,099.3 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 16,019.5 | 289.1 | 78,971 | 15.61x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 16,019.5 | 289.1 | 78,971 | 15.61x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x38` | 30,970 | 10,731.2 | 346.5 | 1 | 11.26x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | 35,860 | 12,446.0 | 347.1 | 1 | 12.78x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | 35,860 | 12,446.0 | 347.1 | -- | 347.1 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x45` | 36,675 | 12,561.2 | 342.5 | 141.4 | 347.1 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x47` | 38,305 | 12,743.8 | 332.7 | 121.8 | 347.1 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x50` | 40,750 | 12,935.0 | 317.4 | 100.0 | 347.1 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x51` | 41,565 | 12,957.4 | 311.7 | 89.6 | 347.1 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 16,019.5 | 289.1 | 182.7 | 347.1 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x44` **<-- recommended** | 35,860 | 44 | 12,446.0 | 12,446 | 347.1 | 1 | `link_latency` | 2,385 | 191.6 | `a100_sxm_80gb-x43-tensor` | 12.78x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x45` | 36,675 | 45 | 12,561.2 | 12,561 | 342.5 | 1 | `link_latency` | 2,503 | 199.3 | `a100_sxm_80gb-x44-tensor` | 12.85x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x47` | 38,305 | 47 | 12,743.8 | 12,744 | 332.7 | 1 | `link_latency` | 2,741 | 215.1 | `a100_sxm_80gb-x46-tensor` | 12.95x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x50` | 40,750 | 50 | 12,935.0 | 12,935 | 317.4 | 1 | `link_latency` | 3,096 | 239.4 | `a100_sxm_80gb-x49-tensor` | 13.05x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x51` | 41,565 | 51 | 12,957.4 | 12,957 | 311.7 | 1 | `link_latency` | 3,214 | 248.1 | `a100_sxm_80gb-x50-tensor` | 13.04x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 68 | 16,019.5 | 272,332 | 289.1 | 78,971 | `compute` | 8,227 | 389.5 | `a100_sxm_80gb-x67-tensor` | 15.61x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 342 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | 35,860 | 12,446.0 | 347.1 | 1 |
| array | 342 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 16,019.5 | 289.1 | 78,971 |
| array | 342 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x38` | 30,970 | 10,731.2 | 346.5 | 1 |
| wafer | 80 | densest | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | 5,520.1 | 119.4 | 9,987 |
| wafer | 80 | fastest | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,523.4 | 59.7 | 19,975 |
| wafer | 80 | smallest | `ROM-N6-native-HBMKV-wafer-tensor-x1` | 46,225 | 5,520.1 | 119.4 | 9,987 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 16,019.5 | 272,332 | 78,971 | 8,227 | 389.5 | `compute` | `a100_sxm_80gb-x67-tensor` | 1,026.2 | 75,118 | 10,611.2 | 1.001 | 15.61x | 27.2x |
| 1 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,523.4 | 11,047 | 19,975 | 8,682 | 1,564.1 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 1,067.2 | 127,378 | 16,336.7 | 0.999 | 5.18x | 10.4x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill` | 90,465 | 15,812.2 | 442,743 | 128,909 | 13,479 | 643.2 | `compute` | `a100_sxm_80gb-x110-tensor` | 1,066.0 | 125,056 | 16,083.7 | 0.996 | 14.83x | 25.0x |
| 1 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,523.4 | -- | 19,975 | -- | 1,564.1 | -- | -- | -- | -- | -- | 0.979 | 0.35x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 16,019.5 | 272,332 | 78,971 | 8,227 | 198.6 | `compute` | `a100_sxm_80gb-x67-tensor` | 920.4 | 75,118 | 6,027.0 | 1.001 | 17.41x | 30.3x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,523.4 | 11,047 | 19,975 | 8,682 | 785.9 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 961.5 | 127,378 | 9,181.0 | 0.999 | 5.74x | 11.7x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x111-romfill` | 90,465 | 15,812.2 | 442,743 | 128,909 | 13,479 | 325.5 | `compute` | `a100_sxm_80gb-x110-tensor` | 960.2 | 125,056 | 9,042.3 | 0.996 | 16.47x | 27.8x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,523.4 | -- | 19,975 | -- | 785.9 | -- | -- | -- | -- | -- | 0.979 | 0.35x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 16,019.5 | 272,332 | 78,971 | 8,227 | 103.2 | `compute` | `a100_sxm_80gb-x67-tensor` | 764.3 | 75,118 | 3,723.5 | 1.001 | 20.96x | 36.1x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 5,517.2 | 22,069 | 39,950 | 17,364 | 786.8 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 833.6 | 257,449 | 10,258.7 | 0.999 | 6.62x | 13.0x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 15,479.7 | 882,340 | 263,625 | 27,386 | 339.6 | `compute` | `a100_sxm_80gb-x224-tensor` | 833.6 | 257,449 | 10,258.7 | 1.000 | 18.57x | 30.2x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 184,900 | 5,517.2 | -- | 39,950 | -- | 786.8 | -- | -- | -- | -- | -- | 1.001 | 0.36x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 16,019.5 | 272,332 | 78,971 | 8,227 | 55.5 | `compute` | `a100_sxm_80gb-x67-hybrid` | 723.5 | 75,118 | 2,855.4 | 1.001 | 22.14x | 46.0x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 5,504.9 | 44,039 | 79,900 | 34,727 | 788.5 | `link_latency` | `a100_sxm_80gb-x448-hybrid` | 714.9 | 517,591 | 12,493.9 | 0.999 | 7.70x | 15.8x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 16,019.5 | 272,332 | 78,971 | 8,227 | 31.6 | `compute` | `a100_sxm_80gb-x67-hybrid` | 623.3 | 75,118 | 1,793.7 | 1.001 | 25.70x | 56.7x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,462.5 | 87,400 | 119,850 | 52,202 | 597.3 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 714.9 | 777,732 | 9,666.5 | 0.999 | 7.64x | 16.2x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 120,620 | 15,680.6 | 580,181 | 171,879 | 17,893 | 34.4 | `compute` | `a100_sxm_80gb-x146-hybrid` | 637.2 | 166,864 | 1,883.3 | 1.000 | 24.61x | 54.7x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 5,345.0 | 171,040 | 119,850 | 52,643 | 307.8 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 714.9 | 777,732 | 5,425.3 | 0.999 | 7.48x | 17.6x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 15,527.8 | 1,319,866 | 394,857 | 41,006 | 38.7 | `compute` | `a100_sxm_80gb-x335-hybrid` | 647.2 | 386,359 | 2,068.9 | 1.001 | 23.99x | 53.4x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 5,317.6 | 3,621,263 | 119,850 | 79,646 | 159.3 | `compute` | `a100_sxm_80gb-x672-hybrid` | 714.9 | 777,732 | 3,304.7 | 0.999 | 7.44x | 20.7x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,364.6 | 1,629,348 | 394,857 | 40,743 | 25.0 | `compute` | `a100_sxm_80gb-x335-hybrid` | 363.4 | 386,359 | 1,000.6 | 1.001 | 17.51x | 24.4x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 5,317.6 | 3,621,263 | 119,850 | 79,646 | 45.6 | `compute` | `a100_sxm_80gb-x672-hybrid` | 510.3 | 777,732 | 1,369.7 | 0.999 | 10.42x | 22.0x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 1,778.8 | 1,821,444 | 394,857 | 41,918 | 23.0 | `compute` | `a100_sxm_80gb-x335-expert` | 293.3 | 381,346 | 182.0 | 1.001 | 6.07x | 7.9x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 3,651.1 | 3,738,754 | 119,850 | 77,517 | 20.7 | `compute` | `a100_sxm_80gb-x672-expert` | 365.2 | 767,332 | 280.4 | 0.999 | 10.00x | 13.5x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 185,005 | 532.3 | 2,180,451 | 263,625 | 37,655 | 17.3 | `compute` | `a100_sxm_80gb-x224-expert` | 121.5 | 254,066 | 74.0 | 1.000 | 4.38x | 4.3x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,134.4 | 4,646,452 | 119,850 | 99,514 | 21.4 | `kv_read` | `a100_sxm_80gb-x672-expert` | 262.0 | 767,332 | 99.5 | 0.999 | 4.33x | 4.6x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | 35,860 | array | SRAM | 1 |
| 2-16 | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | array | HBM | 78,971 |
| 32-64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x74` | 60,310 | array | HBM | 85,939 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x113` | 92,095 | array | HBM | 131,232 |
| 1024 | `ROM-N6-native-HBMKV-array-hw-hybrid-x148` | 120,620 | array | HBM | 171,879 |
| 4096 | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 185,005 | array | HBM | 263,625 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash-0731 | HBM | rom | 41, 47, 53, 56, 57, 68, 74, 111, 113, 148, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | HBM | sram | 41, 47, 53, 56, 57, 68, 69, 74, 111, 113, 148, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | rom | 38, 44, 45, 47, 50, 51, 53, 57, 70, 105, 113, 140, 170, 227, 340 |
| DeepSeek-V4-Flash-0731 | SRAM | sram | 38, 44, 45, 47, 50, 51, 53, 57, 70, 105, 113, 140, 170, 227, 340 |

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

- **0 of 4,162 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 81% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 360 | 0 | 58.2% | 80.5% | 0.390 | 62% |
| gpu | small array (1,600-5,000 mm2) | 30 | 0 | 72.6% | 80.4% | 0.389 | 50% |
| gpu | wafer (>=40,000 mm2) | 840 | 0 | 62.6% | 79.8% | 0.387 | 71% |
| rom | large array (5,000-40,000 mm2) | 864 | 0 | 19.3% | 52.6% | 0.263 | 89% |
| rom | wafer (>=40,000 mm2) | 2,068 | 0 | 25.7% | 40.7% | 0.204 | 91% |

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
| DeepSeek-V4-Flash-0731 | 1 | 55,420 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 0.389529 | 8,226.7 | compute | `DSV4-Flash/a100_sxm_80gb-x67-tensor` | 10.611203 | 10,888.9 | link_latency | 27.24x |
| DeepSeek-V4-Flash-0731 | 2 | 55,420 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 0.198640 | 8,226.7 | compute | `DSV4-Flash/a100_sxm_80gb-x67-tensor` | 6.026966 | 11,094.1 | link_latency | 30.34x |
| DeepSeek-V4-Flash-0731 | 4 | 55,420 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 0.103195 | 8,226.7 | compute | `DSV4-Flash/a100_sxm_80gb-x67-tensor` | 3.723537 | 11,383.3 | link_latency | 36.08x |
| DeepSeek-V4-Flash-0731 | 8 | 55,420 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 0.055473 | 8,226.7 | compute | `DSV4-Flash/a100_sxm_80gb-x67-hybrid` | 2.855446 | 17,384.5 | weight_read | 45.98x |
| DeepSeek-V4-Flash-0731 | 16 | 55,420 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 0.031612 | 8,226.7 | compute | `DSV4-Flash/a100_sxm_80gb-x67-hybrid` | 1.793668 | 17,887.0 | weight_read | 56.74x |
| DeepSeek-V4-Flash-0731 | 32 | 120,620 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill` | 0.034449 | 17,893.3 | compute | `DSV4-Flash/a100_sxm_80gb-x146-hybrid` | 1.883277 | 38,403.2 | weight_read | 54.67x |
| DeepSeek-V4-Flash-0731 | 64 | 277,100 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.038719 | 41,005.7 | compute | `DSV4-Flash/a100_sxm_80gb-x335-hybrid` | 2.068936 | 85,699.5 | weight_read | 53.43x |
| DeepSeek-V4-Flash-0731 | 256 | 277,100 | `DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.025006 | 40,742.7 | compute | `DSV4-Flash/a100_sxm_80gb-x335-hybrid` | 1.000553 | 93,079.1 | weight_read | 24.39x |
| DeepSeek-V4-Flash-0731 | 1024 | 554,700 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 0.020733 | 77,516.7 | compute | `DSV4-Flash/a100_sxm_80gb-x672-expert` | 0.280405 | 104,868.7 | weight_read | 13.52x |
| DeepSeek-V4-Flash-0731 | 4096 | 554,700 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 0.021417 | 99,513.8 | kv_read | `DSV4-Flash/a100_sxm_80gb-x672-expert` | 0.099453 | 106,729.8 | link_latency | 4.64x |

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
| DeepSeek-V4-Flash-0731 | 8,192 | 284 B | 166.9 GB | 4.70 | 0.029 GB | 0.062 GB | 387.3 |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 47,945.0 | wafer-pipeline | 5,520.1 | wafer-tensor | 8.69x | 4,179.0 | pipeline | 1,008.3 | tensor | 4.14x | 11.47x | 5.47x | 0.48x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 52,235.0 | wafer-pipeline | 5,523.4 | wafer-hybrid | 9.46x | 5,602.5 | pipeline | 1,067.2 | tensor | 5.25x | 9.32x | 5.18x | 0.56x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 53,637.2 | wafer-pipeline | 5,520.3 | wafer-hybrid | 9.72x | 6,320.1 | pipeline | 1,088.4 | tensor | 5.81x | 8.49x | 5.07x | 0.60x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 54,366.9 | wafer-pipeline | 5,517.2 | wafer-hybrid | 9.85x | 6,752.6 | pipeline | 1,099.3 | tensor | 6.14x | 8.05x | 5.02x | 0.62x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 55,116.7 | wafer-pipeline | 5,511.1 | wafer-hybrid | 10.00x | 7,248.6 | pipeline | 800.2 | tensor | 9.06x | 7.60x | 6.89x | 0.91x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 55,499.5 | wafer-pipeline | 5,504.9 | wafer-hybrid | 10.08x | 7,524.9 | pipeline | 803.1 | tensor | 9.37x | 7.38x | 6.85x | 0.93x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 55,887.6 | wafer-pipeline | 5,492.7 | wafer-hybrid | 10.17x | 7,823.2 | pipeline | 806.1 | tensor | 9.71x | 7.14x | 6.81x | 0.95x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.48x to 0.95x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 16,019.5 | 272,332.2 | compute | DSV4-Flash/a100_sxm_80gb-x67-tensor | 55,342 | 1.00x | tensor | 860.47 | 1,026.2 | 1,026.2 | link_latency | 15.61x | 28.16x | 110.97x | 15.61x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x38 | 30,970 | 10,731.2 | 10,731.2 | link_latency | DSV4-Flash/a100_sxm_80gb-x37-tensor | 30,562 | 1.01x | tensor | 852.96 | 952.9 | 952.9 | link_latency | 11.26x | 2.00x | 74.18x | 11.26x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 16,019.5 | 272,332.2 | compute | DSV4-Flash/a100_sxm_80gb-x67-tensor | 55,342 | 1.00x | tensor | 941.78 | 920.4 | 1,840.7 | link_latency | 17.41x | 28.16x | 110.97x | 17.41x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x41 | 33,415 | 8,625.6 | 17,251.2 | link_latency | DSV4-Flash/a100_sxm_80gb-x40-tensor | 33,040 | 1.01x | tensor | 926.76 | 861.5 | 1,722.9 | link_latency | 10.01x | 2.98x | 59.69x | 10.01x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 16,019.5 | 272,332.2 | compute | DSV4-Flash/a100_sxm_80gb-x67-tensor | 55,342 | 1.00x | tensor | 1,104.41 | 764.3 | 3,057.1 | link_latency | 20.96x | 28.16x | 110.97x | 20.96x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x41 | 33,415 | 6,211.4 | 24,845.6 | compute | DSV4-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 445.60 | 763.8 | 3,819.2 | weight_read | 8.13x | 4.30x | 42.98x | 8.13x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 16,019.5 | 272,332.2 | compute | DSV4-Flash/a100_sxm_80gb-x67-hybrid | 55,342 | 1.00x | hybrid | 455.03 | 723.5 | 6,511.7 | weight_read | 22.14x | 28.16x | 110.97x | 22.14x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x41 | 33,415 | 4,043.9 | 44,482.5 | compute | DSV4-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 450.08 | 680.9 | 5,447.1 | weight_read | 5.94x | 7.70x | 27.98x | 5.94x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 16,019.5 | 272,332.2 | compute | DSV4-Flash/a100_sxm_80gb-x67-hybrid | 55,342 | 1.00x | hybrid | 461.86 | 623.3 | 9,972.3 | weight_read | 25.70x | 27.31x | 110.97x | 25.70x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x41 | 33,415 | 2,834.3 | 45,348.5 | compute | DSV4-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 462.04 | 530.9 | 8,495.0 | weight_read | 5.34x | 5.34x | 19.61x | 5.34x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill | 120,620 | 15,680.6 | 580,181.2 | compute | DSV4-Flash/a100_sxm_80gb-x146-hybrid | 120,596 | 1.00x | hybrid | 486.86 | 637.2 | 20,391.7 | weight_read | 24.61x | 27.53x | 108.62x | 24.61x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x41 | 33,415 | 1,448.2 | 46,341.0 | compute | DSV4-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 485.96 | 374.7 | 11,989.7 | weight_read | 3.87x | 3.87x | 10.02x | 3.87x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 15,527.8 | 1,319,865.7 | compute | DSV4-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 543.10 | 647.2 | 41,422.0 | weight_read | 23.99x | 27.29x | 107.57x | 23.99x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x41 | 33,415 | 734.1 | 46,985.2 | compute | DSV4-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 533.80 | 245.2 | 15,691.8 | weight_read | 2.99x | 2.99x | 5.99x | 2.99x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,364.6 | 1,629,348.1 | compute | DSV4-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 632.69 | 363.4 | 93,027.7 | weight_read | 17.51x | 17.51x | 44.09x | 17.51x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x41 | 33,415 | 184.9 | 47,342.2 | compute | DSV4-Flash/a100_sxm_80gb-x40-expert | 33,040 | 1.01x | expert | 2,002.33 | 142.8 | 36,551.3 | weight_read | 1.30x | 1.30x | 3.23x | 1.30x |
| DeepSeek-V4-Flash-0731 | 1024 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3,651.1 | 3,738,753.6 | compute | DSV4-Flash/a100_sxm_80gb-x672-expert | 555,072 | 1.00x | expert | 937.38 | 365.2 | 373,990.6 | weight_read | 10.00x | 10.00x | 29.25x | 10.00x |
| DeepSeek-V4-Flash-0731 | 1024 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x41 | 33,415 | 46.3 | 47,432.3 | compute | DSV4-Flash/a100_sxm_80gb-x40-expert | 33,040 | 1.01x | expert | 6,195.59 | 86.6 | 88,721.1 | link_latency | 0.53x | 0.53x | 2.12x | 0.53x |
| DeepSeek-V4-Flash-0731 | 4096 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,134.4 | 4,646,451.6 | kv_read | DSV4-Flash/a100_sxm_80gb-x672-expert | 555,072 | 1.00x | expert | 1,935.77 | 262.0 | 1,073,164.6 | link_latency | 4.33x | 4.33x | 19.21x | 4.33x |
| DeepSeek-V4-Flash-0731 | 4096 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x41 | 33,415 | 11.6 | 47,454.8 | compute | DSV4-Flash/a100_sxm_80gb-x40-hybrid | 33,040 | 1.01x | hybrid | 6,561.80 | 37.3 | 152,641.7 | compute | 0.31x | 0.31x | 1.02x | 0.31x |

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
| DeepSeek-V4-Flash-0731 | 6 | 4,956 | 146.3 | 631.6 | — | tensor | 435.87 | 27.5% | weight_read |
| DeepSeek-V4-Flash-0731 | 18 | 14,868 | 145.7 | 811.4 | 629.6 | tensor | 841.69 | 68.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 20 | 16,520 | 145.6 | 837.1 | 678.1 | tensor | 841.69 | 70.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 22 | 18,172 | 145.5 | 859.4 | 723.7 | tensor | 841.69 | 72.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 34 | 28,084 | 144.8 | 938.4 | 685.2 | tensor | 852.96 | 80.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 37 | 30,562 | 144.7 | 952.9 | 725.6 | tensor | 852.96 | 81.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 40 | 33,040 | 144.5 | 965.6 | 763.8 | tensor | 852.96 | 82.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 43 | 35,518 | 144.4 | 974.2 | 709.0 | tensor | 855.78 | 83.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 44 | 36,344 | 144.4 | 977.6 | 720.0 | tensor | 855.78 | 83.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 46 | 37,996 | 144.4 | 984.1 | 741.5 | tensor | 855.78 | 84.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 49 | 40,474 | 144.4 | 990.9 | 696.6 | tensor | 857.79 | 85.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 50 | 41,300 | 144.4 | 993.7 | 706.2 | tensor | 857.79 | 85.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 52 | 42,952 | 144.4 | 998.9 | 725.0 | tensor | 857.79 | 85.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 55 | 45,430 | 144.4 | 1,006.0 | 752.2 | tensor | 857.79 | 86.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 56 | 46,256 | 144.4 | 1,008.3 | 761.1 | tensor | 857.79 | 86.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 67 | 55,342 | 144.4 | 1,026.2 | 723.5 | tensor | 860.47 | 88.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 68 | 56,168 | 144.4 | 1,027.7 | 730.6 | tensor | 860.47 | 88.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 69 | 56,994 | 144.4 | 1,029.3 | 737.7 | tensor | 860.47 | 88.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 73 | 60,298 | 144.4 | 1,034.0 | 713.0 | tensor | 861.41 | 89.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 104 | 85,904 | 144.4 | 1,062.4 | 753.0 | tensor | 863.36 | 91.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 110 | 90,860 | 144.4 | 1,066.0 | 743.0 | tensor | 863.83 | 92.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 111 | 91,686 | 144.4 | 1,066.6 | 747.3 | tensor | 863.83 | 92.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 112 | 92,512 | 144.4 | 1,067.2 | 751.7 | tensor | 863.83 | 92.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 138 | 113,988 | 144.4 | 1,078.9 | 726.3 | tensor | 865.17 | 93.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 146 | 120,596 | 144.4 | 1,081.7 | 726.1 | tensor | 865.42 | 93.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 168 | 138,768 | 144.4 | 1,088.4 | 742.4 | tensor | 865.84 | 94.2% | link_latency |
| DeepSeek-V4-Flash-0731 | 224 | 185,024 | 144.4 | 1,099.3 | 733.5 | tensor | 866.85 | 95.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 335 | 276,710 | 144.4 | 800.2 | 714.8 | tensor | 1,217.01 | 97.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 336 | 277,536 | 144.4 | 800.2 | 716.1 | tensor | 1,217.01 | 97.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 448 | 370,048 | 144.4 | 803.1 | 714.9 | tensor | 1,217.52 | 97.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 672 | 555,072 | 144.4 | 806.1 | 714.9 | tensor | 1,218.02 | 98.2% | link_latency |

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
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x50 | DeepSeek-V4-Flash-0731 | 50 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x47 | DeepSeek-V4-Flash-0731 | 47 | tensor | rom_package_ucie | rom_board_serdes | 172 | 59.95 us | 1,668.0 tok/s | 16,679.8 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 12 on rom_board_serdes (traversals 6.6) = 57.84 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x51 | DeepSeek-V4-Flash-0731 | 51 | hybrid | rom_package_ucie | rom_board_serdes | 98 | 3.37 us | 29,665.7 tok/s | 296,656.6 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 12 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.25 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x50 | DeepSeek-V4-Flash-0731 | 50 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-tensor-x38 | DeepSeek-V4-Flash-0731 | 38 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x45 | DeepSeek-V4-Flash-0731 | 45 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x69 | DeepSeek-V4-Flash-0731 | 69 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x56 | DeepSeek-V4-Flash-0731 | 56 | tensor | rom_package_ucie | rom_board_serdes | 172 | 59.97 us | 1,667.6 tok/s | 16,675.9 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 86 x all_reduce span 14 on rom_board_serdes (traversals 6.6) = 57.85 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | DeepSeek-V4-Flash-0731 | 68 | hybrid | rom_package_ucie | rom_board_serdes | 102 | 3.79 us | 26,391.5 tok/s | 263,914.5 tok/s | 86 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.12 us; 16 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.67 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x68 | DeepSeek-V4-Flash-0731 | 68 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | rom_wafer_serdes | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-tensor-x41 | DeepSeek-V4-Flash-0731 | 41 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | rom_wafer_serdes | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x53 | DeepSeek-V4-Flash-0731 | 53 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x6-pipeline | DeepSeek-V4-Flash-0731 | 6 | pipeline | nvlink3 | infiniband_hdr | 5 | 12.64 us | 7,913.6 tok/s | 79,135.6 tok/s | 5 x point_to_point span 2 on nvlink3 (traversals 1.0) = 12.64 us |
| DSV4-Flash/a100_sxm_80gb-x6-tensor | DeepSeek-V4-Flash-0731 | 6 | tensor | nvlink3 | infiniband_hdr | 86 | 435.87 us | 229.4 tok/s | 2,294.3 tok/s | 86 x all_reduce span 6 on nvlink3 (traversals 2.0) = 435.87 us |
| DSV4-Flash/a100_sxm_80gb-x6-expert | DeepSeek-V4-Flash-0731 | 6 | expert | nvlink3 | infiniband_hdr | 172 | 653.22 us | 153.1 tok/s | 1,530.9 tok/s | 86 x all_reduce span 6 on nvlink3 (traversals 2.0) = 435.87 us; 86 x point_to_point span 2 on nvlink3 (traversals 1.0) = 217.35 us |
| DSV4-Flash/a100_sxm_80gb-x18-pipeline | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink3 | infiniband_hdr | 17 | 42.62 us | 2,346.0 tok/s | 23,460.4 tok/s | 15 x point_to_point span 2 on nvlink3 (traversals 1.0) = 37.91 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x18-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x18-hybrid | DeepSeek-V4-Flash-0731 | 18 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x18-expert | DeepSeek-V4-Flash-0731 | 18 | expert | nvlink3 | infiniband_hdr | 172 | 617.06 us | 162.1 tok/s | 1,620.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 183.97 us |
| DSV4-Flash/a100_sxm_80gb-x20-pipeline | DeepSeek-V4-Flash-0731 | 20 | pipeline | nvlink3 | infiniband_hdr | 19 | 47.68 us | 2,097.3 tok/s | 20,973.3 tok/s | 17 x point_to_point span 2 on nvlink3 (traversals 1.0) = 42.96 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x20-tensor | DeepSeek-V4-Flash-0731 | 20 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x20-hybrid | DeepSeek-V4-Flash-0731 | 20 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x20-expert | DeepSeek-V4-Flash-0731 | 20 | expert | nvlink3 | infiniband_hdr | 172 | 616.12 us | 162.3 tok/s | 1,623.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 183.03 us |
| DSV4-Flash/a100_sxm_80gb-x22-pipeline | DeepSeek-V4-Flash-0731 | 22 | pipeline | nvlink3 | infiniband_hdr | 21 | 52.73 us | 1,896.3 tok/s | 18,963.0 tok/s | 19 x point_to_point span 2 on nvlink3 (traversals 1.0) = 48.02 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x22-tensor | DeepSeek-V4-Flash-0731 | 22 | tensor | nvlink3 | infiniband_hdr | 172 | 841.69 us | 118.8 tok/s | 1,188.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 405.52 us |
| DSV4-Flash/a100_sxm_80gb-x22-hybrid | DeepSeek-V4-Flash-0731 | 22 | hybrid | nvlink3 | infiniband_hdr | 88 | 440.88 us | 226.8 tok/s | 2,268.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| DSV4-Flash/a100_sxm_80gb-x22-expert | DeepSeek-V4-Flash-0731 | 22 | expert | nvlink3 | infiniband_hdr | 172 | 615.35 us | 162.5 tok/s | 1,625.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 433.08 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 182.27 us |
| DSV4-Flash/a100_sxm_80gb-x34-pipeline | DeepSeek-V4-Flash-0731 | 34 | pipeline | nvlink3 | infiniband_hdr | 33 | 82.72 us | 1,208.9 tok/s | 12,088.6 tok/s | 29 x point_to_point span 2 on nvlink3 (traversals 1.0) = 73.29 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x34-tensor | DeepSeek-V4-Flash-0731 | 34 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x34-hybrid | DeepSeek-V4-Flash-0731 | 34 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x34-expert | DeepSeek-V4-Flash-0731 | 34 | expert | nvlink3 | infiniband_hdr | 172 | 611.09 us | 163.6 tok/s | 1,636.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 179.55 us |
| DSV4-Flash/a100_sxm_80gb-x37-pipeline | DeepSeek-V4-Flash-0731 | 37 | pipeline | nvlink3 | infiniband_hdr | 36 | 90.30 us | 1,107.4 tok/s | 11,073.6 tok/s | 32 x point_to_point span 2 on nvlink3 (traversals 1.0) = 80.87 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-tensor | DeepSeek-V4-Flash-0731 | 37 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x37-hybrid | DeepSeek-V4-Flash-0731 | 37 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x37-expert | DeepSeek-V4-Flash-0731 | 37 | expert | nvlink3 | infiniband_hdr | 172 | 610.69 us | 163.7 tok/s | 1,637.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.54 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 179.15 us |
| DSV4-Flash/a100_sxm_80gb-x40-pipeline | DeepSeek-V4-Flash-0731 | 40 | pipeline | nvlink3 | infiniband_hdr | 39 | 97.89 us | 1,021.6 tok/s | 10,215.9 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.46 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x40-tensor | DeepSeek-V4-Flash-0731 | 40 | tensor | nvlink3 | infiniband_hdr | 172 | 852.96 us | 117.2 tok/s | 1,172.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 416.79 us |
| DSV4-Flash/a100_sxm_80gb-x40-hybrid | DeepSeek-V4-Flash-0731 | 40 | hybrid | nvlink3 | infiniband_hdr | 90 | 445.60 us | 224.4 tok/s | 2,244.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| DSV4-Flash/a100_sxm_80gb-x40-expert | DeepSeek-V4-Flash-0731 | 40 | expert | nvlink3 | infiniband_hdr | 172 | 610.04 us | 163.9 tok/s | 1,639.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.81 us |
| DSV4-Flash/a100_sxm_80gb-x43-pipeline | DeepSeek-V4-Flash-0731 | 43 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x43-tensor | DeepSeek-V4-Flash-0731 | 43 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x43-hybrid | DeepSeek-V4-Flash-0731 | 43 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x43-expert | DeepSeek-V4-Flash-0731 | 43 | expert | nvlink3 | infiniband_hdr | 172 | 609.75 us | 164.0 tok/s | 1,640.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.51 us |
| DSV4-Flash/a100_sxm_80gb-x44-pipeline | DeepSeek-V4-Flash-0731 | 44 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x44-tensor | DeepSeek-V4-Flash-0731 | 44 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x44-hybrid | DeepSeek-V4-Flash-0731 | 44 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x44-expert | DeepSeek-V4-Flash-0731 | 44 | expert | nvlink3 | infiniband_hdr | 172 | 609.66 us | 164.0 tok/s | 1,640.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.42 us |
| DSV4-Flash/a100_sxm_80gb-x46-pipeline | DeepSeek-V4-Flash-0731 | 46 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x46-tensor | DeepSeek-V4-Flash-0731 | 46 | tensor | nvlink3 | infiniband_hdr | 172 | 855.78 us | 116.9 tok/s | 1,168.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 419.61 us |
| DSV4-Flash/a100_sxm_80gb-x46-hybrid | DeepSeek-V4-Flash-0731 | 46 | hybrid | nvlink3 | infiniband_hdr | 91 | 447.95 us | 223.2 tok/s | 2,232.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x46-expert | DeepSeek-V4-Flash-0731 | 46 | expert | nvlink3 | infiniband_hdr | 172 | 609.49 us | 164.1 tok/s | 1,640.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.23 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.26 us |
| DSV4-Flash/a100_sxm_80gb-x49-pipeline | DeepSeek-V4-Flash-0731 | 49 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x49-tensor | DeepSeek-V4-Flash-0731 | 49 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x49-hybrid | DeepSeek-V4-Flash-0731 | 49 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x49-expert | DeepSeek-V4-Flash-0731 | 49 | expert | nvlink3 | infiniband_hdr | 172 | 609.06 us | 164.2 tok/s | 1,641.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 178.03 us |
| DSV4-Flash/a100_sxm_80gb-x50-pipeline | DeepSeek-V4-Flash-0731 | 50 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x50-tensor | DeepSeek-V4-Flash-0731 | 50 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x50-hybrid | DeepSeek-V4-Flash-0731 | 50 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x50-expert | DeepSeek-V4-Flash-0731 | 50 | expert | nvlink3 | infiniband_hdr | 172 | 608.99 us | 164.2 tok/s | 1,642.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.96 us |
| DSV4-Flash/a100_sxm_80gb-x52-pipeline | DeepSeek-V4-Flash-0731 | 52 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x52-tensor | DeepSeek-V4-Flash-0731 | 52 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x52-hybrid | DeepSeek-V4-Flash-0731 | 52 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x52-expert | DeepSeek-V4-Flash-0731 | 52 | expert | nvlink3 | infiniband_hdr | 172 | 608.86 us | 164.2 tok/s | 1,642.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.83 us |
| DSV4-Flash/a100_sxm_80gb-x55-pipeline | DeepSeek-V4-Flash-0731 | 55 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x55-tensor | DeepSeek-V4-Flash-0731 | 55 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x55-hybrid | DeepSeek-V4-Flash-0731 | 55 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x55-expert | DeepSeek-V4-Flash-0731 | 55 | expert | nvlink3 | infiniband_hdr | 172 | 608.68 us | 164.3 tok/s | 1,642.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 431.03 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.65 us |
| DSV4-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Flash-0731 | 56 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Flash-0731 | 56 | tensor | nvlink3 | infiniband_hdr | 172 | 857.79 us | 116.6 tok/s | 1,165.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 421.62 us |
| DSV4-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Flash-0731 | 56 | hybrid | nvlink3 | infiniband_hdr | 92 | 450.31 us | 222.1 tok/s | 2,220.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| DSV4-Flash/a100_sxm_80gb-x56-expert | DeepSeek-V4-Flash-0731 | 56 | expert | nvlink3 | infiniband_hdr | 172 | 608.48 us | 164.3 tok/s | 1,643.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.88 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.60 us |
| DSV4-Flash/a100_sxm_80gb-x67-pipeline | DeepSeek-V4-Flash-0731 | 67 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x67-tensor | DeepSeek-V4-Flash-0731 | 67 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x67-hybrid | DeepSeek-V4-Flash-0731 | 67 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x67-expert | DeepSeek-V4-Flash-0731 | 67 | expert | nvlink3 | infiniband_hdr | 172 | 607.87 us | 164.5 tok/s | 1,645.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.77 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.10 us |
| DSV4-Flash/a100_sxm_80gb-x68-pipeline | DeepSeek-V4-Flash-0731 | 68 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x68-tensor | DeepSeek-V4-Flash-0731 | 68 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x68-hybrid | DeepSeek-V4-Flash-0731 | 68 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x68-expert | DeepSeek-V4-Flash-0731 | 68 | expert | nvlink3 | infiniband_hdr | 172 | 607.84 us | 164.5 tok/s | 1,645.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.77 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.07 us |
| DSV4-Flash/a100_sxm_80gb-x69-pipeline | DeepSeek-V4-Flash-0731 | 69 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x69-tensor | DeepSeek-V4-Flash-0731 | 69 | tensor | nvlink3 | infiniband_hdr | 172 | 860.47 us | 116.2 tok/s | 1,162.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 424.31 us |
| DSV4-Flash/a100_sxm_80gb-x69-hybrid | DeepSeek-V4-Flash-0731 | 69 | hybrid | nvlink3 | infiniband_hdr | 94 | 455.03 us | 219.8 tok/s | 2,197.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| DSV4-Flash/a100_sxm_80gb-x69-expert | DeepSeek-V4-Flash-0731 | 69 | expert | nvlink3 | infiniband_hdr | 172 | 607.80 us | 164.5 tok/s | 1,645.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.77 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 177.03 us |
| DSV4-Flash/a100_sxm_80gb-x73-pipeline | DeepSeek-V4-Flash-0731 | 73 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x73-tensor | DeepSeek-V4-Flash-0731 | 73 | tensor | nvlink3 | infiniband_hdr | 172 | 861.41 us | 116.1 tok/s | 1,160.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 425.25 us |
| DSV4-Flash/a100_sxm_80gb-x73-hybrid | DeepSeek-V4-Flash-0731 | 73 | hybrid | nvlink3 | infiniband_hdr | 95 | 457.38 us | 218.6 tok/s | 2,186.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| DSV4-Flash/a100_sxm_80gb-x73-expert | DeepSeek-V4-Flash-0731 | 73 | expert | nvlink3 | infiniband_hdr | 172 | 607.58 us | 164.6 tok/s | 1,645.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.68 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.90 us |
| DSV4-Flash/a100_sxm_80gb-x104-pipeline | DeepSeek-V4-Flash-0731 | 104 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x104-tensor | DeepSeek-V4-Flash-0731 | 104 | tensor | nvlink3 | infiniband_hdr | 172 | 863.36 us | 115.8 tok/s | 1,158.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 427.20 us |
| DSV4-Flash/a100_sxm_80gb-x104-hybrid | DeepSeek-V4-Flash-0731 | 104 | hybrid | nvlink3 | infiniband_hdr | 98 | 464.46 us | 215.3 tok/s | 2,153.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.29 us |
| DSV4-Flash/a100_sxm_80gb-x104-expert | DeepSeek-V4-Flash-0731 | 104 | expert | nvlink3 | infiniband_hdr | 172 | 606.68 us | 164.8 tok/s | 1,648.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.47 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.21 us |
| DSV4-Flash/a100_sxm_80gb-x110-pipeline | DeepSeek-V4-Flash-0731 | 110 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x110-tensor | DeepSeek-V4-Flash-0731 | 110 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x110-hybrid | DeepSeek-V4-Flash-0731 | 110 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x110-expert | DeepSeek-V4-Flash-0731 | 110 | expert | nvlink3 | infiniband_hdr | 172 | 606.59 us | 164.9 tok/s | 1,648.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.47 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.12 us |
| DSV4-Flash/a100_sxm_80gb-x111-pipeline | DeepSeek-V4-Flash-0731 | 111 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x111-tensor | DeepSeek-V4-Flash-0731 | 111 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x111-hybrid | DeepSeek-V4-Flash-0731 | 111 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x111-expert | DeepSeek-V4-Flash-0731 | 111 | expert | nvlink3 | infiniband_hdr | 172 | 606.58 us | 164.9 tok/s | 1,648.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.47 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.10 us |
| DSV4-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Flash-0731 | 112 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Flash-0731 | 112 | tensor | nvlink3 | infiniband_hdr | 172 | 863.83 us | 115.8 tok/s | 1,157.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 427.66 us |
| DSV4-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Flash-0731 | 112 | hybrid | nvlink3 | infiniband_hdr | 99 | 466.81 us | 214.2 tok/s | 2,142.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| DSV4-Flash/a100_sxm_80gb-x112-expert | DeepSeek-V4-Flash-0731 | 112 | expert | nvlink3 | infiniband_hdr | 172 | 606.53 us | 164.9 tok/s | 1,648.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.44 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 176.09 us |
| DSV4-Flash/a100_sxm_80gb-x138-pipeline | DeepSeek-V4-Flash-0731 | 138 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x138-tensor | DeepSeek-V4-Flash-0731 | 138 | tensor | nvlink3 | infiniband_hdr | 172 | 865.17 us | 115.6 tok/s | 1,155.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 429.00 us |
| DSV4-Flash/a100_sxm_80gb-x138-hybrid | DeepSeek-V4-Flash-0731 | 138 | hybrid | nvlink3 | infiniband_hdr | 103 | 476.25 us | 210.0 tok/s | 2,099.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| DSV4-Flash/a100_sxm_80gb-x138-expert | DeepSeek-V4-Flash-0731 | 138 | expert | nvlink3 | infiniband_hdr | 172 | 606.17 us | 165.0 tok/s | 1,649.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.36 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.81 us |
| DSV4-Flash/a100_sxm_80gb-x146-pipeline | DeepSeek-V4-Flash-0731 | 146 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x146-tensor | DeepSeek-V4-Flash-0731 | 146 | tensor | nvlink3 | infiniband_hdr | 172 | 865.42 us | 115.6 tok/s | 1,155.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 429.25 us |
| DSV4-Flash/a100_sxm_80gb-x146-hybrid | DeepSeek-V4-Flash-0731 | 146 | hybrid | nvlink3 | infiniband_hdr | 104 | 478.60 us | 208.9 tok/s | 2,089.4 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 42.44 us |
| DSV4-Flash/a100_sxm_80gb-x146-expert | DeepSeek-V4-Flash-0731 | 146 | expert | nvlink3 | infiniband_hdr | 172 | 606.08 us | 165.0 tok/s | 1,649.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.34 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 175.74 us |
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
| DSV4-Flash/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Flash-0731 | 448 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Flash-0731 | 448 | tensor | nvlink3 | infiniband_hdr | 172 | 1,217.52 us | 82.1 tok/s | 821.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 781.35 us |
| DSV4-Flash/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Flash-0731 | 448 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x448-expert | DeepSeek-V4-Flash-0731 | 448 | expert | nvlink3 | infiniband_hdr | 172 | 605.07 us | 165.3 tok/s | 1,652.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.11 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 174.96 us |
| DSV4-Flash/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Flash-0731 | 672 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| DSV4-Flash/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Flash-0731 | 672 | tensor | nvlink3 | infiniband_hdr | 172 | 1,218.02 us | 82.1 tok/s | 821.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 781.85 us |
| DSV4-Flash/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Flash-0731 | 672 | hybrid | nvlink3 | infiniband_hdr | 128 | 535.19 us | 186.9 tok/s | 1,868.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 99.02 us |
| DSV4-Flash/a100_sxm_80gb-x672-expert | DeepSeek-V4-Flash-0731 | 672 | expert | nvlink3 | infiniband_hdr | 172 | 604.90 us | 165.3 tok/s | 1,653.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 430.07 us; 86 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 174.83 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 1 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 16,019.5 | 0.289 | 16,019.5 (55,420) | 5,520.1 (46,225) | 0.34x | compute |
| DeepSeek-V4-Flash-0731 | 2 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 16,019.5 | 0.289 | 16,019.5 (55,420) | 5,423.8 (46,225) | 0.34x | compute |
| DeepSeek-V4-Flash-0731 | 4 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 16,019.5 | 0.289 | 16,019.5 (55,420) | 5,433.3 (92,450) | 0.34x | compute |
| DeepSeek-V4-Flash-0731 | 8 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 16,019.5 | 0.289 | 16,019.5 (55,420) | 5,326.9 (92,450) | 0.33x | compute |
| DeepSeek-V4-Flash-0731 | 16 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 16,019.5 | 0.289 | 16,019.5 (55,420) | 5,296.4 (92,450) | 0.33x | compute |
| DeepSeek-V4-Flash-0731 | 32 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x148-romfill | 120,620 | 15,680.6 | 0.130 | 15,680.6 (120,620) | 5,296.4 (92,450) | 0.34x | compute |
| DeepSeek-V4-Flash-0731 | 64 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 15,527.8 | 0.056 | 15,527.8 (277,100) | 5,296.4 (92,450) | 0.34x | compute |
| DeepSeek-V4-Flash-0731 | 256 | array | array | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,364.6 | 0.023 | 6,364.6 (277,100) | 5,310.5 (277,350) | 0.83x | compute |
| DeepSeek-V4-Flash-0731 | 1024 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 3,651.1 | 0.007 | 1,778.8 (277,100) | 3,651.1 (554,700) | 2.05x | compute |
| DeepSeek-V4-Flash-0731 | 4096 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1,134.4 | 0.002 | 532.3 (185,005) | 1,134.4 (554,700) | 2.13x | kv_read |

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
| DeepSeek-V4-Flash-0731 | 1 | sram | 384,602.4 | 28,756.4 | 28,756.4 | 13.37x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 384,602.4 | 28,756.4 | 28,756.4 | 13.37x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 384,602.4 | 28,756.4 | 34,043.6 | 13.37x | 1.18x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | sram | 384,602.4 | 28,756.4 | 55,424.3 | 13.37x | 1.93x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | sram | 384,602.4 | 28,756.4 | 87,079.2 | 13.37x | 3.03x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 384,602.4 | 28,756.4 | 128,580.8 | 13.37x | 4.47x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 543,246.5 | 28,784.4 | 177,416.0 | 18.87x | 6.16x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 925,350.6 | 28,956.7 | 390,776.4 | 31.96x | 13.50x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1024 | sram | 2,268,824.4 | 29,000.1 | 496,886.5 | 78.24x | 17.13x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 4096 | sram | 4,646,451.6 | 29,011.0 | 622,897.5 | 160.16x | 21.47x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 3,621,263.4 | 89,874.7 | 89,874.7 | 40.29x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 3,621,263.4 | 89,874.7 | 89,874.7 | 40.29x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 3,621,263.4 | 89,874.7 | 89,874.7 | 40.29x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 3,621,263.4 | 89,874.7 | 89,874.7 | 40.29x | 1.00x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 3,621,263.4 | 89,874.7 | 115,939.3 | 40.29x | 1.29x | compute | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | rom | 3,621,263.4 | 89,874.7 | 172,029.1 | 40.29x | 1.91x | compute | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | rom | 3,621,263.4 | 90,149.0 | 235,692.3 | 40.17x | 2.61x | compute | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | rom | 3,621,263.4 | 91,861.2 | 394,656.5 | 39.42x | 4.30x | compute | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1024 | rom | 3,738,753.6 | 92,299.4 | 612,026.8 | 40.51x | 6.63x | compute | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4096 | rom | 3,928,550.2 | 92,409.6 | 951,097.0 | 42.51x | 10.29x | compute | weight_read | weight_read |

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
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 3,621,263.4 | 6.528 | compute | 9.42x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.00 | 89,874.7 | 1.944 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 1.00 | 89,874.7 | 1.944 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 3,621,263.4 | 6.528 | compute | 9.42x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.00 | 89,874.7 | 1.944 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 1.00 | 89,874.7 | 1.944 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 3,621,263.4 | 6.528 | compute | 9.42x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.00 | 89,874.7 | 1.944 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x18-perregion | 14,670 | 1.00 | 1.57 | 34,043.6 | 2.321 | weight_read | 0.09x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 1.00 | 89,874.7 | 1.944 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 3,621,263.4 | 6.528 | compute | 9.42x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.00 | 89,874.7 | 1.944 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x18-perregion | 14,670 | 1.00 | 2.13 | 55,424.3 | 3.778 | weight_read | 0.14x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 3.19 | 1.00 | 89,874.7 | 1.944 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 3,621,263.4 | 6.528 | compute | 9.42x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.00 | 89,874.7 | 1.944 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x20-perregion | 16,300 | 1.00 | 2.88 | 87,079.2 | 5.342 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x34-perregion-romfill | 27,710 | 1.75 | 2.88 | 115,939.3 | 4.184 | link_latency | 0.30x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 384,602.4 | 0.693 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 3,621,263.4 | 6.528 | compute | 9.42x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,756.4 | 0.622 | weight_read | 0.07x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.00 | 89,874.7 | 1.944 | weight_read | 0.23x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x20-perregion | 16,300 | 1.00 | 4.03 | 128,580.8 | 7.888 | weight_read | 0.33x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x34-perregion-romfill | 27,710 | 1.75 | 4.03 | 172,029.1 | 6.208 | link_latency | 0.45x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x111 | 90,465 | 1.00 | 1.00 | 543,246.5 | 6.005 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 3,621,263.4 | 6.528 | compute | 6.67x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,784.4 | 0.623 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 1.12 | 90,149.0 | 1.950 | weight_read | 0.17x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x20-perregion | 16,300 | 1.00 | 5.83 | 177,416.0 | 10.884 | weight_read | 0.33x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x34-perregion-romfill | 27,710 | 1.75 | 5.83 | 235,692.3 | 8.506 | link_latency | 0.43x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x148 | 120,620 | 1.00 | 1.00 | 925,350.6 | 7.672 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 3,621,263.4 | 6.528 | compute | 3.91x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,956.7 | 0.626 | weight_read | 0.03x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 4.49 | 91,861.2 | 1.987 | weight_read | 0.10x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 13.84 | 390,776.4 | 8.454 | weight_read | 0.42x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 3.19 | 13.84 | 394,656.5 | 8.538 | kv_read | 0.43x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 2,268,824.4 | 6.135 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1024 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 3,738,753.6 | 6.740 | compute | 1.65x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 17.96 | 29,000.1 | 0.627 | weight_read | 0.01x |
| DeepSeek-V4-Flash-0731 | 1024 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 17.96 | 92,299.4 | 1.997 | weight_read | 0.04x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 38.75 | 496,886.5 | 10.749 | kv_read | 0.22x |
| DeepSeek-V4-Flash-0731 | 1024 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x34-perregion-romfill | 27,710 | 1.75 | 8.18 | 612,026.8 | 22.087 | weight_read | 0.27x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 4,646,451.6 | 8.377 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 4096 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 10.55 | 1.00 | 3,928,550.2 | 7.082 | compute | 0.85x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 71.86 | 29,011.0 | 0.628 | weight_read | 0.01x |
| DeepSeek-V4-Flash-0731 | 4096 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 3.19 | 71.86 | 92,409.6 | 1.999 | weight_read | 0.02x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x20-perregion | 16,300 | 1.00 | 32.49 | 622,897.5 | 38.215 | weight_read | 0.13x |
| DeepSeek-V4-Flash-0731 | 4096 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x34-perregion-romfill | 27,710 | 1.75 | 20.82 | 951,097.0 | 34.323 | weight_read | 0.20x |

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
| DeepSeek-V4-Flash-0731 | 1 | 18 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 57 | 1.12 | 1.001 | 1.014 | 1.01x |
| DeepSeek-V4-Flash-0731 | 256 | 57 | 4.49 | 1.042 | 1.670 | 1.60x |
| DeepSeek-V4-Flash-0731 | 1024 | 20 | 51.20 | 1.707 | 5.155 | 3.02x |
| DeepSeek-V4-Flash-0731 | 4096 | 20 | 204.80 | 4.838 | 11.909 | 2.46x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 6 | 3.99 | 2.71 | 1.47x |
| DeepSeek-V4-Flash-0731 | 2 | 6 | 5.31 | 3.23 | 1.64x |
| DeepSeek-V4-Flash-0731 | 4 | 6 | 5.91 | 3.73 | 1.59x |
| DeepSeek-V4-Flash-0731 | 8 | 6 | 6.00 | 4.17 | 1.44x |
| DeepSeek-V4-Flash-0731 | 16 | 6 | 6.00 | 4.54 | 1.32x |
| DeepSeek-V4-Flash-0731 | 32 | 6 | 6.00 | 4.81 | 1.25x |
| DeepSeek-V4-Flash-0731 | 64 | 6 | 6.00 | 4.99 | 1.20x |
| DeepSeek-V4-Flash-0731 | 256 | 6 | 6.00 | 5.09 | 1.18x |
| DeepSeek-V4-Flash-0731 | 1024 | 6 | 6.00 | 5.09 | 1.18x |
| DeepSeek-V4-Flash-0731 | 4096 | 6 | 6.00 | 5.09 | 1.18x |
| DeepSeek-V4-Flash-0731 | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 8.86 | 5.03 | 1.76x |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 13.21 | 6.47 | 2.04x |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 16.56 | 7.99 | 2.07x |
| DeepSeek-V4-Flash-0731 | 16 | 18 | 17.82 | 9.44 | 1.89x |
| DeepSeek-V4-Flash-0731 | 32 | 18 | 17.99 | 10.67 | 1.69x |
| DeepSeek-V4-Flash-0731 | 64 | 18 | 18.00 | 11.53 | 1.56x |
| DeepSeek-V4-Flash-0731 | 256 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 1024 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 4096 | 18 | 18.00 | 12.05 | 1.49x |
| DeepSeek-V4-Flash-0731 | 1 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 2 | 20 | 9.11 | 5.21 | 1.75x |
| DeepSeek-V4-Flash-0731 | 4 | 20 | 13.91 | 6.76 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 20 | 17.93 | 8.43 | 2.13x |
| DeepSeek-V4-Flash-0731 | 16 | 20 | 19.68 | 10.04 | 1.96x |
| DeepSeek-V4-Flash-0731 | 32 | 20 | 19.98 | 11.42 | 1.75x |
| DeepSeek-V4-Flash-0731 | 64 | 20 | 20.00 | 12.40 | 1.61x |
| DeepSeek-V4-Flash-0731 | 256 | 20 | 20.00 | 13.00 | 1.54x |
| DeepSeek-V4-Flash-0731 | 1024 | 20 | 20.00 | 13.00 | 1.54x |
| DeepSeek-V4-Flash-0731 | 4096 | 20 | 20.00 | 13.00 | 1.54x |
| DeepSeek-V4-Flash-0731 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Flash-0731 | 2 | 22 | 9.33 | 5.36 | 1.74x |
| DeepSeek-V4-Flash-0731 | 4 | 22 | 14.51 | 7.03 | 2.06x |
| DeepSeek-V4-Flash-0731 | 8 | 22 | 19.19 | 8.83 | 2.17x |
| DeepSeek-V4-Flash-0731 | 16 | 22 | 21.49 | 10.61 | 2.03x |
| DeepSeek-V4-Flash-0731 | 32 | 22 | 21.96 | 12.14 | 1.81x |
| DeepSeek-V4-Flash-0731 | 64 | 22 | 22.00 | 13.24 | 1.66x |
| DeepSeek-V4-Flash-0731 | 256 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 1024 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 4096 | 22 | 22.00 | 13.91 | 1.58x |
| DeepSeek-V4-Flash-0731 | 1 | 34 | 5.58 | 4.44 | 1.26x |
| DeepSeek-V4-Flash-0731 | 2 | 34 | 10.14 | 6.09 | 1.66x |
| DeepSeek-V4-Flash-0731 | 4 | 34 | 16.97 | 8.30 | 2.05x |
| DeepSeek-V4-Flash-0731 | 8 | 34 | 24.92 | 10.80 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 34 | 30.96 | 13.41 | 2.31x |
| DeepSeek-V4-Flash-0731 | 32 | 34 | 33.42 | 15.79 | 2.12x |
| DeepSeek-V4-Flash-0731 | 64 | 34 | 33.91 | 17.56 | 1.93x |
| DeepSeek-V4-Flash-0731 | 256 | 34 | 33.98 | 18.68 | 1.82x |
| DeepSeek-V4-Flash-0731 | 1024 | 34 | 33.98 | 18.69 | 1.82x |
| DeepSeek-V4-Flash-0731 | 4096 | 34 | 33.98 | 18.69 | 1.82x |
| DeepSeek-V4-Flash-0731 | 1 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Flash-0731 | 2 | 37 | 10.26 | 6.23 | 1.65x |
| DeepSeek-V4-Flash-0731 | 4 | 37 | 17.39 | 8.55 | 2.03x |
| DeepSeek-V4-Flash-0731 | 8 | 37 | 25.99 | 11.20 | 2.32x |
| DeepSeek-V4-Flash-0731 | 16 | 37 | 32.96 | 14.00 | 2.35x |
| DeepSeek-V4-Flash-0731 | 32 | 37 | 36.11 | 16.57 | 2.18x |
| DeepSeek-V4-Flash-0731 | 64 | 37 | 36.85 | 18.50 | 1.99x |
| DeepSeek-V4-Flash-0731 | 256 | 37 | 36.97 | 19.73 | 1.87x |
| DeepSeek-V4-Flash-0731 | 1024 | 37 | 36.97 | 19.74 | 1.87x |
| DeepSeek-V4-Flash-0731 | 4096 | 37 | 36.97 | 19.74 | 1.87x |
| DeepSeek-V4-Flash-0731 | 1 | 40 | 5.64 | 4.59 | 1.23x |
| DeepSeek-V4-Flash-0731 | 2 | 40 | 10.37 | 6.37 | 1.63x |
| DeepSeek-V4-Flash-0731 | 4 | 40 | 17.75 | 8.78 | 2.02x |
| DeepSeek-V4-Flash-0731 | 8 | 40 | 26.95 | 11.57 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 40 | 34.83 | 14.55 | 2.39x |
| DeepSeek-V4-Flash-0731 | 32 | 40 | 38.73 | 17.31 | 2.24x |
| DeepSeek-V4-Flash-0731 | 64 | 40 | 39.75 | 19.40 | 2.05x |
| DeepSeek-V4-Flash-0731 | 256 | 40 | 39.94 | 20.73 | 1.93x |
| DeepSeek-V4-Flash-0731 | 1024 | 40 | 39.94 | 20.74 | 1.93x |
| DeepSeek-V4-Flash-0731 | 4096 | 40 | 39.94 | 20.74 | 1.93x |
| DeepSeek-V4-Flash-0731 | 1 | 43 | 5.66 | 4.66 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 43 | 10.47 | 6.49 | 1.61x |
| DeepSeek-V4-Flash-0731 | 4 | 43 | 18.07 | 9.00 | 2.01x |
| DeepSeek-V4-Flash-0731 | 8 | 43 | 27.82 | 11.92 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 43 | 36.58 | 15.07 | 2.43x |
| DeepSeek-V4-Flash-0731 | 32 | 43 | 41.25 | 18.02 | 2.29x |
| DeepSeek-V4-Flash-0731 | 64 | 43 | 42.61 | 20.26 | 2.10x |
| DeepSeek-V4-Flash-0731 | 256 | 43 | 42.89 | 21.69 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1024 | 43 | 42.90 | 21.70 | 1.98x |
| DeepSeek-V4-Flash-0731 | 4096 | 43 | 42.90 | 21.70 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1 | 44 | 5.67 | 4.68 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 44 | 10.50 | 6.53 | 1.61x |
| DeepSeek-V4-Flash-0731 | 4 | 44 | 18.17 | 9.06 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 44 | 28.09 | 12.03 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 44 | 37.14 | 15.23 | 2.44x |
| DeepSeek-V4-Flash-0731 | 32 | 44 | 42.08 | 18.24 | 2.31x |
| DeepSeek-V4-Flash-0731 | 64 | 44 | 43.56 | 20.53 | 2.12x |
| DeepSeek-V4-Flash-0731 | 256 | 44 | 43.88 | 22.00 | 1.99x |
| DeepSeek-V4-Flash-0731 | 1024 | 44 | 43.88 | 22.01 | 1.99x |
| DeepSeek-V4-Flash-0731 | 4096 | 44 | 43.88 | 22.01 | 1.99x |
| DeepSeek-V4-Flash-0731 | 1 | 46 | 5.68 | 4.72 | 1.21x |
| DeepSeek-V4-Flash-0731 | 2 | 46 | 10.55 | 6.61 | 1.60x |
| DeepSeek-V4-Flash-0731 | 4 | 46 | 18.36 | 9.19 | 2.00x |
| DeepSeek-V4-Flash-0731 | 8 | 46 | 28.60 | 12.24 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 46 | 38.22 | 15.56 | 2.46x |
| DeepSeek-V4-Flash-0731 | 32 | 46 | 43.69 | 18.69 | 2.34x |
| DeepSeek-V4-Flash-0731 | 64 | 46 | 45.43 | 21.07 | 2.16x |
| DeepSeek-V4-Flash-0731 | 256 | 46 | 45.83 | 22.61 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1024 | 46 | 45.83 | 22.63 | 2.03x |
| DeepSeek-V4-Flash-0731 | 4096 | 46 | 45.83 | 22.63 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1 | 49 | 5.70 | 4.77 | 1.20x |
| DeepSeek-V4-Flash-0731 | 2 | 49 | 10.63 | 6.72 | 1.58x |
| DeepSeek-V4-Flash-0731 | 4 | 49 | 18.61 | 9.38 | 1.98x |
| DeepSeek-V4-Flash-0731 | 8 | 49 | 29.32 | 12.55 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 49 | 39.75 | 16.03 | 2.48x |
| DeepSeek-V4-Flash-0731 | 32 | 49 | 46.04 | 19.33 | 2.38x |
| DeepSeek-V4-Flash-0731 | 64 | 49 | 48.21 | 21.86 | 2.21x |
| DeepSeek-V4-Flash-0731 | 256 | 49 | 48.75 | 23.50 | 2.07x |
| DeepSeek-V4-Flash-0731 | 1024 | 49 | 48.75 | 23.51 | 2.07x |
| DeepSeek-V4-Flash-0731 | 4096 | 49 | 48.75 | 23.51 | 2.07x |
| DeepSeek-V4-Flash-0731 | 1 | 50 | 5.71 | 4.79 | 1.19x |
| DeepSeek-V4-Flash-0731 | 2 | 50 | 10.65 | 6.76 | 1.58x |
| DeepSeek-V4-Flash-0731 | 4 | 50 | 18.69 | 9.43 | 1.98x |
| DeepSeek-V4-Flash-0731 | 8 | 50 | 29.55 | 12.65 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 50 | 40.23 | 16.18 | 2.49x |
| DeepSeek-V4-Flash-0731 | 32 | 50 | 46.81 | 19.53 | 2.40x |
| DeepSeek-V4-Flash-0731 | 64 | 50 | 49.12 | 22.12 | 2.22x |
| DeepSeek-V4-Flash-0731 | 256 | 50 | 49.71 | 23.79 | 2.09x |
| DeepSeek-V4-Flash-0731 | 1024 | 50 | 49.72 | 23.80 | 2.09x |
| DeepSeek-V4-Flash-0731 | 4096 | 50 | 49.72 | 23.80 | 2.09x |
| DeepSeek-V4-Flash-0731 | 1 | 52 | 5.72 | 4.82 | 1.19x |
| DeepSeek-V4-Flash-0731 | 2 | 52 | 10.70 | 6.83 | 1.57x |
| DeepSeek-V4-Flash-0731 | 4 | 52 | 18.84 | 9.55 | 1.97x |
| DeepSeek-V4-Flash-0731 | 8 | 52 | 29.98 | 12.84 | 2.34x |
| DeepSeek-V4-Flash-0731 | 16 | 52 | 41.18 | 16.47 | 2.50x |
| DeepSeek-V4-Flash-0731 | 32 | 52 | 48.30 | 19.94 | 2.42x |
| DeepSeek-V4-Flash-0731 | 64 | 52 | 50.93 | 22.62 | 2.25x |
| DeepSeek-V4-Flash-0731 | 256 | 52 | 51.64 | 24.35 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1024 | 52 | 51.64 | 24.37 | 2.12x |
| DeepSeek-V4-Flash-0731 | 4096 | 52 | 51.64 | 24.37 | 2.12x |
| DeepSeek-V4-Flash-0731 | 1 | 55 | 5.73 | 4.86 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 55 | 10.76 | 6.93 | 1.55x |
| DeepSeek-V4-Flash-0731 | 4 | 55 | 19.05 | 9.71 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 55 | 30.58 | 13.11 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 55 | 42.52 | 16.89 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 55 | 50.48 | 20.52 | 2.46x |
| DeepSeek-V4-Flash-0731 | 64 | 55 | 53.60 | 23.34 | 2.30x |
| DeepSeek-V4-Flash-0731 | 256 | 55 | 54.49 | 25.18 | 2.16x |
| DeepSeek-V4-Flash-0731 | 1024 | 55 | 54.50 | 25.19 | 2.16x |
| DeepSeek-V4-Flash-0731 | 4096 | 55 | 54.50 | 25.19 | 2.16x |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 10.77 | 6.96 | 1.55x |
| DeepSeek-V4-Flash-0731 | 4 | 56 | 19.11 | 9.76 | 1.96x |
| DeepSeek-V4-Flash-0731 | 8 | 56 | 30.77 | 13.20 | 2.33x |
| DeepSeek-V4-Flash-0731 | 16 | 56 | 42.95 | 17.03 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 56 | 51.18 | 20.71 | 2.47x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 54.47 | 23.58 | 2.31x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 55.44 | 25.44 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1024 | 56 | 55.44 | 25.46 | 2.18x |
| DeepSeek-V4-Flash-0731 | 4096 | 56 | 55.44 | 25.46 | 2.18x |
| DeepSeek-V4-Flash-0731 | 1 | 67 | 5.78 | 5.02 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 67 | 10.94 | 7.29 | 1.50x |
| DeepSeek-V4-Flash-0731 | 4 | 67 | 19.71 | 10.25 | 1.92x |
| DeepSeek-V4-Flash-0731 | 8 | 67 | 32.55 | 14.09 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 67 | 47.13 | 18.41 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 67 | 58.35 | 22.66 | 2.58x |
| DeepSeek-V4-Flash-0731 | 64 | 67 | 63.68 | 26.01 | 2.45x |
| DeepSeek-V4-Flash-0731 | 256 | 67 | 65.56 | 28.21 | 2.32x |
| DeepSeek-V4-Flash-0731 | 1024 | 67 | 65.57 | 28.23 | 2.32x |
| DeepSeek-V4-Flash-0731 | 4096 | 67 | 65.57 | 28.23 | 2.32x |
| DeepSeek-V4-Flash-0731 | 1 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 68 | 10.96 | 7.32 | 1.50x |
| DeepSeek-V4-Flash-0731 | 4 | 68 | 19.76 | 10.29 | 1.92x |
| DeepSeek-V4-Flash-0731 | 8 | 68 | 32.69 | 14.16 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 68 | 47.47 | 18.53 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 68 | 58.95 | 22.82 | 2.58x |
| DeepSeek-V4-Flash-0731 | 64 | 68 | 64.48 | 26.21 | 2.46x |
| DeepSeek-V4-Flash-0731 | 256 | 68 | 66.45 | 28.45 | 2.34x |
| DeepSeek-V4-Flash-0731 | 1024 | 68 | 66.47 | 28.47 | 2.33x |
| DeepSeek-V4-Flash-0731 | 4096 | 68 | 66.47 | 28.47 | 2.33x |
| DeepSeek-V4-Flash-0731 | 1 | 69 | 5.79 | 5.04 | 1.15x |
| DeepSeek-V4-Flash-0731 | 2 | 69 | 10.97 | 7.34 | 1.49x |
| DeepSeek-V4-Flash-0731 | 4 | 69 | 19.80 | 10.33 | 1.92x |
| DeepSeek-V4-Flash-0731 | 8 | 69 | 32.83 | 14.23 | 2.31x |
| DeepSeek-V4-Flash-0731 | 16 | 69 | 47.80 | 18.64 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 69 | 59.55 | 22.98 | 2.59x |
| DeepSeek-V4-Flash-0731 | 64 | 69 | 65.27 | 26.42 | 2.47x |
| DeepSeek-V4-Flash-0731 | 256 | 69 | 67.34 | 28.68 | 2.35x |
| DeepSeek-V4-Flash-0731 | 1024 | 69 | 67.36 | 28.71 | 2.35x |
| DeepSeek-V4-Flash-0731 | 4096 | 69 | 67.36 | 28.71 | 2.35x |
| DeepSeek-V4-Flash-0731 | 1 | 73 | 5.80 | 5.08 | 1.14x |
| DeepSeek-V4-Flash-0731 | 2 | 73 | 11.02 | 7.45 | 1.48x |
| DeepSeek-V4-Flash-0731 | 4 | 73 | 19.97 | 10.48 | 1.90x |
| DeepSeek-V4-Flash-0731 | 8 | 73 | 33.34 | 14.52 | 2.30x |
| DeepSeek-V4-Flash-0731 | 16 | 73 | 49.06 | 19.09 | 2.57x |
| DeepSeek-V4-Flash-0731 | 32 | 73 | 61.84 | 23.61 | 2.62x |
| DeepSeek-V4-Flash-0731 | 64 | 73 | 68.37 | 27.22 | 2.51x |
| DeepSeek-V4-Flash-0731 | 256 | 73 | 70.85 | 29.60 | 2.39x |
| DeepSeek-V4-Flash-0731 | 1024 | 73 | 70.86 | 29.62 | 2.39x |
| DeepSeek-V4-Flash-0731 | 4096 | 73 | 70.86 | 29.62 | 2.39x |
| DeepSeek-V4-Flash-0731 | 1 | 104 | 5.86 | 5.31 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 104 | 11.26 | 8.12 | 1.39x |
| DeepSeek-V4-Flash-0731 | 4 | 104 | 20.86 | 11.42 | 1.83x |
| DeepSeek-V4-Flash-0731 | 8 | 104 | 36.17 | 16.39 | 2.21x |
| DeepSeek-V4-Flash-0731 | 16 | 104 | 56.38 | 21.98 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 104 | 76.09 | 27.76 | 2.74x |
| DeepSeek-V4-Flash-0731 | 64 | 104 | 88.92 | 32.51 | 2.74x |
| DeepSeek-V4-Flash-0731 | 256 | 104 | 95.18 | 35.72 | 2.66x |
| DeepSeek-V4-Flash-0731 | 1024 | 104 | 95.23 | 35.75 | 2.66x |
| DeepSeek-V4-Flash-0731 | 4096 | 104 | 95.23 | 35.75 | 2.66x |
| DeepSeek-V4-Flash-0731 | 1 | 110 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 110 | 11.29 | 8.23 | 1.37x |
| DeepSeek-V4-Flash-0731 | 4 | 110 | 20.98 | 11.57 | 1.81x |
| DeepSeek-V4-Flash-0731 | 8 | 110 | 36.56 | 16.69 | 2.19x |
| DeepSeek-V4-Flash-0731 | 16 | 110 | 57.43 | 22.44 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 110 | 78.28 | 28.44 | 2.75x |
| DeepSeek-V4-Flash-0731 | 64 | 110 | 92.27 | 33.39 | 2.76x |
| DeepSeek-V4-Flash-0731 | 256 | 110 | 99.32 | 36.75 | 2.70x |
| DeepSeek-V4-Flash-0731 | 1024 | 110 | 99.38 | 36.78 | 2.70x |
| DeepSeek-V4-Flash-0731 | 4096 | 110 | 99.38 | 36.78 | 2.70x |
| DeepSeek-V4-Flash-0731 | 1 | 111 | 5.87 | 5.34 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 111 | 11.30 | 8.25 | 1.37x |
| DeepSeek-V4-Flash-0731 | 4 | 111 | 21.00 | 11.59 | 1.81x |
| DeepSeek-V4-Flash-0731 | 8 | 111 | 36.62 | 16.74 | 2.19x |
| DeepSeek-V4-Flash-0731 | 16 | 111 | 57.59 | 22.52 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 111 | 78.62 | 28.55 | 2.75x |
| DeepSeek-V4-Flash-0731 | 64 | 111 | 92.82 | 33.53 | 2.77x |
| DeepSeek-V4-Flash-0731 | 256 | 111 | 100.00 | 36.92 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1024 | 111 | 100.06 | 36.95 | 2.71x |
| DeepSeek-V4-Flash-0731 | 4096 | 111 | 100.06 | 36.95 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 112 | 11.30 | 8.26 | 1.37x |
| DeepSeek-V4-Flash-0731 | 4 | 112 | 21.01 | 11.62 | 1.81x |
| DeepSeek-V4-Flash-0731 | 8 | 112 | 36.68 | 16.79 | 2.18x |
| DeepSeek-V4-Flash-0731 | 16 | 112 | 57.76 | 22.59 | 2.56x |
| DeepSeek-V4-Flash-0731 | 32 | 112 | 78.97 | 28.66 | 2.76x |
| DeepSeek-V4-Flash-0731 | 64 | 112 | 93.35 | 33.67 | 2.77x |
| DeepSeek-V4-Flash-0731 | 256 | 112 | 100.67 | 37.08 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1024 | 112 | 100.73 | 37.11 | 2.71x |
| DeepSeek-V4-Flash-0731 | 4096 | 112 | 100.73 | 37.11 | 2.71x |
| DeepSeek-V4-Flash-0731 | 1 | 138 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Flash-0731 | 2 | 138 | 11.40 | 8.65 | 1.32x |
| DeepSeek-V4-Flash-0731 | 4 | 138 | 21.40 | 12.19 | 1.76x |
| DeepSeek-V4-Flash-0731 | 8 | 138 | 37.97 | 17.89 | 2.12x |
| DeepSeek-V4-Flash-0731 | 16 | 138 | 61.34 | 24.29 | 2.53x |
| DeepSeek-V4-Flash-0731 | 32 | 138 | 86.73 | 31.22 | 2.78x |
| DeepSeek-V4-Flash-0731 | 64 | 138 | 105.75 | 37.05 | 2.85x |
| DeepSeek-V4-Flash-0731 | 256 | 138 | 116.46 | 41.05 | 2.84x |
| DeepSeek-V4-Flash-0731 | 1024 | 138 | 116.56 | 41.09 | 2.84x |
| DeepSeek-V4-Flash-0731 | 4096 | 138 | 116.56 | 41.09 | 2.84x |
| DeepSeek-V4-Flash-0731 | 1 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Flash-0731 | 2 | 146 | 11.43 | 8.76 | 1.30x |
| DeepSeek-V4-Flash-0731 | 4 | 146 | 21.49 | 12.35 | 1.74x |
| DeepSeek-V4-Flash-0731 | 8 | 146 | 38.28 | 18.17 | 2.11x |
| DeepSeek-V4-Flash-0731 | 16 | 146 | 62.23 | 24.74 | 2.52x |
| DeepSeek-V4-Flash-0731 | 32 | 146 | 88.72 | 31.93 | 2.78x |
| DeepSeek-V4-Flash-0731 | 64 | 146 | 109.04 | 37.99 | 2.87x |
| DeepSeek-V4-Flash-0731 | 256 | 146 | 120.77 | 42.16 | 2.86x |
| DeepSeek-V4-Flash-0731 | 1024 | 146 | 120.87 | 42.20 | 2.86x |
| DeepSeek-V4-Flash-0731 | 4096 | 146 | 120.87 | 42.20 | 2.86x |
| DeepSeek-V4-Flash-0731 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 2 | 168 | 11.48 | 9.01 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 168 | 21.70 | 12.77 | 1.70x |
| DeepSeek-V4-Flash-0731 | 8 | 168 | 39.00 | 18.86 | 2.07x |
| DeepSeek-V4-Flash-0731 | 16 | 168 | 64.32 | 25.90 | 2.48x |
| DeepSeek-V4-Flash-0731 | 32 | 168 | 93.48 | 33.74 | 2.77x |
| DeepSeek-V4-Flash-0731 | 64 | 168 | 117.06 | 40.37 | 2.90x |
| DeepSeek-V4-Flash-0731 | 256 | 168 | 131.43 | 44.95 | 2.92x |
| DeepSeek-V4-Flash-0731 | 1024 | 168 | 131.56 | 45.00 | 2.92x |
| DeepSeek-V4-Flash-0731 | 4096 | 168 | 131.56 | 45.00 | 2.92x |
| DeepSeek-V4-Flash-0731 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 224 | 11.58 | 9.50 | 1.22x |
| DeepSeek-V4-Flash-0731 | 4 | 224 | 22.06 | 13.68 | 1.61x |
| DeepSeek-V4-Flash-0731 | 8 | 224 | 40.23 | 20.13 | 2.00x |
| DeepSeek-V4-Flash-0731 | 16 | 224 | 67.98 | 28.43 | 2.39x |
| DeepSeek-V4-Flash-0731 | 32 | 224 | 102.19 | 37.57 | 2.72x |
| DeepSeek-V4-Flash-0731 | 64 | 224 | 132.41 | 45.34 | 2.92x |
| DeepSeek-V4-Flash-0731 | 256 | 224 | 152.56 | 50.95 | 2.99x |
| DeepSeek-V4-Flash-0731 | 1024 | 224 | 152.75 | 51.00 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 224 | 152.75 | 51.00 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 335 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 335 | 11.67 | 10.10 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 335 | 22.42 | 15.08 | 1.49x |
| DeepSeek-V4-Flash-0731 | 8 | 335 | 41.50 | 21.74 | 1.91x |
| DeepSeek-V4-Flash-0731 | 16 | 335 | 71.92 | 32.23 | 2.23x |
| DeepSeek-V4-Flash-0731 | 32 | 335 | 112.01 | 42.67 | 2.63x |
| DeepSeek-V4-Flash-0731 | 64 | 335 | 150.70 | 52.74 | 2.86x |
| DeepSeek-V4-Flash-0731 | 256 | 335 | 178.89 | 59.63 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 335 | 179.16 | 59.70 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 335 | 179.16 | 59.70 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 336 | 11.67 | 10.11 | 1.15x |
| DeepSeek-V4-Flash-0731 | 4 | 336 | 22.42 | 15.09 | 1.49x |
| DeepSeek-V4-Flash-0731 | 8 | 336 | 41.51 | 21.75 | 1.91x |
| DeepSeek-V4-Flash-0731 | 16 | 336 | 71.94 | 32.26 | 2.23x |
| DeepSeek-V4-Flash-0731 | 32 | 336 | 112.08 | 42.70 | 2.62x |
| DeepSeek-V4-Flash-0731 | 64 | 336 | 150.82 | 52.80 | 2.86x |
| DeepSeek-V4-Flash-0731 | 256 | 336 | 179.07 | 59.69 | 3.00x |
| DeepSeek-V4-Flash-0731 | 1024 | 336 | 179.34 | 59.76 | 3.00x |
| DeepSeek-V4-Flash-0731 | 4096 | 336 | 179.34 | 59.76 | 3.00x |
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
| rom | DeepSeek-V4-Flash-0731 | 1 | 12.39 | 19.9% |

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
| DeepSeek-V4-Flash-0731 | 1 | 18 | 8.63% | 6.74 | 4.34 |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 8.63% | 6.74 | 4.34 |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 8.63% | 6.74 | 4.34 |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 8.63% | 6.74 | 4.34 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 0.10% | 0.25 | 4.34 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 0.10% | 0.25 | 4.34 |
| DeepSeek-V4-Flash-0731 | 64 | 1 | 0.11% | 0.28 | 4.34 |
| DeepSeek-V4-Flash-0731 | 256 | 1 | 0.45% | 1.12 | 4.34 |

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
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,139.6 | 46,721.8 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,139.6 | 46,721.8 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,139.6 | 46,721.8 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,139.6 | 46,721.8 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,139.6 | 46,721.8 |
| DeepSeek-V4-Flash-0731 | 32 | 2.34% | 11.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 1,139.6 | 46,721.8 |
| DeepSeek-V4-Flash-0731 | 64 | 3.63% | 13.1 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 734.1 | 46,985.2 |
| DeepSeek-V4-Flash-0731 | 256 | 13.76% | 28.0 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 184.9 | 47,342.2 |
| DeepSeek-V4-Flash-0731 | 1024 | 44.70% | 73.5 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 46.3 | 47,432.3 |
| DeepSeek-V4-Flash-0731 | 4096 | 90.65% | 141.2 GB | 100.00% | 4,841.92 TB/s | 4,841.92 TB/s | 11.6 | 47,454.8 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 19 |
| gpu | link_latency | 348 |
| gpu | weight_read | 863 |
| rom | compute | 899 |
| rom | infeasible | 2528 |
| rom | kv_read | 101 |
| rom | link_latency | 1246 |
| rom | weight_read | 686 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2528 |

## Mechanical consistency audit

**FAIL** over 134,363 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x47', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x50', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x51', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x53', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x70', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x105', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x140', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x47', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x50', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x51', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x53', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x70', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x105', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x140', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x47', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x50', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x51', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x53', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x57', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x70', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x105', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x140', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x38', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x44', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x45', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x47', 'DeepSeek-V4-Flash-0731', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x50', 'DeepSeek-V4-Flash-0731', 1)

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

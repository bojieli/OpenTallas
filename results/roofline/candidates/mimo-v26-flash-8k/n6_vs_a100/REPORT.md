# Area-constrained roofline: n6_vs_a100-mimo-v26-flash-8k

> CANDIDATE MODEL under n6_vs_a100: MiMo-V2.6-Flash at 8,192 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 261x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 68 devices. On the GPU side the correction reaches 56x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 107 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Flash takes 43 x 815 mm2 (35,045 mm2, array, KV in SRAM) at 11,302 tok/s per user and 323 tok/s per 1,000 mm2, holding 1 session, against 42 copies of one unified HBM die at the same silicon: 13.0x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Flash on 277,100 mm2 of ROM silicon at 14,657 tok/s per user against 276,710 mm2 of a100_sxm_80gb-x335-tensor at 718 tok/s: **20.4x**, ROM binding on `weight_read` and the GPU on `link_latency`. It holds 114,230 resident sessions against the GPU cluster's 111,744. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 7.83x to it.** At 185,005 mm2 on MiMo-V2.6-Flash the pipeline-only GPU delivers 126.09 tok/s and the same silicon running tensor delivers 987 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (MiMo-V2.6-Flash, ROM binding on `link_latency`) to 4.63x (MiMo-V2.6-Flash, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Flash engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 1,000 to 42,528 tok/s, and its rate with every slot occupied from 42,017 to 42,528. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 42 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,360 us over NVLink, capping per-user decode at 735 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 206.1 us and cap it at 4,852 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 5.2x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 0 of 10 operating points and an array 10; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 393 of 4356 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 65.1x of aggregate throughput (MiMo-V2.6-Flash). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 11.38x, on MiMo-V2.6-Flash at batch 256, where the busiest region carries 3.02x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### MiMo-V2.6-Flash at 8,192 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x43`** -- 43 x 815 mm2 reticle dies, 35,045 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **11,302.3 tok/s per user** (0.09 ms/token), binding on `link_latency`
- **322.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 11,302 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 2,216 W at 0.063 W/mm2, 196.1 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 42 copies of one unified HBM die -- `a100_sxm_80gb-x42-tensor`, 34,692 mm2, area ratio 1.0102 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 35,045 | 34,692 | 1.0102 |
| user tok/s | 11,302.3 | 868.1 | 13.02x |
| aggregate tok/s | 11,302 | 868 | 2.13x |
| resident sessions | 1 | 13,303 | -- |
| J/token | 0.1961 | 8.3420 | 42.5x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 13,303 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x224-tensor` at 185,024 mm2 and 986.9 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 15,571.9 | 281.0 | 22,846 | 16.94x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 15,571.9 | 281.0 | 22,846 | 16.94x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x38` | 30,970 | 9,042.2 | 292.0 | 1 | 10.61x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x43` | 35,045 | 11,302.3 | 322.5 | 1 | 13.02x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x43` | 35,045 | 11,302.3 | 322.5 | -- | 322.5 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | 35,860 | 11,355.7 | 316.7 | 65.4 | 322.5 | stop |
| `ROM-N6-native-HBMKV-array-hw-tensor-x49` | 39,935 | 11,649.4 | 291.7 | 71.0 | 322.5 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 15,571.9 | 281.0 | 209.5 | 322.5 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x43` **<-- recommended** | 35,045 | 43 | 11,302.3 | 11,302 | 322.5 | 1 | `link_latency` | 2,216 | 196.1 | `a100_sxm_80gb-x42-tensor` | 13.02x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x44` | 35,860 | 44 | 11,355.7 | 11,356 | 316.7 | 1 | `link_latency` | 2,281 | 200.9 | `a100_sxm_80gb-x43-tensor` | 13.03x |
| `ROM-N6-native-HBMKV-array-hw-tensor-x49` | 39,935 | 49 | 11,649.4 | 11,649 | 291.7 | 16,462 | `link_latency` | 3,824 | 328.3 | `a100_sxm_80gb-x48-tensor` | 13.15x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 68 | 15,571.9 | 264,722 | 281.0 | 22,846 | `compute` | 13,364 | 413.8 | `a100_sxm_80gb-x67-tensor` | 16.94x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 324 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x43` | 35,045 | 11,302.3 | 322.5 | 1 |
| array | 324 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 15,571.9 | 281.0 | 22,846 |
| array | 324 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x38` | 30,970 | 9,042.2 | 292.0 | 1 |
| wafer | 76 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,880.0 | 105.6 | 1 |
| wafer | 76 | fastest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,880.0 | 105.6 | 1 |
| wafer | 76 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,880.0 | 105.6 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 15,571.9 | 264,722 | 22,846 | 13,364 | 413.8 | `compute` | `a100_sxm_80gb-x67-tensor` | 919.3 | 21,703 | 11,880.1 | 1.001 | 16.94x | 28.7x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,880.0 | 4,880 | 1 | 3,746 | 767.6 | `link_latency` | `a100_sxm_80gb-x56-tensor` | 902.8 | 18,007 | 10,313.1 | 0.999 | 5.41x | 13.4x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x59` | 48,085 | 12,958.5 | 194,378 | 19,822 | 10,221 | 399.9 | `compute` | `a100_sxm_80gb-x58-tensor` | 905.3 | 18,679 | 10,606.8 | 1.004 | 14.31x | 26.5x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-tensor-x1` | 46,225 | 4,880.0 | -- | 1 | -- | 767.6 | -- | -- | -- | -- | -- | 1.040 | 0.38x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 15,571.9 | 264,722 | 22,846 | 13,364 | 220.8 | `compute` | `a100_sxm_80gb-x67-tensor` | 816.6 | 21,703 | 6,869.7 | 1.001 | 19.07x | 31.1x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,743.0 | 9,486 | 5,778 | 10,933 | 1,152.6 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 857.1 | 36,822 | 10,380.7 | 0.999 | 5.53x | 9.0x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x113-romfill` | 92,095 | 14,799.2 | 429,176 | 37,964 | 22,148 | 373.3 | `weight_read` | `a100_sxm_80gb-x111-tensor` | 856.4 | 36,486 | 10,303.5 | 1.004 | 17.28x | 27.6x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x2` | 92,450 | 4,743.0 | -- | 5,778 | -- | 1,152.6 | -- | -- | -- | -- | -- | 0.996 | 0.32x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 15,571.9 | 264,722 | 22,846 | 13,364 | 124.3 | `compute` | `a100_sxm_80gb-x67-tensor` | 669.4 | 21,703 | 4,342.8 | 1.001 | 23.26x | 34.9x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,738.4 | 18,954 | 11,557 | 24,842 | 1,310.7 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 742.4 | 74,451 | 11,620.8 | 0.999 | 6.38x | 8.9x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 185,005 | 14,609.6 | 832,748 | 76,265 | 43,675 | 379.4 | `weight_read` | `a100_sxm_80gb-x224-tensor` | 742.4 | 74,451 | 11,620.8 | 1.000 | 19.68x | 30.6x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 4,738.4 | -- | 11,557 | -- | 1,310.7 | -- | -- | -- | -- | -- | 1.001 | 0.32x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 15,571.9 | 264,722 | 22,846 | 13,364 | 76.0 | `compute` | `a100_sxm_80gb-x67-hybrid` | 639.1 | 21,703 | 3,248.8 | 1.001 | 24.36x | 40.0x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 369,800 | 4,729.3 | 37,835 | 23,114 | 35,436 | 936.6 | `link_latency` | `a100_sxm_80gb-x448-hybrid` | 631.4 | 149,709 | 14,162.7 | 0.999 | 7.49x | 15.1x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | 15,571.9 | 264,722 | 22,846 | 13,364 | 51.9 | `compute` | `a100_sxm_80gb-x67-hybrid` | 527.8 | 21,703 | 2,144.4 | 1.001 | 29.50x | 41.3x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,610.6 | 73,770 | 34,672 | 53,582 | 726.3 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 631.4 | 224,967 | 10,961.2 | 0.999 | 7.30x | 15.1x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill` | 127,140 | 14,861.9 | 579,613 | 52,411 | 30,218 | 57.5 | `weight_read` | `a100_sxm_80gb-x154-hybrid` | 554.0 | 50,932 | 2,304.7 | 0.999 | 26.83x | 40.1x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 4,218.5 | 134,993 | 34,672 | 55,122 | 408.3 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 631.4 | 224,967 | 6,159.1 | 0.999 | 6.68x | 15.1x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 14,656.9 | 1,245,836 | 114,230 | 65,376 | 60.6 | `weight_read` | `a100_sxm_80gb-x335-hybrid` | 559.6 | 111,744 | 2,426.7 | 1.001 | 26.19x | 40.1x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,605.3 | 230,742 | 34,672 | 57,519 | 249.3 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 631.4 | 224,967 | 3,758.0 | 0.999 | 5.71x | 15.1x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 277,100 | 6,275.3 | 1,606,481 | 114,230 | 72,771 | 45.3 | `compute` | `a100_sxm_80gb-x335-expert` | 310.7 | 110,317 | 702.1 | 1.001 | 20.19x | 15.5x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,925.8 | 493,006 | 34,672 | 91,278 | 185.1 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 415.8 | 224,967 | 1,711.8 | 0.999 | 4.63x | 6.1x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 1,747.1 | 1,789,068 | 114,230 | 77,544 | 43.3 | `compute` | `a100_sxm_80gb-x335-expert` | 236.9 | 110,317 | 241.7 | 1.001 | 7.38x | 5.6x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 766.0 | 784,349 | 34,672 | 72,729 | 92.7 | `kv_read` | `a100_sxm_80gb-x672-expert` | 311.3 | 222,006 | 346.6 | 0.999 | 2.46x | 3.7x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 277,100 | 443.9 | 1,818,359 | 114,230 | 76,884 | 42.3 | `compute` | `a100_sxm_80gb-x335-expert` | 121.4 | 110,317 | 126.5 | 1.001 | 3.66x | 3.0x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill` | 554,700 | 193.3 | 791,950 | 34,672 | 71,915 | 90.8 | `kv_read` | `a100_sxm_80gb-x672-expert` | 192.0 | 222,006 | 152.6 | 0.999 | 1.01x | 1.7x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x43` | 35,045 | array | SRAM | 1 |
| 2-16 | `ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 55,420 | array | HBM | 22,846 |
| 32-64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x78` | 63,570 | array | HBM | 26,205 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x113` | 92,095 | array | HBM | 37,964 |
| 1024 | `ROM-N6-native-HBMKV-array-hw-pipeline-x113` | 92,095 | array | HBM | 37,964 |
| 4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x117` | 95,355 | array | HBM | 39,308 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Flash | HBM | rom | 42, 49, 54, 56, 57, 59, 68, 78, 113, 117, 156, 170, 227, 340 |
| MiMo-V2.6-Flash | HBM | sram | 42, 49, 54, 56, 57, 59, 68, 78, 113, 117, 156, 170, 227, 340 |
| MiMo-V2.6-Flash | SRAM | rom | 38, 43, 44, 45, 54, 57, 72, 108, 113, 144, 170, 227, 340 |
| MiMo-V2.6-Flash | SRAM | sram | 38, 43, 44, 45, 54, 57, 72, 108, 113, 144, 170, 227, 340 |

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

- **0 of 4,356 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 81% of its cooling budget, and the busiest wafer-scale ROM design 35%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 520 | 0 | 64.7% | 80.6% | 0.390 | 56% |
| gpu | wafer (>=40,000 mm2) | 760 | 0 | 62.9% | 79.8% | 0.386 | 70% |
| rom | large array (5,000-40,000 mm2) | 972 | 0 | 25.2% | 63.9% | 0.319 | 69% |
| rom | wafer (>=40,000 mm2) | 2,104 | 0 | 29.7% | 74.8% | 0.374 | 77% |

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
| MiMo-V2.6-Flash | 1 | 55,420 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 0.413846 | 13,363.9 | compute | `MiMo-V2.6-Flash/a100_sxm_80gb-x67-tensor` | 11.880056 | 10,921.1 | link_latency | 28.71x |
| MiMo-V2.6-Flash | 2 | 55,420 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 0.220809 | 13,363.9 | compute | `MiMo-V2.6-Flash/a100_sxm_80gb-x67-tensor` | 6.869702 | 11,220.2 | link_latency | 31.11x |
| MiMo-V2.6-Flash | 4 | 55,420 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 0.124291 | 13,363.9 | compute | `MiMo-V2.6-Flash/a100_sxm_80gb-x67-tensor` | 4.342779 | 11,628.3 | link_latency | 34.94x |
| MiMo-V2.6-Flash | 8 | 55,420 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 0.076032 | 13,363.9 | compute | `MiMo-V2.6-Flash/a100_sxm_80gb-x67-hybrid` | 3.248838 | 17,478.5 | weight_read | 39.97x |
| MiMo-V2.6-Flash | 16 | 55,420 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68` | 0.051902 | 13,363.9 | compute | `MiMo-V2.6-Flash/a100_sxm_80gb-x67-hybrid` | 2.144447 | 18,108.7 | weight_read | 41.32x |
| MiMo-V2.6-Flash | 32 | 92,095 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x113-romfill` | 0.049828 | 22,875.1 | weight_read | `MiMo-V2.6-Flash/a100_sxm_80gb-x111-hybrid` | 1.907873 | 30,166.9 | weight_read | 38.29x |
| MiMo-V2.6-Flash | 64 | 185,005 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill` | 0.050285 | 45,367.3 | weight_read | `MiMo-V2.6-Flash/a100_sxm_80gb-x224-hybrid` | 1.929983 | 60,268.1 | weight_read | 37.08x |
| MiMo-V2.6-Flash | 256 | 277,100 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill` | 0.045298 | 72,771.1 | compute | `MiMo-V2.6-Flash/a100_sxm_80gb-x335-expert` | 0.702129 | 55,855.7 | weight_read | 15.50x |
| MiMo-V2.6-Flash | 1024 | 277,100 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.043343 | 77,544.2 | compute | `MiMo-V2.6-Flash/a100_sxm_80gb-x335-expert` | 0.241665 | 58,615.0 | weight_read | 5.58x |
| MiMo-V2.6-Flash | 4096 | 277,100 | `MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill` | 0.042282 | 76,883.6 | compute | `MiMo-V2.6-Flash/a100_sxm_80gb-x335-expert` | 0.126533 | 62,926.1 | link_latency | 2.99x |

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
| MiMo-V2.6-Flash | 8,192 | 309 B | 172.9 GB | 4.48 | 0.214 GB | 0.214 GB | 59.1 |

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
| MiMo-V2.6-Flash | 1 | 46,225 | 38,474.2 | wafer-pipeline | 4,880.0 | wafer-tensor | 7.88x | 3,730.0 | pipeline | 902.8 | tensor | 4.13x | 10.31x | 5.41x | 0.52x |
| MiMo-V2.6-Flash | 2 | 92,450 | 41,220.0 | wafer-pipeline | 4,743.0 | wafer-hybrid | 8.69x | 5,039.5 | pipeline | 957.2 | tensor | 5.27x | 8.18x | 4.96x | 0.61x |
| MiMo-V2.6-Flash | 3 | 138,675 | 45,992.2 | wafer-pipeline | 4,740.7 | wafer-hybrid | 9.70x | 5,707.4 | pipeline | 976.8 | tensor | 5.84x | 8.06x | 4.85x | 0.60x |
| MiMo-V2.6-Flash | 4 | 184,900 | 48,818.2 | wafer-pipeline | 4,738.4 | wafer-hybrid | 10.30x | 6,112.5 | pipeline | 986.9 | tensor | 6.19x | 7.99x | 4.80x | 0.60x |
| MiMo-V2.6-Flash | 6 | 277,350 | 52,014.1 | wafer-pipeline | 4,733.9 | wafer-hybrid | 10.99x | 6,579.4 | pipeline | 718.1 | tensor | 9.16x | 7.91x | 6.59x | 0.83x |
| MiMo-V2.6-Flash | 8 | 369,800 | 53,774.3 | wafer-pipeline | 4,729.3 | wafer-hybrid | 11.37x | 6,840.7 | pipeline | 720.8 | tensor | 9.49x | 7.86x | 6.56x | 0.83x |
| MiMo-V2.6-Flash | 12 | 554,700 | 55,657.8 | wafer-pipeline | 4,720.3 | wafer-hybrid | 11.79x | 7,123.6 | pipeline | 723.5 | tensor | 9.85x | 7.81x | 6.52x | 0.83x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.52x to 0.83x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Flash | 1 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 15,571.9 | 264,722.1 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x67-tensor | 55,342 | 1.00x | tensor | 960.53 | 919.3 | 919.3 | link_latency | 16.94x | 31.34x | 123.50x | 16.94x |
| MiMo-V2.6-Flash | 1 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x38 | 30,970 | 9,042.2 | 9,042.2 | link_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x37-tensor | 30,562 | 1.01x | tensor | 952.14 | 851.9 | 851.9 | link_latency | 10.61x | 1.93x | 71.46x | 10.61x |
| MiMo-V2.6-Flash | 2 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 15,571.9 | 264,722.1 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x67-tensor | 55,342 | 1.00x | tensor | 1,051.29 | 816.6 | 1,633.3 | link_latency | 19.07x | 31.34x | 123.50x | 19.07x |
| MiMo-V2.6-Flash | 2 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x42 | 34,230 | 7,911.5 | 15,823.1 | link_latency | MiMo-V2.6-Flash/a100_sxm_80gb-x41-tensor | 33,866 | 1.01x | tensor | 1,040.81 | 759.3 | 1,518.6 | link_latency | 10.42x | 3.05x | 62.61x | 10.42x |
| MiMo-V2.6-Flash | 4 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 15,571.9 | 264,722.1 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x67-tensor | 55,342 | 1.00x | tensor | 1,232.83 | 669.4 | 2,677.6 | link_latency | 23.26x | 31.34x | 123.50x | 23.26x |
| MiMo-V2.6-Flash | 4 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x42 | 34,230 | 5,659.9 | 22,639.5 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x41-tensor | 33,866 | 1.01x | tensor | 1,211.86 | 612.9 | 2,451.6 | link_latency | 9.23x | 4.37x | 44.79x | 9.23x |
| MiMo-V2.6-Flash | 8 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 15,571.9 | 264,722.1 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x67-hybrid | 55,342 | 1.00x | hybrid | 505.74 | 639.1 | 5,752.1 | weight_read | 24.36x | 31.34x | 123.50x | 24.36x |
| MiMo-V2.6-Flash | 8 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x42 | 34,230 | 3,665.3 | 40,317.8 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x41-hybrid | 33,866 | 1.01x | hybrid | 501.51 | 553.8 | 4,430.1 | weight_read | 6.62x | 7.78x | 29.00x | 6.62x |
| MiMo-V2.6-Flash | 16 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 15,571.9 | 264,722.1 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x67-hybrid | 55,342 | 1.00x | hybrid | 513.13 | 527.8 | 8,444.4 | weight_read | 29.50x | 31.34x | 123.50x | 29.50x |
| MiMo-V2.6-Flash | 16 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x42 | 34,230 | 2,560.2 | 40,963.1 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x41-hybrid | 33,866 | 1.01x | hybrid | 512.87 | 415.1 | 6,642.3 | weight_read | 6.17x | 6.17x | 20.26x | 6.17x |
| MiMo-V2.6-Flash | 32 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x156-romfill | 127,140 | 14,861.9 | 579,612.8 | weight_read | MiMo-V2.6-Flash/a100_sxm_80gb-x154-hybrid | 127,204 | 1.00x | hybrid | 539.54 | 554.0 | 17,728.7 | weight_read | 26.83x | 29.85x | 117.87x | 26.83x |
| MiMo-V2.6-Flash | 32 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x42 | 34,230 | 1,303.0 | 41,697.2 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x41-hybrid | 33,866 | 1.01x | hybrid | 535.59 | 282.1 | 9,025.9 | weight_read | 4.62x | 4.62x | 10.31x | 4.62x |
| MiMo-V2.6-Flash | 64 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 14,656.9 | 1,245,836.3 | weight_read | MiMo-V2.6-Flash/a100_sxm_80gb-x335-hybrid | 276,710 | 1.00x | hybrid | 594.19 | 559.6 | 35,817.4 | weight_read | 26.19x | 29.49x | 116.24x | 26.19x |
| MiMo-V2.6-Flash | 64 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x42 | 34,230 | 659.3 | 42,193.0 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x41-hybrid | 33,866 | 1.01x | hybrid | 581.03 | 179.6 | 11,497.3 | weight_read | 3.67x | 3.67x | 6.36x | 3.67x |
| MiMo-V2.6-Flash | 256 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,275.3 | 1,606,480.6 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x335-expert | 276,710 | 1.00x | expert | 910.16 | 310.7 | 79,551.9 | weight_read | 20.19x | 20.19x | 49.77x | 20.19x |
| MiMo-V2.6-Flash | 256 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x42 | 34,230 | 165.8 | 42,447.9 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x41-expert | 33,866 | 1.01x | expert | 2,598.53 | 116.2 | 29,742.6 | weight_read | 1.43x | 1.43x | 3.83x | 1.43x |
| MiMo-V2.6-Flash | 1024 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 1,747.1 | 1,789,068.0 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x335-expert | 276,710 | 1.00x | expert | 1,615.99 | 236.9 | 242,546.3 | weight_read | 7.38x | 7.38x | 24.75x | 7.38x |
| MiMo-V2.6-Flash | 1024 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x42 | 34,230 | 41.5 | 42,512.1 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x41-expert | 33,866 | 1.01x | expert | 8,369.48 | 59.5 | 60,908.1 | link_latency | 0.70x | 0.70x | 2.55x | 0.70x |
| MiMo-V2.6-Flash | 4096 | fastest | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 443.9 | 1,818,359.1 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x335-expert | 276,710 | 1.00x | expert | 4,439.33 | 121.4 | 497,309.3 | link_latency | 3.66x | 3.66x | 16.74x | 3.66x |
| MiMo-V2.6-Flash | 4096 | smallest silicon | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x42 | 34,230 | 10.4 | 42,528.2 | compute | MiMo-V2.6-Flash/a100_sxm_80gb-x41-hybrid | 33,866 | 1.01x | hybrid | 6,306.25 | 29.2 | 119,682.0 | compute | 0.36x | 0.36x | 1.16x | 0.36x |

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
| MiMo-V2.6-Flash | 15 | 12,390 | 127.4 | 687.4 | 649.2 | tensor | 923.83 | 63.5% | link_latency |
| MiMo-V2.6-Flash | 19 | 15,694 | 127.3 | 734.7 | 576.6 | tensor | 939.56 | 69.0% | link_latency |
| MiMo-V2.6-Flash | 20 | 16,520 | 127.2 | 746.0 | 597.8 | tensor | 939.56 | 70.1% | link_latency |
| MiMo-V2.6-Flash | 21 | 17,346 | 127.2 | 756.5 | 618.4 | tensor | 939.56 | 71.1% | link_latency |
| MiMo-V2.6-Flash | 22 | 18,172 | 127.1 | 766.3 | 638.4 | tensor | 939.56 | 72.0% | link_latency |
| MiMo-V2.6-Flash | 24 | 19,824 | 127.1 | 784.0 | 676.7 | tensor | 939.56 | 73.7% | link_latency |
| MiMo-V2.6-Flash | 34 | 28,084 | 126.6 | 838.6 | 604.4 | tensor | 952.14 | 79.8% | link_latency |
| MiMo-V2.6-Flash | 37 | 30,562 | 126.5 | 851.9 | 640.4 | tensor | 952.14 | 81.1% | link_latency |
| MiMo-V2.6-Flash | 41 | 33,866 | 126.4 | 864.7 | 605.6 | tensor | 955.28 | 82.6% | link_latency |
| MiMo-V2.6-Flash | 42 | 34,692 | 126.3 | 868.1 | 615.7 | tensor | 955.28 | 82.9% | link_latency |
| MiMo-V2.6-Flash | 43 | 35,518 | 126.3 | 871.4 | 625.7 | tensor | 955.28 | 83.2% | link_latency |
| MiMo-V2.6-Flash | 44 | 36,344 | 126.2 | 874.6 | 635.5 | tensor | 955.28 | 83.5% | link_latency |
| MiMo-V2.6-Flash | 48 | 39,648 | 126.1 | 886.0 | 673.5 | tensor | 955.28 | 84.6% | link_latency |
| MiMo-V2.6-Flash | 53 | 43,778 | 126.1 | 896.4 | 648.4 | tensor | 957.53 | 85.8% | link_latency |
| MiMo-V2.6-Flash | 55 | 45,430 | 126.1 | 900.7 | 664.5 | tensor | 957.53 | 86.2% | link_latency |
| MiMo-V2.6-Flash | 56 | 46,256 | 126.1 | 902.8 | 672.4 | tensor | 957.53 | 86.4% | link_latency |
| MiMo-V2.6-Flash | 58 | 47,908 | 126.1 | 905.3 | 628.8 | tensor | 959.22 | 86.8% | link_latency |
| MiMo-V2.6-Flash | 67 | 55,342 | 126.1 | 919.3 | 639.1 | tensor | 960.53 | 88.3% | link_latency |
| MiMo-V2.6-Flash | 71 | 58,646 | 126.1 | 924.9 | 664.2 | tensor | 960.53 | 88.8% | link_latency |
| MiMo-V2.6-Flash | 77 | 63,602 | 126.1 | 931.3 | 652.7 | tensor | 961.58 | 89.6% | link_latency |
| MiMo-V2.6-Flash | 107 | 88,382 | 126.1 | 954.2 | 645.5 | tensor | 964.27 | 92.0% | link_latency |
| MiMo-V2.6-Flash | 111 | 91,686 | 126.1 | 956.6 | 661.2 | tensor | 964.27 | 92.2% | link_latency |
| MiMo-V2.6-Flash | 112 | 92,512 | 126.1 | 957.2 | 665.1 | tensor | 964.27 | 92.3% | link_latency |
| MiMo-V2.6-Flash | 115 | 94,990 | 126.1 | 958.4 | 645.8 | tensor | 964.72 | 92.5% | link_latency |
| MiMo-V2.6-Flash | 142 | 117,292 | 126.1 | 969.4 | 655.0 | tensor | 965.77 | 93.6% | link_latency |
| MiMo-V2.6-Flash | 154 | 127,204 | 126.1 | 973.0 | 642.8 | tensor | 966.29 | 94.0% | link_latency |
| MiMo-V2.6-Flash | 168 | 138,768 | 126.1 | 976.8 | 657.8 | tensor | 966.52 | 94.4% | link_latency |
| MiMo-V2.6-Flash | 224 | 185,024 | 126.1 | 986.9 | 650.8 | tensor | 967.64 | 95.5% | link_latency |
| MiMo-V2.6-Flash | 335 | 276,710 | 126.1 | 718.1 | 635.9 | tensor | 1,358.53 | 97.5% | link_latency |
| MiMo-V2.6-Flash | 336 | 277,536 | 126.1 | 718.1 | 637.1 | tensor | 1,358.53 | 97.6% | link_latency |
| MiMo-V2.6-Flash | 448 | 370,048 | 126.1 | 720.8 | 631.4 | tensor | 1,359.09 | 98.0% | link_latency |
| MiMo-V2.6-Flash | 672 | 555,072 | 126.1 | 723.5 | 631.4 | tensor | 1,359.65 | 98.4% | link_latency |

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
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x43 | MiMo-V2.6-Flash | 43 | pipeline | rom_package_ucie | rom_board_serdes | 42 | 1.43 us | 69,878.9 tok/s | 698,789.0 tok/s | 32 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.39 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x43 | MiMo-V2.6-Flash | 43 | tensor | rom_package_ucie | rom_board_serdes | 192 | 66.91 us | 1,494.5 tok/s | 14,944.6 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 96 x all_reduce span 11 on rom_board_serdes (traversals 6.6) = 64.55 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x44 | MiMo-V2.6-Flash | 44 | hybrid | rom_package_ucie | rom_board_serdes | 106 | 3.41 us | 29,343.8 tok/s | 293,437.6 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 10 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.05 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x43 | MiMo-V2.6-Flash | 43 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | MiMo-V2.6-Flash | 1 | pipeline | on_wafer | rom_wafer_serdes | 47 | 5.88 us | 17,021.2 tok/s | 170,212.3 tok/s | 47 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.88 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-tensor-x38 | MiMo-V2.6-Flash | 38 | tensor | nvlink3 | infiniband_hdr | 192 | 952.14 us | 105.0 tok/s | 1,050.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 465.26 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | MiMo-V2.6-Flash | 1 | tensor | on_wafer | rom_wafer_serdes | 96 | 184.80 us | 541.1 tok/s | 5,411.3 tok/s | 96 x all_reduce span 57 on on_wafer (traversals 15.4) = 184.80 us |
| MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hybrid-x43 | MiMo-V2.6-Flash | 43 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x68 | MiMo-V2.6-Flash | 68 | pipeline | rom_package_ucie | rom_board_serdes | 47 | 1.58 us | 63,139.7 tok/s | 631,396.8 tok/s | 36 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.43 us; 11 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.15 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x56 | MiMo-V2.6-Flash | 56 | tensor | rom_package_ucie | rom_board_serdes | 192 | 66.94 us | 1,493.9 tok/s | 14,938.9 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 96 x all_reduce span 14 on rom_board_serdes (traversals 6.6) = 64.58 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | MiMo-V2.6-Flash | 68 | hybrid | rom_package_ucie | rom_board_serdes | 112 | 4.04 us | 24,782.0 tok/s | 247,820.1 tok/s | 96 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 2.36 us; 16 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.67 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-pipeline-x68 | MiMo-V2.6-Flash | 68 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2 | MiMo-V2.6-Flash | 2 | pipeline | on_wafer | rom_wafer_serdes | 47 | 5.88 us | 17,021.2 tok/s | 170,212.3 tok/s | 47 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.88 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-tensor-x42 | MiMo-V2.6-Flash | 42 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-tensor-x2 | MiMo-V2.6-Flash | 2 | tensor | on_wafer | rom_wafer_serdes | 192 | 206.12 us | 485.2 tok/s | 4,851.6 tok/s | 96 x all_reduce span 57 on on_wafer (traversals 15.4) = 184.80 us; 96 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 21.32 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hybrid-x54 | MiMo-V2.6-Flash | 54 | hybrid | nvlink3 | infiniband_hdr | 102 | 501.03 us | 199.6 tok/s | 1,995.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | MiMo-V2.6-Flash | 2 | hybrid | on_wafer | rom_wafer_serdes | 97 | 184.90 us | 540.8 tok/s | 5,408.3 tok/s | 96 x all_reduce span 57 on on_wafer (traversals 15.4) = 184.80 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x15-pipeline | MiMo-V2.6-Flash | 15 | pipeline | nvlink3 | infiniband_hdr | 14 | 35.21 us | 2,839.9 tok/s | 28,398.9 tok/s | 13 x point_to_point span 2 on nvlink3 (traversals 1.0) = 32.85 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x15-tensor | MiMo-V2.6-Flash | 15 | tensor | nvlink3 | infiniband_hdr | 192 | 923.83 us | 108.2 tok/s | 1,082.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 2 on infiniband_hdr (traversals 2.0) = 436.95 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x15-hybrid | MiMo-V2.6-Flash | 15 | hybrid | nvlink3 | infiniband_hdr | 97 | 489.24 us | 204.4 tok/s | 2,044.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 1 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 2.36 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x15-expert | MiMo-V2.6-Flash | 15 | expert | nvlink3 | infiniband_hdr | 192 | 698.54 us | 143.2 tok/s | 1,431.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 211.66 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x19-pipeline | MiMo-V2.6-Flash | 19 | pipeline | nvlink3 | infiniband_hdr | 18 | 45.15 us | 2,214.7 tok/s | 22,147.3 tok/s | 16 x point_to_point span 2 on nvlink3 (traversals 1.0) = 40.44 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x19-tensor | MiMo-V2.6-Flash | 19 | tensor | nvlink3 | infiniband_hdr | 192 | 939.56 us | 106.4 tok/s | 1,064.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 452.67 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x19-hybrid | MiMo-V2.6-Flash | 19 | hybrid | nvlink3 | infiniband_hdr | 98 | 491.60 us | 203.4 tok/s | 2,034.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x19-expert | MiMo-V2.6-Flash | 19 | expert | nvlink3 | infiniband_hdr | 192 | 691.57 us | 144.6 tok/s | 1,446.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 483.44 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 208.13 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x20-pipeline | MiMo-V2.6-Flash | 20 | pipeline | nvlink3 | infiniband_hdr | 19 | 47.68 us | 2,097.3 tok/s | 20,973.3 tok/s | 17 x point_to_point span 2 on nvlink3 (traversals 1.0) = 42.96 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x20-tensor | MiMo-V2.6-Flash | 20 | tensor | nvlink3 | infiniband_hdr | 192 | 939.56 us | 106.4 tok/s | 1,064.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 452.67 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x20-hybrid | MiMo-V2.6-Flash | 20 | hybrid | nvlink3 | infiniband_hdr | 98 | 491.60 us | 203.4 tok/s | 2,034.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x20-expert | MiMo-V2.6-Flash | 20 | expert | nvlink3 | infiniband_hdr | 192 | 690.90 us | 144.7 tok/s | 1,447.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 483.44 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 207.46 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x21-pipeline | MiMo-V2.6-Flash | 21 | pipeline | nvlink3 | infiniband_hdr | 20 | 50.21 us | 1,991.8 tok/s | 19,917.6 tok/s | 18 x point_to_point span 2 on nvlink3 (traversals 1.0) = 45.49 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x21-tensor | MiMo-V2.6-Flash | 21 | tensor | nvlink3 | infiniband_hdr | 192 | 939.56 us | 106.4 tok/s | 1,064.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 452.67 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x21-hybrid | MiMo-V2.6-Flash | 21 | hybrid | nvlink3 | infiniband_hdr | 98 | 491.60 us | 203.4 tok/s | 2,034.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x21-expert | MiMo-V2.6-Flash | 21 | expert | nvlink3 | infiniband_hdr | 192 | 690.30 us | 144.9 tok/s | 1,448.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 483.44 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 206.86 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x22-pipeline | MiMo-V2.6-Flash | 22 | pipeline | nvlink3 | infiniband_hdr | 21 | 52.73 us | 1,896.3 tok/s | 18,963.0 tok/s | 19 x point_to_point span 2 on nvlink3 (traversals 1.0) = 48.02 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x22-tensor | MiMo-V2.6-Flash | 22 | tensor | nvlink3 | infiniband_hdr | 192 | 939.56 us | 106.4 tok/s | 1,064.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 452.67 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x22-hybrid | MiMo-V2.6-Flash | 22 | hybrid | nvlink3 | infiniband_hdr | 98 | 491.60 us | 203.4 tok/s | 2,034.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x22-expert | MiMo-V2.6-Flash | 22 | expert | nvlink3 | infiniband_hdr | 192 | 689.76 us | 145.0 tok/s | 1,449.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 483.44 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 206.32 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x24-pipeline | MiMo-V2.6-Flash | 24 | pipeline | nvlink3 | infiniband_hdr | 23 | 57.79 us | 1,730.4 tok/s | 17,304.4 tok/s | 21 x point_to_point span 2 on nvlink3 (traversals 1.0) = 53.07 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x24-tensor | MiMo-V2.6-Flash | 24 | tensor | nvlink3 | infiniband_hdr | 192 | 939.56 us | 106.4 tok/s | 1,064.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 452.67 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x24-hybrid | MiMo-V2.6-Flash | 24 | hybrid | nvlink3 | infiniband_hdr | 98 | 491.60 us | 203.4 tok/s | 2,034.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 4.72 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x24-expert | MiMo-V2.6-Flash | 24 | expert | nvlink3 | infiniband_hdr | 192 | 687.66 us | 145.4 tok/s | 1,454.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 482.29 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 205.37 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x34-pipeline | MiMo-V2.6-Flash | 34 | pipeline | nvlink3 | infiniband_hdr | 33 | 82.72 us | 1,208.9 tok/s | 12,088.6 tok/s | 29 x point_to_point span 2 on nvlink3 (traversals 1.0) = 73.29 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x34-tensor | MiMo-V2.6-Flash | 34 | tensor | nvlink3 | infiniband_hdr | 192 | 952.14 us | 105.0 tok/s | 1,050.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 465.26 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x34-hybrid | MiMo-V2.6-Flash | 34 | hybrid | nvlink3 | infiniband_hdr | 100 | 496.31 us | 201.5 tok/s | 2,014.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x34-expert | MiMo-V2.6-Flash | 34 | expert | nvlink3 | infiniband_hdr | 192 | 684.00 us | 146.2 tok/s | 1,462.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.72 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 202.28 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x37-pipeline | MiMo-V2.6-Flash | 37 | pipeline | nvlink3 | infiniband_hdr | 36 | 90.30 us | 1,107.4 tok/s | 11,073.6 tok/s | 32 x point_to_point span 2 on nvlink3 (traversals 1.0) = 80.87 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x37-tensor | MiMo-V2.6-Flash | 37 | tensor | nvlink3 | infiniband_hdr | 192 | 952.14 us | 105.0 tok/s | 1,050.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 465.26 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x37-hybrid | MiMo-V2.6-Flash | 37 | hybrid | nvlink3 | infiniband_hdr | 100 | 496.31 us | 201.5 tok/s | 2,014.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x37-expert | MiMo-V2.6-Flash | 37 | expert | nvlink3 | infiniband_hdr | 192 | 683.40 us | 146.3 tok/s | 1,463.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.72 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 201.68 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x41-pipeline | MiMo-V2.6-Flash | 41 | pipeline | nvlink3 | infiniband_hdr | 40 | 100.24 us | 997.6 tok/s | 9,975.6 tok/s | 35 x point_to_point span 2 on nvlink3 (traversals 1.0) = 88.46 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x41-tensor | MiMo-V2.6-Flash | 41 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x41-hybrid | MiMo-V2.6-Flash | 41 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x41-expert | MiMo-V2.6-Flash | 41 | expert | nvlink3 | infiniband_hdr | 192 | 682.39 us | 146.5 tok/s | 1,465.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.38 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 201.02 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x42-pipeline | MiMo-V2.6-Flash | 42 | pipeline | nvlink3 | infiniband_hdr | 41 | 102.77 us | 973.0 tok/s | 9,730.3 tok/s | 36 x point_to_point span 2 on nvlink3 (traversals 1.0) = 90.98 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x42-tensor | MiMo-V2.6-Flash | 42 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x42-hybrid | MiMo-V2.6-Flash | 42 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x42-expert | MiMo-V2.6-Flash | 42 | expert | nvlink3 | infiniband_hdr | 192 | 682.25 us | 146.6 tok/s | 1,465.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.38 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 200.87 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x43-pipeline | MiMo-V2.6-Flash | 43 | pipeline | nvlink3 | infiniband_hdr | 42 | 105.30 us | 949.7 tok/s | 9,496.8 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x43-tensor | MiMo-V2.6-Flash | 43 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x43-hybrid | MiMo-V2.6-Flash | 43 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x43-expert | MiMo-V2.6-Flash | 43 | expert | nvlink3 | infiniband_hdr | 192 | 682.11 us | 146.6 tok/s | 1,466.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.38 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 200.73 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x44-pipeline | MiMo-V2.6-Flash | 44 | pipeline | nvlink3 | infiniband_hdr | 43 | 107.83 us | 927.4 tok/s | 9,274.2 tok/s | 38 x point_to_point span 2 on nvlink3 (traversals 1.0) = 96.04 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x44-tensor | MiMo-V2.6-Flash | 44 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x44-hybrid | MiMo-V2.6-Flash | 44 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x44-expert | MiMo-V2.6-Flash | 44 | expert | nvlink3 | infiniband_hdr | 192 | 681.98 us | 146.6 tok/s | 1,466.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.38 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 200.60 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x48-pipeline | MiMo-V2.6-Flash | 48 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x48-tensor | MiMo-V2.6-Flash | 48 | tensor | nvlink3 | infiniband_hdr | 192 | 955.28 us | 104.7 tok/s | 1,046.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 468.40 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x48-hybrid | MiMo-V2.6-Flash | 48 | hybrid | nvlink3 | infiniband_hdr | 101 | 498.67 us | 200.5 tok/s | 2,005.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x48-expert | MiMo-V2.6-Flash | 48 | expert | nvlink3 | infiniband_hdr | 192 | 681.27 us | 146.8 tok/s | 1,467.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.15 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 200.12 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x53-pipeline | MiMo-V2.6-Flash | 53 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x53-tensor | MiMo-V2.6-Flash | 53 | tensor | nvlink3 | infiniband_hdr | 192 | 957.53 us | 104.4 tok/s | 1,044.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 470.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x53-hybrid | MiMo-V2.6-Flash | 53 | hybrid | nvlink3 | infiniband_hdr | 102 | 501.03 us | 199.6 tok/s | 1,995.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x53-expert | MiMo-V2.6-Flash | 53 | expert | nvlink3 | infiniband_hdr | 192 | 680.78 us | 146.9 tok/s | 1,468.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.15 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 199.63 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x55-pipeline | MiMo-V2.6-Flash | 55 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x55-tensor | MiMo-V2.6-Flash | 55 | tensor | nvlink3 | infiniband_hdr | 192 | 957.53 us | 104.4 tok/s | 1,044.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 470.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x55-hybrid | MiMo-V2.6-Flash | 55 | hybrid | nvlink3 | infiniband_hdr | 102 | 501.03 us | 199.6 tok/s | 1,995.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x55-expert | MiMo-V2.6-Flash | 55 | expert | nvlink3 | infiniband_hdr | 192 | 680.60 us | 146.9 tok/s | 1,469.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 481.15 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 199.46 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x56-pipeline | MiMo-V2.6-Flash | 56 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x56-tensor | MiMo-V2.6-Flash | 56 | tensor | nvlink3 | infiniband_hdr | 192 | 957.53 us | 104.4 tok/s | 1,044.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 470.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x56-hybrid | MiMo-V2.6-Flash | 56 | hybrid | nvlink3 | infiniband_hdr | 102 | 501.03 us | 199.6 tok/s | 1,995.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x56-expert | MiMo-V2.6-Flash | 56 | expert | nvlink3 | infiniband_hdr | 192 | 680.36 us | 147.0 tok/s | 1,469.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.98 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 199.37 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x58-pipeline | MiMo-V2.6-Flash | 58 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x58-tensor | MiMo-V2.6-Flash | 58 | tensor | nvlink3 | infiniband_hdr | 192 | 959.22 us | 104.3 tok/s | 1,042.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 472.34 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x58-hybrid | MiMo-V2.6-Flash | 58 | hybrid | nvlink3 | infiniband_hdr | 103 | 503.39 us | 198.7 tok/s | 1,986.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 16.50 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x58-expert | MiMo-V2.6-Flash | 58 | expert | nvlink3 | infiniband_hdr | 192 | 680.20 us | 147.0 tok/s | 1,470.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.98 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 199.22 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x67-pipeline | MiMo-V2.6-Flash | 67 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x67-tensor | MiMo-V2.6-Flash | 67 | tensor | nvlink3 | infiniband_hdr | 192 | 960.53 us | 104.1 tok/s | 1,041.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 473.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x67-hybrid | MiMo-V2.6-Flash | 67 | hybrid | nvlink3 | infiniband_hdr | 104 | 505.74 us | 197.7 tok/s | 1,977.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x67-expert | MiMo-V2.6-Flash | 67 | expert | nvlink3 | infiniband_hdr | 192 | 679.50 us | 147.2 tok/s | 1,471.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.86 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.64 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x71-pipeline | MiMo-V2.6-Flash | 71 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x71-tensor | MiMo-V2.6-Flash | 71 | tensor | nvlink3 | infiniband_hdr | 192 | 960.53 us | 104.1 tok/s | 1,041.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 473.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x71-hybrid | MiMo-V2.6-Flash | 71 | hybrid | nvlink3 | infiniband_hdr | 104 | 505.74 us | 197.7 tok/s | 1,977.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 18.86 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x71-expert | MiMo-V2.6-Flash | 71 | expert | nvlink3 | infiniband_hdr | 192 | 679.28 us | 147.2 tok/s | 1,472.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.86 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.42 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x77-pipeline | MiMo-V2.6-Flash | 77 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x77-tensor | MiMo-V2.6-Flash | 77 | tensor | nvlink3 | infiniband_hdr | 192 | 961.58 us | 104.0 tok/s | 1,040.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 474.69 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x77-hybrid | MiMo-V2.6-Flash | 77 | hybrid | nvlink3 | infiniband_hdr | 105 | 508.10 us | 196.8 tok/s | 1,968.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x77-expert | MiMo-V2.6-Flash | 77 | expert | nvlink3 | infiniband_hdr | 192 | 678.91 us | 147.3 tok/s | 1,472.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.76 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 198.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x107-pipeline | MiMo-V2.6-Flash | 107 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x107-tensor | MiMo-V2.6-Flash | 107 | tensor | nvlink3 | infiniband_hdr | 192 | 964.27 us | 103.7 tok/s | 1,037.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 477.39 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x107-hybrid | MiMo-V2.6-Flash | 107 | hybrid | nvlink3 | infiniband_hdr | 109 | 517.53 us | 193.2 tok/s | 1,932.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x107-expert | MiMo-V2.6-Flash | 107 | expert | nvlink3 | infiniband_hdr | 192 | 677.76 us | 147.5 tok/s | 1,475.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.53 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.23 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x111-pipeline | MiMo-V2.6-Flash | 111 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x111-tensor | MiMo-V2.6-Flash | 111 | tensor | nvlink3 | infiniband_hdr | 192 | 964.27 us | 103.7 tok/s | 1,037.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 477.39 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x111-hybrid | MiMo-V2.6-Flash | 111 | hybrid | nvlink3 | infiniband_hdr | 109 | 517.53 us | 193.2 tok/s | 1,932.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x111-expert | MiMo-V2.6-Flash | 111 | expert | nvlink3 | infiniband_hdr | 192 | 677.68 us | 147.6 tok/s | 1,475.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.53 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x112-pipeline | MiMo-V2.6-Flash | 112 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x112-tensor | MiMo-V2.6-Flash | 112 | tensor | nvlink3 | infiniband_hdr | 192 | 964.27 us | 103.7 tok/s | 1,037.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 477.39 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x112-hybrid | MiMo-V2.6-Flash | 112 | hybrid | nvlink3 | infiniband_hdr | 109 | 517.53 us | 193.2 tok/s | 1,932.3 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x112-expert | MiMo-V2.6-Flash | 112 | expert | nvlink3 | infiniband_hdr | 192 | 677.62 us | 147.6 tok/s | 1,475.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.49 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.13 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x115-pipeline | MiMo-V2.6-Flash | 115 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x115-tensor | MiMo-V2.6-Flash | 115 | tensor | nvlink3 | infiniband_hdr | 192 | 964.72 us | 103.7 tok/s | 1,036.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 477.84 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x115-hybrid | MiMo-V2.6-Flash | 115 | hybrid | nvlink3 | infiniband_hdr | 110 | 519.89 us | 192.3 tok/s | 1,923.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.01 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x115-expert | MiMo-V2.6-Flash | 115 | expert | nvlink3 | infiniband_hdr | 192 | 677.56 us | 147.6 tok/s | 1,475.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.49 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.07 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x142-pipeline | MiMo-V2.6-Flash | 142 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x142-tensor | MiMo-V2.6-Flash | 142 | tensor | nvlink3 | infiniband_hdr | 192 | 965.77 us | 103.5 tok/s | 1,035.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 478.89 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x142-hybrid | MiMo-V2.6-Flash | 142 | hybrid | nvlink3 | infiniband_hdr | 113 | 526.96 us | 189.8 tok/s | 1,897.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.08 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x142-expert | MiMo-V2.6-Flash | 142 | expert | nvlink3 | infiniband_hdr | 192 | 677.06 us | 147.7 tok/s | 1,477.0 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.40 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.65 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x154-pipeline | MiMo-V2.6-Flash | 154 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x154-tensor | MiMo-V2.6-Flash | 154 | tensor | nvlink3 | infiniband_hdr | 192 | 966.29 us | 103.5 tok/s | 1,034.9 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 479.41 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x154-hybrid | MiMo-V2.6-Flash | 154 | hybrid | nvlink3 | infiniband_hdr | 115 | 531.68 us | 188.1 tok/s | 1,880.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 44.80 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x154-expert | MiMo-V2.6-Flash | 154 | expert | nvlink3 | infiniband_hdr | 192 | 676.88 us | 147.7 tok/s | 1,477.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.36 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.51 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x168-pipeline | MiMo-V2.6-Flash | 168 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x168-tensor | MiMo-V2.6-Flash | 168 | tensor | nvlink3 | infiniband_hdr | 192 | 966.52 us | 103.5 tok/s | 1,034.6 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 479.64 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x168-hybrid | MiMo-V2.6-Flash | 168 | hybrid | nvlink3 | infiniband_hdr | 116 | 534.03 us | 187.3 tok/s | 1,872.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.15 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x168-expert | MiMo-V2.6-Flash | 168 | expert | nvlink3 | infiniband_hdr | 192 | 676.71 us | 147.8 tok/s | 1,477.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.33 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.38 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x224-pipeline | MiMo-V2.6-Flash | 224 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x224-tensor | MiMo-V2.6-Flash | 224 | tensor | nvlink3 | infiniband_hdr | 192 | 967.64 us | 103.3 tok/s | 1,033.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 480.76 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x224-hybrid | MiMo-V2.6-Flash | 224 | hybrid | nvlink3 | infiniband_hdr | 123 | 550.54 us | 181.6 tok/s | 1,816.4 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.66 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x224-expert | MiMo-V2.6-Flash | 224 | expert | nvlink3 | infiniband_hdr | 192 | 676.25 us | 147.9 tok/s | 1,478.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.25 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 196.00 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x335-pipeline | MiMo-V2.6-Flash | 335 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x335-tensor | MiMo-V2.6-Flash | 335 | tensor | nvlink3 | infiniband_hdr | 192 | 1,358.53 us | 73.6 tok/s | 736.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 871.64 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x335-hybrid | MiMo-V2.6-Flash | 335 | hybrid | nvlink3 | infiniband_hdr | 137 | 583.55 us | 171.4 tok/s | 1,713.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x335-expert | MiMo-V2.6-Flash | 335 | expert | nvlink3 | infiniband_hdr | 192 | 675.80 us | 148.0 tok/s | 1,479.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.17 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.63 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x336-pipeline | MiMo-V2.6-Flash | 336 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x336-tensor | MiMo-V2.6-Flash | 336 | tensor | nvlink3 | infiniband_hdr | 192 | 1,358.53 us | 73.6 tok/s | 736.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 871.64 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x336-hybrid | MiMo-V2.6-Flash | 336 | hybrid | nvlink3 | infiniband_hdr | 137 | 583.55 us | 171.4 tok/s | 1,713.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.66 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x336-expert | MiMo-V2.6-Flash | 336 | expert | nvlink3 | infiniband_hdr | 192 | 675.79 us | 148.0 tok/s | 1,479.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.16 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.63 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x448-pipeline | MiMo-V2.6-Flash | 448 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x448-tensor | MiMo-V2.6-Flash | 448 | tensor | nvlink3 | infiniband_hdr | 192 | 1,359.09 us | 73.6 tok/s | 735.8 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 872.21 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x448-hybrid | MiMo-V2.6-Flash | 448 | hybrid | nvlink3 | infiniband_hdr | 143 | 597.69 us | 167.3 tok/s | 1,673.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 110.81 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x448-expert | MiMo-V2.6-Flash | 448 | expert | nvlink3 | infiniband_hdr | 192 | 675.56 us | 148.0 tok/s | 1,480.2 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.12 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.44 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x672-pipeline | MiMo-V2.6-Flash | 672 | pipeline | nvlink3 | infiniband_hdr | 47 | 117.94 us | 847.9 tok/s | 8,479.2 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 106.15 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 11.79 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x672-tensor | MiMo-V2.6-Flash | 672 | tensor | nvlink3 | infiniband_hdr | 192 | 1,359.65 us | 73.5 tok/s | 735.5 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 96 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 872.77 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x672-hybrid | MiMo-V2.6-Flash | 672 | hybrid | nvlink3 | infiniband_hdr | 143 | 597.69 us | 167.3 tok/s | 1,673.1 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 486.88 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 110.81 us |
| MiMo-V2.6-Flash/a100_sxm_80gb-x672-expert | MiMo-V2.6-Flash | 672 | expert | nvlink3 | infiniband_hdr | 192 | 675.34 us | 148.1 tok/s | 1,480.7 tok/s | 96 x all_reduce span 8 on nvlink3 (traversals 2.0) = 480.08 us; 96 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 195.25 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Flash | 1 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 15,571.9 | 0.281 | 15,571.9 (55,420) | 4,880.0 (46,225) | 0.31x | compute |
| MiMo-V2.6-Flash | 2 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 15,571.9 | 0.281 | 15,571.9 (55,420) | 4,743.0 (92,450) | 0.30x | compute |
| MiMo-V2.6-Flash | 4 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 15,571.9 | 0.281 | 15,571.9 (55,420) | 4,630.2 (138,675) | 0.30x | compute |
| MiMo-V2.6-Flash | 8 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 15,571.9 | 0.281 | 15,571.9 (55,420) | 4,623.6 (277,350) | 0.30x | compute |
| MiMo-V2.6-Flash | 16 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x68 | 55,420 | 15,571.9 | 0.281 | 15,571.9 (55,420) | 4,413.8 (369,800) | 0.28x | compute |
| MiMo-V2.6-Flash | 32 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x113-romfill | 92,095 | 14,346.2 | 0.156 | 14,346.2 (92,095) | 4,218.5 (554,700) | 0.29x | weight_read |
| MiMo-V2.6-Flash | 64 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x227-romfill | 185,005 | 14,096.9 | 0.076 | 14,096.9 (185,005) | 3,605.3 (554,700) | 0.26x | weight_read |
| MiMo-V2.6-Flash | 256 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 6,275.3 | 0.023 | 6,275.3 (277,100) | 1,925.8 (554,700) | 0.31x | compute |
| MiMo-V2.6-Flash | 1024 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 1,747.1 | 0.006 | 1,747.1 (277,100) | 766.0 (554,700) | 0.44x | compute |
| MiMo-V2.6-Flash | 4096 | array | array | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 443.9 | 0.002 | 443.9 (277,100) | 193.3 (554,700) | 0.44x | compute |

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
| MiMo-V2.6-Flash | 256 | 628.4 MB | 137.8 mm2 | 24.81 mm2 (18.0%) | 35,280 mm2 | 6,350 mm2 | 37,926 mm2 = 46.5 reticles |

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
| MiMo-V2.6-Flash | 1 | sram | 353,266.8 | 28,769.9 | 28,769.9 | 12.28x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 2 | sram | 353,266.8 | 28,769.9 | 28,769.9 | 12.28x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 4 | sram | 353,266.8 | 28,769.9 | 30,851.1 | 12.28x | 1.07x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 8 | sram | 353,266.8 | 28,769.9 | 51,043.1 | 12.28x | 1.77x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 16 | sram | 353,266.8 | 28,769.9 | 78,174.5 | 12.28x | 2.72x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 32 | sram | 376,592.9 | 28,769.9 | 105,949.9 | 13.09x | 3.68x | compute | weight_read | kv_read |
| MiMo-V2.6-Flash | 64 | sram | 471,237.6 | 28,796.5 | 148,284.5 | 16.36x | 5.15x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 256 | sram | 794,587.6 | 28,959.8 | 329,493.2 | 27.44x | 11.38x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Flash | 1024 | sram | 1,156,641.2 | 26,103.8 | 161,316.1 | 44.31x | 6.18x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 4096 | sram | 1,700,743.0 | 26,110.4 | 161,535.2 | 65.14x | 6.19x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Flash | 1 | rom | 1,597,084.5 | 129,898.4 | 129,898.4 | 12.29x | 1.00x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 2 | rom | 1,597,084.5 | 129,898.4 | 129,898.4 | 12.29x | 1.00x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 4 | rom | 1,597,084.5 | 129,898.4 | 129,898.4 | 12.29x | 1.00x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 8 | rom | 1,597,084.5 | 129,898.4 | 129,898.4 | 12.29x | 1.00x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 16 | rom | 1,597,084.5 | 129,898.4 | 129,898.4 | 12.29x | 1.00x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 32 | rom | 1,597,084.5 | 129,898.4 | 139,932.7 | 12.29x | 1.08x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 64 | rom | 1,597,084.5 | 129,898.4 | 159,057.8 | 12.29x | 1.22x | weight_read | kv_read | kv_read |
| MiMo-V2.6-Flash | 256 | rom | 1,606,480.6 | 131,284.8 | 254,683.5 | 12.24x | 1.94x | compute | kv_read | kv_read |
| MiMo-V2.6-Flash | 1024 | rom | 1,789,068.0 | 132,134.0 | 260,791.4 | 13.54x | 1.97x | compute | kv_read | kv_read |
| MiMo-V2.6-Flash | 4096 | rom | 1,818,359.1 | 132,348.0 | 261,384.6 | 13.74x | 1.97x | compute | kv_read | kv_read |

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
| MiMo-V2.6-Flash | 1 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 353,266.8 | 0.637 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 1 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,597,084.5 | 5.764 | weight_read | 4.52x |
| MiMo-V2.6-Flash | 1 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 1 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 129,898.4 | 1.405 | kv_read | 0.37x |
| MiMo-V2.6-Flash | 1 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 1 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.15 | 1.00 | 129,898.4 | 1.405 | kv_read | 0.37x |
| MiMo-V2.6-Flash | 2 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 353,266.8 | 0.637 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 2 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,597,084.5 | 5.764 | weight_read | 4.52x |
| MiMo-V2.6-Flash | 2 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 2 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 129,898.4 | 1.405 | kv_read | 0.37x |
| MiMo-V2.6-Flash | 2 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 2 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.15 | 1.00 | 129,898.4 | 1.405 | kv_read | 0.37x |
| MiMo-V2.6-Flash | 4 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 353,266.8 | 0.637 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 4 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,597,084.5 | 5.764 | weight_read | 4.52x |
| MiMo-V2.6-Flash | 4 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 4 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 129,898.4 | 1.405 | kv_read | 0.37x |
| MiMo-V2.6-Flash | 4 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x19-perregion | 15,485 | 1.00 | 1.79 | 30,851.1 | 1.992 | weight_read | 0.09x |
| MiMo-V2.6-Flash | 4 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.15 | 1.00 | 129,898.4 | 1.405 | kv_read | 0.37x |
| MiMo-V2.6-Flash | 8 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 353,266.8 | 0.637 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 8 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,597,084.5 | 5.764 | weight_read | 4.52x |
| MiMo-V2.6-Flash | 8 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 8 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 129,898.4 | 1.405 | kv_read | 0.37x |
| MiMo-V2.6-Flash | 8 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x21-perregion | 17,115 | 1.00 | 2.34 | 51,043.1 | 2.982 | weight_read | 0.14x |
| MiMo-V2.6-Flash | 8 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.15 | 1.00 | 129,898.4 | 1.405 | kv_read | 0.37x |
| MiMo-V2.6-Flash | 16 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 353,266.8 | 0.637 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 16 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,597,084.5 | 5.764 | weight_read | 4.52x |
| MiMo-V2.6-Flash | 16 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 16 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 129,898.4 | 1.405 | kv_read | 0.37x |
| MiMo-V2.6-Flash | 16 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x21-perregion | 17,115 | 1.00 | 3.27 | 78,174.5 | 4.568 | weight_read | 0.22x |
| MiMo-V2.6-Flash | 16 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perregion-romfill | 92,450 | 6.15 | 1.00 | 129,898.4 | 1.405 | kv_read | 0.37x |
| MiMo-V2.6-Flash | 32 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x78 | 63,570 | 1.00 | 1.00 | 376,592.9 | 5.924 | compute | 1.00x |
| MiMo-V2.6-Flash | 32 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,597,084.5 | 5.764 | weight_read | 4.24x |
| MiMo-V2.6-Flash | 32 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 28,769.9 | 0.622 | weight_read | 0.08x |
| MiMo-V2.6-Flash | 32 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 129,898.4 | 1.405 | kv_read | 0.34x |
| MiMo-V2.6-Flash | 32 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x21-perregion | 17,115 | 1.00 | 4.64 | 105,949.9 | 6.190 | kv_read | 0.28x |
| MiMo-V2.6-Flash | 32 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x34-perregion-romfill | 27,710 | 1.69 | 4.64 | 139,932.7 | 5.050 | kv_read | 0.37x |
| MiMo-V2.6-Flash | 64 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x113 | 92,095 | 1.00 | 1.00 | 471,237.6 | 5.117 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 64 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,597,084.5 | 5.764 | weight_read | 3.39x |
| MiMo-V2.6-Flash | 64 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 28,796.5 | 0.623 | weight_read | 0.06x |
| MiMo-V2.6-Flash | 64 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 1.00 | 129,898.4 | 1.405 | kv_read | 0.28x |
| MiMo-V2.6-Flash | 64 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 6.85 | 148,284.5 | 3.208 | weight_read | 0.31x |
| MiMo-V2.6-Flash | 64 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-tensor-x34-perregion-romfill | 27,710 | 1.69 | 6.85 | 159,057.8 | 5.740 | kv_read | 0.34x |
| MiMo-V2.6-Flash | 256 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x113 | 92,095 | 1.00 | 1.00 | 794,587.6 | 8.628 | weight_read | 1.00x |
| MiMo-V2.6-Flash | 256 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill | 277,100 | 4.76 | 1.00 | 1,606,480.6 | 5.797 | compute | 2.02x |
| MiMo-V2.6-Flash | 256 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 28,959.8 | 0.626 | weight_read | 0.04x |
| MiMo-V2.6-Flash | 256 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 2.25 | 131,284.8 | 1.420 | kv_read | 0.17x |
| MiMo-V2.6-Flash | 256 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 16.87 | 329,493.2 | 7.128 | weight_read | 0.41x |
| MiMo-V2.6-Flash | 256 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x34-perregion-romfill | 27,710 | 1.69 | 4.36 | 254,683.5 | 9.191 | kv_read | 0.32x |
| MiMo-V2.6-Flash | 1024 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x156 | 127,140 | 1.00 | 1.00 | 1,156,641.2 | 9.097 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 1024 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,789,068.0 | 6.456 | compute | 1.55x |
| MiMo-V2.6-Flash | 1024 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x21-perstream | 17,115 | 1.00 | 48.76 | 26,103.8 | 1.525 | weight_read | 0.02x |
| MiMo-V2.6-Flash | 1024 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 8.98 | 132,134.0 | 1.429 | kv_read | 0.11x |
| MiMo-V2.6-Flash | 1024 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x21-perregion | 17,115 | 1.00 | 5.85 | 161,316.1 | 9.425 | kv_read | 0.14x |
| MiMo-V2.6-Flash | 1024 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x34-perregion-romfill | 27,710 | 1.69 | 4.49 | 260,791.4 | 9.411 | kv_read | 0.23x |
| MiMo-V2.6-Flash | 4096 | batched | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 1.00 | 1.00 | 1,700,743.0 | 9.193 | kv_read | 1.00x |
| MiMo-V2.6-Flash | 4096 | batched | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x340-romfill | 277,100 | 4.76 | 1.00 | 1,818,359.1 | 6.562 | compute | 1.07x |
| MiMo-V2.6-Flash | 4096 | per_stream | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream | 92,450 | 1.00 | 35.93 | 26,110.4 | 0.282 | weight_read | 0.02x |
| MiMo-V2.6-Flash | 4096 | per_stream | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x2-perstream-romfill | 92,450 | 6.15 | 35.93 | 132,348.0 | 1.432 | kv_read | 0.08x |
| MiMo-V2.6-Flash | 4096 | per_region | sram | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x21-perregion | 17,115 | 1.00 | 13.95 | 161,535.2 | 9.438 | kv_read | 0.09x |
| MiMo-V2.6-Flash | 4096 | per_region | rom | MiMo-V2.6-Flash/ROM-N6-native-HBMKV-array-hw-pipeline-x34-perregion-romfill | 27,710 | 1.69 | 10.12 | 261,384.6 | 9.433 | kv_read | 0.15x |

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
| MiMo-V2.6-Flash | 1 | 19 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 2 | 19 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 4 | 19 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Flash | 64 | 57 | 1.12 | 1.002 | 1.027 | 1.02x |
| MiMo-V2.6-Flash | 256 | 57 | 4.49 | 1.056 | 1.885 | 1.78x |
| MiMo-V2.6-Flash | 1024 | 21 | 48.76 | 1.935 | 5.848 | 3.02x |
| MiMo-V2.6-Flash | 4096 | 21 | 195.05 | 6.108 | 13.947 | 2.28x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Flash | 1 | 15 | 6.36 | 4.06 | 1.57x |
| MiMo-V2.6-Flash | 2 | 15 | 9.94 | 5.24 | 1.90x |
| MiMo-V2.6-Flash | 4 | 15 | 13.17 | 6.51 | 2.02x |
| MiMo-V2.6-Flash | 8 | 15 | 14.71 | 7.78 | 1.89x |
| MiMo-V2.6-Flash | 16 | 15 | 14.99 | 8.90 | 1.68x |
| MiMo-V2.6-Flash | 32 | 15 | 15.00 | 9.77 | 1.54x |
| MiMo-V2.6-Flash | 64 | 15 | 15.00 | 10.30 | 1.46x |
| MiMo-V2.6-Flash | 256 | 15 | 15.00 | 10.54 | 1.42x |
| MiMo-V2.6-Flash | 1024 | 15 | 15.00 | 10.54 | 1.42x |
| MiMo-V2.6-Flash | 4096 | 15 | 15.00 | 10.54 | 1.42x |
| MiMo-V2.6-Flash | 1 | 19 | 6.67 | 4.36 | 1.53x |
| MiMo-V2.6-Flash | 2 | 19 | 10.89 | 5.74 | 1.90x |
| MiMo-V2.6-Flash | 4 | 19 | 15.35 | 7.29 | 2.11x |
| MiMo-V2.6-Flash | 8 | 19 | 18.15 | 8.87 | 2.05x |
| MiMo-V2.6-Flash | 16 | 19 | 18.92 | 10.33 | 1.83x |
| MiMo-V2.6-Flash | 32 | 19 | 19.00 | 11.49 | 1.65x |
| MiMo-V2.6-Flash | 64 | 19 | 19.00 | 12.22 | 1.56x |
| MiMo-V2.6-Flash | 256 | 19 | 19.00 | 12.53 | 1.52x |
| MiMo-V2.6-Flash | 1024 | 19 | 19.00 | 12.53 | 1.52x |
| MiMo-V2.6-Flash | 4096 | 19 | 19.00 | 12.53 | 1.52x |
| MiMo-V2.6-Flash | 1 | 20 | 6.73 | 4.42 | 1.52x |
| MiMo-V2.6-Flash | 2 | 20 | 11.08 | 5.85 | 1.90x |
| MiMo-V2.6-Flash | 4 | 20 | 15.82 | 7.46 | 2.12x |
| MiMo-V2.6-Flash | 8 | 20 | 18.95 | 9.12 | 2.08x |
| MiMo-V2.6-Flash | 16 | 20 | 19.89 | 10.66 | 1.87x |
| MiMo-V2.6-Flash | 32 | 20 | 20.00 | 11.89 | 1.68x |
| MiMo-V2.6-Flash | 64 | 20 | 20.00 | 12.66 | 1.58x |
| MiMo-V2.6-Flash | 256 | 20 | 20.00 | 13.00 | 1.54x |
| MiMo-V2.6-Flash | 1024 | 20 | 20.00 | 13.00 | 1.54x |
| MiMo-V2.6-Flash | 4096 | 20 | 20.00 | 13.00 | 1.54x |
| MiMo-V2.6-Flash | 1 | 21 | 6.79 | 4.48 | 1.51x |
| MiMo-V2.6-Flash | 2 | 21 | 11.26 | 5.95 | 1.89x |
| MiMo-V2.6-Flash | 4 | 21 | 16.27 | 7.62 | 2.13x |
| MiMo-V2.6-Flash | 8 | 21 | 19.72 | 9.36 | 2.11x |
| MiMo-V2.6-Flash | 16 | 21 | 20.85 | 10.98 | 1.90x |
| MiMo-V2.6-Flash | 32 | 21 | 20.99 | 12.28 | 1.71x |
| MiMo-V2.6-Flash | 64 | 21 | 21.00 | 13.10 | 1.60x |
| MiMo-V2.6-Flash | 256 | 21 | 21.00 | 13.46 | 1.56x |
| MiMo-V2.6-Flash | 1024 | 21 | 21.00 | 13.46 | 1.56x |
| MiMo-V2.6-Flash | 4096 | 21 | 21.00 | 13.46 | 1.56x |
| MiMo-V2.6-Flash | 1 | 22 | 6.84 | 4.54 | 1.51x |
| MiMo-V2.6-Flash | 2 | 22 | 11.43 | 6.05 | 1.89x |
| MiMo-V2.6-Flash | 4 | 22 | 16.68 | 7.78 | 2.14x |
| MiMo-V2.6-Flash | 8 | 22 | 20.48 | 9.60 | 2.13x |
| MiMo-V2.6-Flash | 16 | 22 | 21.81 | 11.29 | 1.93x |
| MiMo-V2.6-Flash | 32 | 22 | 21.99 | 12.66 | 1.74x |
| MiMo-V2.6-Flash | 64 | 22 | 22.00 | 13.53 | 1.63x |
| MiMo-V2.6-Flash | 256 | 22 | 22.00 | 13.91 | 1.58x |
| MiMo-V2.6-Flash | 1024 | 22 | 22.00 | 13.91 | 1.58x |
| MiMo-V2.6-Flash | 4096 | 22 | 22.00 | 13.91 | 1.58x |
| MiMo-V2.6-Flash | 1 | 24 | 6.93 | 4.65 | 1.49x |
| MiMo-V2.6-Flash | 2 | 24 | 11.72 | 6.23 | 1.88x |
| MiMo-V2.6-Flash | 4 | 24 | 17.46 | 8.08 | 2.16x |
| MiMo-V2.6-Flash | 8 | 24 | 21.92 | 10.04 | 2.18x |
| MiMo-V2.6-Flash | 16 | 24 | 23.69 | 11.89 | 1.99x |
| MiMo-V2.6-Flash | 32 | 24 | 23.98 | 13.40 | 1.79x |
| MiMo-V2.6-Flash | 64 | 24 | 24.00 | 14.36 | 1.67x |
| MiMo-V2.6-Flash | 256 | 24 | 24.00 | 14.79 | 1.62x |
| MiMo-V2.6-Flash | 1024 | 24 | 24.00 | 14.79 | 1.62x |
| MiMo-V2.6-Flash | 4096 | 24 | 24.00 | 14.79 | 1.62x |
| MiMo-V2.6-Flash | 1 | 34 | 7.22 | 5.11 | 1.41x |
| MiMo-V2.6-Flash | 2 | 34 | 12.75 | 6.96 | 1.83x |
| MiMo-V2.6-Flash | 4 | 34 | 20.33 | 9.31 | 2.18x |
| MiMo-V2.6-Flash | 8 | 34 | 27.88 | 11.90 | 2.34x |
| MiMo-V2.6-Flash | 16 | 34 | 32.38 | 14.47 | 2.24x |
| MiMo-V2.6-Flash | 32 | 34 | 33.74 | 16.63 | 2.03x |
| MiMo-V2.6-Flash | 64 | 34 | 33.96 | 18.05 | 1.88x |
| MiMo-V2.6-Flash | 256 | 34 | 33.98 | 18.69 | 1.82x |
| MiMo-V2.6-Flash | 1024 | 34 | 33.98 | 18.69 | 1.82x |
| MiMo-V2.6-Flash | 4096 | 34 | 33.98 | 18.69 | 1.82x |
| MiMo-V2.6-Flash | 1 | 37 | 7.28 | 5.22 | 1.40x |
| MiMo-V2.6-Flash | 2 | 37 | 12.97 | 7.13 | 1.82x |
| MiMo-V2.6-Flash | 4 | 37 | 20.97 | 9.62 | 2.18x |
| MiMo-V2.6-Flash | 8 | 37 | 29.33 | 12.38 | 2.37x |
| MiMo-V2.6-Flash | 16 | 37 | 34.74 | 15.13 | 2.30x |
| MiMo-V2.6-Flash | 32 | 37 | 36.58 | 17.49 | 2.09x |
| MiMo-V2.6-Flash | 64 | 37 | 36.92 | 19.04 | 1.94x |
| MiMo-V2.6-Flash | 256 | 37 | 36.97 | 19.74 | 1.87x |
| MiMo-V2.6-Flash | 1024 | 37 | 36.97 | 19.74 | 1.87x |
| MiMo-V2.6-Flash | 4096 | 37 | 36.97 | 19.74 | 1.87x |
| MiMo-V2.6-Flash | 1 | 41 | 7.35 | 5.35 | 1.37x |
| MiMo-V2.6-Flash | 2 | 41 | 13.21 | 7.34 | 1.80x |
| MiMo-V2.6-Flash | 4 | 41 | 21.71 | 9.99 | 2.17x |
| MiMo-V2.6-Flash | 8 | 41 | 31.07 | 12.96 | 2.40x |
| MiMo-V2.6-Flash | 16 | 41 | 37.69 | 15.97 | 2.36x |
| MiMo-V2.6-Flash | 32 | 41 | 40.27 | 18.56 | 2.17x |
| MiMo-V2.6-Flash | 64 | 41 | 40.83 | 20.29 | 2.01x |
| MiMo-V2.6-Flash | 256 | 41 | 40.93 | 21.06 | 1.94x |
| MiMo-V2.6-Flash | 1024 | 41 | 40.93 | 21.07 | 1.94x |
| MiMo-V2.6-Flash | 4096 | 41 | 40.93 | 21.07 | 1.94x |
| MiMo-V2.6-Flash | 1 | 42 | 7.36 | 5.38 | 1.37x |
| MiMo-V2.6-Flash | 2 | 42 | 13.26 | 7.39 | 1.80x |
| MiMo-V2.6-Flash | 4 | 42 | 21.88 | 10.08 | 2.17x |
| MiMo-V2.6-Flash | 8 | 42 | 31.47 | 13.10 | 2.40x |
| MiMo-V2.6-Flash | 16 | 42 | 38.40 | 16.17 | 2.38x |
| MiMo-V2.6-Flash | 32 | 42 | 41.18 | 18.82 | 2.19x |
| MiMo-V2.6-Flash | 64 | 42 | 41.80 | 20.59 | 2.03x |
| MiMo-V2.6-Flash | 256 | 42 | 41.91 | 21.38 | 1.96x |
| MiMo-V2.6-Flash | 1024 | 42 | 41.91 | 21.39 | 1.96x |
| MiMo-V2.6-Flash | 4096 | 42 | 41.91 | 21.39 | 1.96x |
| MiMo-V2.6-Flash | 1 | 43 | 7.38 | 5.41 | 1.36x |
| MiMo-V2.6-Flash | 2 | 43 | 13.32 | 7.44 | 1.79x |
| MiMo-V2.6-Flash | 4 | 43 | 22.04 | 10.17 | 2.17x |
| MiMo-V2.6-Flash | 8 | 43 | 31.87 | 13.24 | 2.41x |
| MiMo-V2.6-Flash | 16 | 43 | 39.10 | 16.36 | 2.39x |
| MiMo-V2.6-Flash | 32 | 43 | 42.08 | 19.07 | 2.21x |
| MiMo-V2.6-Flash | 64 | 43 | 42.77 | 20.88 | 2.05x |
| MiMo-V2.6-Flash | 256 | 43 | 42.90 | 21.70 | 1.98x |
| MiMo-V2.6-Flash | 1024 | 43 | 42.90 | 21.70 | 1.98x |
| MiMo-V2.6-Flash | 4096 | 43 | 42.90 | 21.70 | 1.98x |
| MiMo-V2.6-Flash | 1 | 44 | 7.39 | 5.44 | 1.36x |
| MiMo-V2.6-Flash | 2 | 44 | 13.37 | 7.48 | 1.79x |
| MiMo-V2.6-Flash | 4 | 44 | 22.19 | 10.26 | 2.16x |
| MiMo-V2.6-Flash | 8 | 44 | 32.25 | 13.37 | 2.41x |
| MiMo-V2.6-Flash | 16 | 44 | 39.78 | 16.55 | 2.40x |
| MiMo-V2.6-Flash | 32 | 44 | 42.97 | 19.32 | 2.22x |
| MiMo-V2.6-Flash | 64 | 44 | 43.74 | 21.17 | 2.07x |
| MiMo-V2.6-Flash | 256 | 44 | 43.88 | 22.01 | 1.99x |
| MiMo-V2.6-Flash | 1024 | 44 | 43.88 | 22.01 | 1.99x |
| MiMo-V2.6-Flash | 4096 | 44 | 43.88 | 22.01 | 1.99x |
| MiMo-V2.6-Flash | 1 | 48 | 7.44 | 5.56 | 1.34x |
| MiMo-V2.6-Flash | 2 | 48 | 13.55 | 7.66 | 1.77x |
| MiMo-V2.6-Flash | 4 | 48 | 22.76 | 10.58 | 2.15x |
| MiMo-V2.6-Flash | 8 | 48 | 33.67 | 13.88 | 2.43x |
| MiMo-V2.6-Flash | 16 | 48 | 42.39 | 17.29 | 2.45x |
| MiMo-V2.6-Flash | 32 | 48 | 46.46 | 20.29 | 2.29x |
| MiMo-V2.6-Flash | 64 | 48 | 47.56 | 22.30 | 2.13x |
| MiMo-V2.6-Flash | 256 | 48 | 47.78 | 23.22 | 2.06x |
| MiMo-V2.6-Flash | 1024 | 48 | 47.78 | 23.22 | 2.06x |
| MiMo-V2.6-Flash | 4096 | 48 | 47.78 | 23.22 | 2.06x |
| MiMo-V2.6-Flash | 1 | 53 | 7.49 | 5.69 | 1.32x |
| MiMo-V2.6-Flash | 2 | 53 | 13.74 | 7.86 | 1.75x |
| MiMo-V2.6-Flash | 4 | 53 | 23.37 | 10.96 | 2.13x |
| MiMo-V2.6-Flash | 8 | 53 | 35.25 | 14.47 | 2.44x |
| MiMo-V2.6-Flash | 16 | 53 | 45.40 | 18.15 | 2.50x |
| MiMo-V2.6-Flash | 32 | 53 | 50.64 | 21.42 | 2.36x |
| MiMo-V2.6-Flash | 64 | 53 | 52.23 | 23.63 | 2.21x |
| MiMo-V2.6-Flash | 256 | 53 | 52.60 | 24.64 | 2.13x |
| MiMo-V2.6-Flash | 1024 | 53 | 52.60 | 24.65 | 2.13x |
| MiMo-V2.6-Flash | 4096 | 53 | 52.60 | 24.65 | 2.13x |
| MiMo-V2.6-Flash | 1 | 55 | 7.51 | 5.73 | 1.31x |
| MiMo-V2.6-Flash | 2 | 55 | 13.80 | 7.94 | 1.74x |
| MiMo-V2.6-Flash | 4 | 55 | 23.59 | 11.10 | 2.13x |
| MiMo-V2.6-Flash | 8 | 55 | 35.82 | 14.69 | 2.44x |
| MiMo-V2.6-Flash | 16 | 55 | 46.53 | 18.47 | 2.52x |
| MiMo-V2.6-Flash | 32 | 55 | 52.25 | 21.85 | 2.39x |
| MiMo-V2.6-Flash | 64 | 55 | 54.07 | 24.14 | 2.24x |
| MiMo-V2.6-Flash | 256 | 55 | 54.50 | 25.19 | 2.16x |
| MiMo-V2.6-Flash | 1024 | 55 | 54.50 | 25.19 | 2.16x |
| MiMo-V2.6-Flash | 4096 | 55 | 54.50 | 25.19 | 2.16x |
| MiMo-V2.6-Flash | 1 | 56 | 7.52 | 5.76 | 1.31x |
| MiMo-V2.6-Flash | 2 | 56 | 13.84 | 7.98 | 1.73x |
| MiMo-V2.6-Flash | 4 | 56 | 23.69 | 11.17 | 2.12x |
| MiMo-V2.6-Flash | 8 | 56 | 36.10 | 14.80 | 2.44x |
| MiMo-V2.6-Flash | 16 | 56 | 47.08 | 18.63 | 2.53x |
| MiMo-V2.6-Flash | 32 | 56 | 53.05 | 22.06 | 2.40x |
| MiMo-V2.6-Flash | 64 | 56 | 54.98 | 24.39 | 2.25x |
| MiMo-V2.6-Flash | 256 | 56 | 55.44 | 25.46 | 2.18x |
| MiMo-V2.6-Flash | 1024 | 56 | 55.44 | 25.46 | 2.18x |
| MiMo-V2.6-Flash | 4096 | 56 | 55.44 | 25.46 | 2.18x |
| MiMo-V2.6-Flash | 1 | 58 | 7.53 | 5.80 | 1.30x |
| MiMo-V2.6-Flash | 2 | 58 | 13.90 | 8.05 | 1.73x |
| MiMo-V2.6-Flash | 4 | 58 | 23.89 | 11.30 | 2.11x |
| MiMo-V2.6-Flash | 8 | 58 | 36.63 | 15.01 | 2.44x |
| MiMo-V2.6-Flash | 16 | 58 | 48.15 | 18.95 | 2.54x |
| MiMo-V2.6-Flash | 32 | 58 | 54.61 | 22.48 | 2.43x |
| MiMo-V2.6-Flash | 64 | 58 | 56.79 | 24.88 | 2.28x |
| MiMo-V2.6-Flash | 256 | 58 | 57.32 | 25.99 | 2.21x |
| MiMo-V2.6-Flash | 1024 | 58 | 57.32 | 25.99 | 2.21x |
| MiMo-V2.6-Flash | 4096 | 58 | 57.32 | 25.99 | 2.21x |
| MiMo-V2.6-Flash | 1 | 67 | 7.59 | 5.98 | 1.27x |
| MiMo-V2.6-Flash | 2 | 67 | 14.13 | 8.35 | 1.69x |
| MiMo-V2.6-Flash | 4 | 67 | 24.67 | 11.85 | 2.08x |
| MiMo-V2.6-Flash | 8 | 67 | 38.75 | 15.89 | 2.44x |
| MiMo-V2.6-Flash | 16 | 67 | 52.54 | 20.26 | 2.59x |
| MiMo-V2.6-Flash | 32 | 67 | 61.25 | 24.23 | 2.53x |
| MiMo-V2.6-Flash | 64 | 67 | 64.64 | 26.96 | 2.40x |
| MiMo-V2.6-Flash | 256 | 67 | 65.57 | 28.23 | 2.32x |
| MiMo-V2.6-Flash | 1024 | 67 | 65.57 | 28.23 | 2.32x |
| MiMo-V2.6-Flash | 4096 | 67 | 65.57 | 28.23 | 2.32x |
| MiMo-V2.6-Flash | 1 | 71 | 7.62 | 6.05 | 1.26x |
| MiMo-V2.6-Flash | 2 | 71 | 14.22 | 8.48 | 1.68x |
| MiMo-V2.6-Flash | 4 | 71 | 24.96 | 12.07 | 2.07x |
| MiMo-V2.6-Flash | 8 | 71 | 39.56 | 16.24 | 2.44x |
| MiMo-V2.6-Flash | 16 | 71 | 54.28 | 20.79 | 2.61x |
| MiMo-V2.6-Flash | 32 | 71 | 64.00 | 24.95 | 2.57x |
| MiMo-V2.6-Flash | 64 | 71 | 67.97 | 27.83 | 2.44x |
| MiMo-V2.6-Flash | 256 | 71 | 69.12 | 29.17 | 2.37x |
| MiMo-V2.6-Flash | 1024 | 71 | 69.12 | 29.17 | 2.37x |
| MiMo-V2.6-Flash | 4096 | 71 | 69.12 | 29.17 | 2.37x |
| MiMo-V2.6-Flash | 1 | 77 | 7.65 | 6.15 | 1.24x |
| MiMo-V2.6-Flash | 2 | 77 | 14.33 | 8.65 | 1.66x |
| MiMo-V2.6-Flash | 4 | 77 | 25.34 | 12.37 | 2.05x |
| MiMo-V2.6-Flash | 8 | 77 | 40.65 | 16.73 | 2.43x |
| MiMo-V2.6-Flash | 16 | 77 | 56.69 | 21.55 | 2.63x |
| MiMo-V2.6-Flash | 32 | 77 | 67.89 | 25.98 | 2.61x |
| MiMo-V2.6-Flash | 64 | 77 | 72.80 | 29.07 | 2.50x |
| MiMo-V2.6-Flash | 256 | 77 | 74.29 | 30.50 | 2.44x |
| MiMo-V2.6-Flash | 1024 | 77 | 74.29 | 30.51 | 2.44x |
| MiMo-V2.6-Flash | 4096 | 77 | 74.29 | 30.51 | 2.44x |
| MiMo-V2.6-Flash | 1 | 107 | 7.74 | 6.52 | 1.19x |
| MiMo-V2.6-Flash | 2 | 107 | 14.71 | 9.40 | 1.56x |
| MiMo-V2.6-Flash | 4 | 107 | 26.67 | 13.51 | 1.97x |
| MiMo-V2.6-Flash | 8 | 107 | 44.59 | 18.77 | 2.38x |
| MiMo-V2.6-Flash | 16 | 107 | 65.92 | 24.72 | 2.67x |
| MiMo-V2.6-Flash | 32 | 107 | 83.91 | 30.35 | 2.77x |
| MiMo-V2.6-Flash | 64 | 107 | 93.75 | 34.37 | 2.73x |
| MiMo-V2.6-Flash | 256 | 107 | 97.32 | 36.27 | 2.68x |
| MiMo-V2.6-Flash | 1024 | 107 | 97.33 | 36.27 | 2.68x |
| MiMo-V2.6-Flash | 4096 | 107 | 97.33 | 36.27 | 2.68x |
| MiMo-V2.6-Flash | 1 | 111 | 7.75 | 6.56 | 1.18x |
| MiMo-V2.6-Flash | 2 | 111 | 14.75 | 9.49 | 1.55x |
| MiMo-V2.6-Flash | 4 | 111 | 26.80 | 13.64 | 1.97x |
| MiMo-V2.6-Flash | 8 | 111 | 44.99 | 19.00 | 2.37x |
| MiMo-V2.6-Flash | 16 | 111 | 66.89 | 25.09 | 2.67x |
| MiMo-V2.6-Flash | 32 | 111 | 85.68 | 30.85 | 2.78x |
| MiMo-V2.6-Flash | 64 | 111 | 96.17 | 34.99 | 2.75x |
| MiMo-V2.6-Flash | 256 | 111 | 100.05 | 36.94 | 2.71x |
| MiMo-V2.6-Flash | 1024 | 111 | 100.06 | 36.95 | 2.71x |
| MiMo-V2.6-Flash | 4096 | 111 | 100.06 | 36.95 | 2.71x |
| MiMo-V2.6-Flash | 1 | 112 | 7.75 | 6.57 | 1.18x |
| MiMo-V2.6-Flash | 2 | 112 | 14.75 | 9.51 | 1.55x |
| MiMo-V2.6-Flash | 4 | 112 | 26.83 | 13.67 | 1.96x |
| MiMo-V2.6-Flash | 8 | 112 | 45.08 | 19.06 | 2.37x |
| MiMo-V2.6-Flash | 16 | 112 | 67.12 | 25.18 | 2.67x |
| MiMo-V2.6-Flash | 32 | 112 | 86.11 | 30.98 | 2.78x |
| MiMo-V2.6-Flash | 64 | 112 | 96.77 | 35.14 | 2.75x |
| MiMo-V2.6-Flash | 256 | 112 | 100.72 | 37.11 | 2.71x |
| MiMo-V2.6-Flash | 1024 | 112 | 100.73 | 37.11 | 2.71x |
| MiMo-V2.6-Flash | 4096 | 112 | 100.73 | 37.11 | 2.71x |
| MiMo-V2.6-Flash | 1 | 115 | 7.76 | 6.59 | 1.18x |
| MiMo-V2.6-Flash | 2 | 115 | 14.78 | 9.57 | 1.54x |
| MiMo-V2.6-Flash | 4 | 115 | 26.92 | 13.75 | 1.96x |
| MiMo-V2.6-Flash | 8 | 115 | 45.35 | 19.23 | 2.36x |
| MiMo-V2.6-Flash | 16 | 115 | 67.80 | 25.44 | 2.66x |
| MiMo-V2.6-Flash | 32 | 115 | 87.38 | 31.35 | 2.79x |
| MiMo-V2.6-Flash | 64 | 115 | 98.52 | 35.59 | 2.77x |
| MiMo-V2.6-Flash | 256 | 115 | 102.70 | 37.60 | 2.73x |
| MiMo-V2.6-Flash | 1024 | 115 | 102.71 | 37.61 | 2.73x |
| MiMo-V2.6-Flash | 4096 | 115 | 102.71 | 37.61 | 2.73x |
| MiMo-V2.6-Flash | 1 | 142 | 7.81 | 6.80 | 1.15x |
| MiMo-V2.6-Flash | 2 | 142 | 14.96 | 10.09 | 1.48x |
| MiMo-V2.6-Flash | 4 | 142 | 27.56 | 14.42 | 1.91x |
| MiMo-V2.6-Flash | 8 | 142 | 47.37 | 20.64 | 2.29x |
| MiMo-V2.6-Flash | 16 | 142 | 72.92 | 27.59 | 2.64x |
| MiMo-V2.6-Flash | 32 | 142 | 97.22 | 34.34 | 2.83x |
| MiMo-V2.6-Flash | 64 | 142 | 112.52 | 39.27 | 2.86x |
| MiMo-V2.6-Flash | 256 | 142 | 118.73 | 41.64 | 2.85x |
| MiMo-V2.6-Flash | 1024 | 142 | 118.74 | 41.65 | 2.85x |
| MiMo-V2.6-Flash | 4096 | 142 | 118.74 | 41.65 | 2.85x |
| MiMo-V2.6-Flash | 1 | 154 | 7.82 | 6.87 | 1.14x |
| MiMo-V2.6-Flash | 2 | 154 | 15.02 | 10.29 | 1.46x |
| MiMo-V2.6-Flash | 4 | 154 | 27.78 | 14.68 | 1.89x |
| MiMo-V2.6-Flash | 8 | 154 | 48.06 | 21.20 | 2.27x |
| MiMo-V2.6-Flash | 16 | 154 | 74.74 | 28.41 | 2.63x |
| MiMo-V2.6-Flash | 32 | 154 | 100.86 | 35.51 | 2.84x |
| MiMo-V2.6-Flash | 64 | 154 | 117.85 | 40.73 | 2.89x |
| MiMo-V2.6-Flash | 256 | 154 | 124.93 | 43.25 | 2.89x |
| MiMo-V2.6-Flash | 1024 | 154 | 124.94 | 43.25 | 2.89x |
| MiMo-V2.6-Flash | 4096 | 154 | 124.94 | 43.25 | 2.89x |
| MiMo-V2.6-Flash | 1 | 168 | 7.84 | 6.95 | 1.13x |
| MiMo-V2.6-Flash | 2 | 168 | 15.08 | 10.51 | 1.43x |
| MiMo-V2.6-Flash | 4 | 168 | 27.99 | 14.95 | 1.87x |
| MiMo-V2.6-Flash | 8 | 168 | 48.76 | 21.79 | 2.24x |
| MiMo-V2.6-Flash | 16 | 168 | 76.60 | 29.28 | 2.62x |
| MiMo-V2.6-Flash | 32 | 168 | 104.63 | 36.76 | 2.85x |
| MiMo-V2.6-Flash | 64 | 168 | 123.48 | 42.32 | 2.92x |
| MiMo-V2.6-Flash | 256 | 168 | 131.55 | 44.99 | 2.92x |
| MiMo-V2.6-Flash | 1024 | 168 | 131.56 | 45.00 | 2.92x |
| MiMo-V2.6-Flash | 4096 | 168 | 131.56 | 45.00 | 2.92x |
| MiMo-V2.6-Flash | 1 | 224 | 7.88 | 7.17 | 1.10x |
| MiMo-V2.6-Flash | 2 | 224 | 15.24 | 11.23 | 1.36x |
| MiMo-V2.6-Flash | 4 | 224 | 28.60 | 15.89 | 1.80x |
| MiMo-V2.6-Flash | 8 | 224 | 50.75 | 23.72 | 2.14x |
| MiMo-V2.6-Flash | 16 | 224 | 82.06 | 32.12 | 2.55x |
| MiMo-V2.6-Flash | 32 | 224 | 116.13 | 41.10 | 2.83x |
| MiMo-V2.6-Flash | 64 | 224 | 141.20 | 47.76 | 2.96x |
| MiMo-V2.6-Flash | 256 | 224 | 152.72 | 50.99 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 224 | 152.75 | 51.00 | 3.00x |
| MiMo-V2.6-Flash | 4096 | 224 | 152.75 | 51.00 | 3.00x |
| MiMo-V2.6-Flash | 1 | 335 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Flash | 2 | 335 | 15.41 | 12.20 | 1.26x |
| MiMo-V2.6-Flash | 4 | 335 | 29.22 | 17.38 | 1.68x |
| MiMo-V2.6-Flash | 8 | 335 | 52.84 | 26.01 | 2.03x |
| MiMo-V2.6-Flash | 16 | 335 | 88.02 | 36.44 | 2.42x |
| MiMo-V2.6-Flash | 32 | 335 | 129.41 | 47.38 | 2.73x |
| MiMo-V2.6-Flash | 64 | 335 | 162.72 | 55.62 | 2.93x |
| MiMo-V2.6-Flash | 256 | 335 | 179.13 | 59.69 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 335 | 179.16 | 59.70 | 3.00x |
| MiMo-V2.6-Flash | 4096 | 335 | 179.16 | 59.70 | 3.00x |
| MiMo-V2.6-Flash | 1 | 336 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Flash | 2 | 336 | 15.41 | 12.20 | 1.26x |
| MiMo-V2.6-Flash | 4 | 336 | 29.23 | 17.40 | 1.68x |
| MiMo-V2.6-Flash | 8 | 336 | 52.85 | 26.03 | 2.03x |
| MiMo-V2.6-Flash | 16 | 336 | 88.06 | 36.47 | 2.41x |
| MiMo-V2.6-Flash | 32 | 336 | 129.49 | 47.43 | 2.73x |
| MiMo-V2.6-Flash | 64 | 336 | 162.86 | 55.68 | 2.93x |
| MiMo-V2.6-Flash | 256 | 336 | 179.31 | 59.75 | 3.00x |
| MiMo-V2.6-Flash | 1024 | 336 | 179.34 | 59.76 | 3.00x |
| MiMo-V2.6-Flash | 4096 | 336 | 179.34 | 59.76 | 3.00x |
| MiMo-V2.6-Flash | 1 | 448 | 7.94 | 7.55 | 1.05x |
| MiMo-V2.6-Flash | 2 | 448 | 15.49 | 12.84 | 1.21x |
| MiMo-V2.6-Flash | 4 | 448 | 29.55 | 18.62 | 1.59x |
| MiMo-V2.6-Flash | 8 | 448 | 53.95 | 27.39 | 1.97x |
| MiMo-V2.6-Flash | 16 | 448 | 91.28 | 39.89 | 2.29x |
| MiMo-V2.6-Flash | 32 | 448 | 136.98 | 51.59 | 2.66x |
| MiMo-V2.6-Flash | 64 | 448 | 175.48 | 61.76 | 2.84x |
| MiMo-V2.6-Flash | 256 | 448 | 195.13 | 66.41 | 2.94x |
| MiMo-V2.6-Flash | 1024 | 448 | 195.17 | 66.42 | 2.94x |
| MiMo-V2.6-Flash | 4096 | 448 | 195.17 | 66.42 | 2.94x |
| MiMo-V2.6-Flash | 1 | 672 | 7.96 | 7.69 | 1.03x |
| MiMo-V2.6-Flash | 2 | 672 | 15.58 | 13.60 | 1.15x |
| MiMo-V2.6-Flash | 4 | 672 | 29.87 | 20.51 | 1.46x |
| MiMo-V2.6-Flash | 8 | 672 | 55.08 | 29.30 | 1.88x |
| MiMo-V2.6-Flash | 16 | 672 | 94.67 | 44.33 | 2.14x |
| MiMo-V2.6-Flash | 32 | 672 | 145.08 | 58.07 | 2.50x |
| MiMo-V2.6-Flash | 64 | 672 | 189.49 | 69.57 | 2.72x |
| MiMo-V2.6-Flash | 256 | 672 | 212.96 | 75.92 | 2.81x |
| MiMo-V2.6-Flash | 1024 | 672 | 213.01 | 75.93 | 2.81x |
| MiMo-V2.6-Flash | 4096 | 672 | 213.01 | 75.93 | 2.81x |

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
| gpu | MiMo-V2.6-Flash | 1 | 10.83 | 1.1% |
| rom | MiMo-V2.6-Flash | 1 | 10.83 | 16.9% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| MiMo-V2.6-Flash | sram | interleaved | 128 B | 1.00x |
| MiMo-V2.6-Flash | hbm | interleaved | 32 B | 1.00x |

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
| MiMo-V2.6-Flash | 1 | 19 | 16.60% | 29.29 | 9.28 |
| MiMo-V2.6-Flash | 2 | 19 | 16.60% | 29.29 | 9.28 |
| MiMo-V2.6-Flash | 4 | 19 | 16.60% | 29.29 | 9.28 |
| MiMo-V2.6-Flash | 8 | 1 | 0.35% | 1.87 | 9.28 |
| MiMo-V2.6-Flash | 16 | 1 | 0.35% | 1.87 | 9.28 |
| MiMo-V2.6-Flash | 32 | 1 | 0.35% | 1.87 | 9.28 |
| MiMo-V2.6-Flash | 64 | 1 | 0.40% | 2.10 | 9.28 |
| MiMo-V2.6-Flash | 256 | 1 | 1.59% | 8.42 | 9.28 |

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
| MiMo-V2.6-Flash | 1 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 1,000.4 | 42,016.8 |
| MiMo-V2.6-Flash | 2 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 1,000.4 | 42,016.8 |
| MiMo-V2.6-Flash | 4 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 1,000.4 | 42,016.8 |
| MiMo-V2.6-Flash | 8 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 1,000.4 | 42,016.8 |
| MiMo-V2.6-Flash | 16 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 1,000.4 | 42,016.8 |
| MiMo-V2.6-Flash | 32 | 3.12% | 12.7 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 1,000.4 | 42,016.8 |
| MiMo-V2.6-Flash | 64 | 4.72% | 15.2 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 659.3 | 42,193.0 |
| MiMo-V2.6-Flash | 256 | 17.59% | 35.9 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 165.8 | 42,447.9 |
| MiMo-V2.6-Flash | 1024 | 53.89% | 94.3 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 41.5 | 42,512.1 |
| MiMo-V2.6-Flash | 4096 | 95.48% | 161.2 GB | 100.00% | 5,017.30 TB/s | 5,017.30 TB/s | 10.4 | 42,528.2 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 18 |
| gpu | link_latency | 373 |
| gpu | weight_read | 889 |
| rom | compute | 647 |
| rom | infeasible | 2324 |
| rom | kv_read | 393 |
| rom | link_latency | 1228 |
| rom | weight_read | 808 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| rom | CAPACITY | 2324 |

## Mechanical consistency audit

**FAIL** over 138,947 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x38', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x43', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x44', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x45', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x54', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x72', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x108', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x144', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x38', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x43', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x44', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x45', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x54', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x72', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x108', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x144', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x38', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x43', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x44', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x45', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x54', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x72', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x108', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x144', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x38', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x43', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x44', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x45', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x54', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x57', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x72', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x108', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x113', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x144', 'MiMo-V2.6-Flash', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Flash/ROM-N6-native-SRAMKV-array-pipeline-x170', 'MiMo-V2.6-Flash', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 71 |
| derived | 47 |
| assumed | 70 |

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
